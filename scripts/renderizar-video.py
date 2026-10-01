"""Renderiza um roteiro (video-N.md) no padrão telejornal do RADAR 360, sem custo de licença:

- Narração: voz neural pt-BR (edge-tts, pt-BR-AntonioNeural), frase a frase, para legenda sincronizada.
- Fundo: fotos reais de licença livre do Wikimedia Commons (com crédito na tela) casadas com
  as pessoas/lugares citados em cada frase; sem foto adequada, entra o apresentador-âncora.
- Tela: selo do jornal, manchete grande (qual notícia), faixa do assunto do bloco, legenda
  do que está sendo falado em frases curtas e rodapé com crédito da imagem.

Uso: python renderizar-video.py video-1.md saida_dir --ancora ancora.jpg
"""
import argparse, asyncio, hashlib, html, io, json, re, subprocess, textwrap
from pathlib import Path

import edge_tts
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
MARCA = "RADAR 360"
SLOGAN = "O MUNDO COMO ELE É"
AZUL, AZUL2, VERMELHO, BRANCO, CINZA = (6, 28, 64), (12, 60, 130), (214, 31, 38), (255, 255, 255), (205, 212, 224)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
VOZ, VELOCIDADE, TOM = "pt-BR-AntonioNeural", "-6%", "-2Hz"
UA = {"User-Agent": "Radar360Bot/1.0 (jornalismo; viniciusmedvet@gmail.com)"}

# Termo que aparece na fala -> busca no Wikimedia Commons (fotos de licença livre).
ENTIDADES = [
    (r"\bZelensk", "Volodymyr Zelensky"), (r"\bPutin\b", "Vladimir Putin"), (r"\bTrump\b", "Donald Trump 2025"),
    (r"\bLavrov\b", "Sergey Lavrov"), (r"\bKiev\b|\bKyiv\b", "Kyiv Maidan Nezalezhnosti"),
    (r"\bPatriot\b", "MIM-104 Patriot launcher"), (r"\bsiderúrg", "steel plant Ukraine"),
    (r"Assembleia-Geral|\bONU\b", "United Nations General Assembly hall"),
    (r"fertilizant|adubo|lavoura", "soybean harvest Brazil"), (r"\bporto\b|portos", "Port of Santos"),
    (r"Ormuz|Hormuz", "Strait of Hormuz"), (r"Guarda Revolucionária|IRGC", "Islamic Revolutionary Guard Corps parade"),
    (r"\bIrã\b|Teerã", "Tehran skyline"), (r"petroleiro|barril|petróleo", "oil tanker ship"),
    (r"Departamento de Estado", "Harry S Truman Building State Department"),
    (r"combustível|posto|diesel|gasolina", "gas station Brazil"),
    (r"Alexandre de Moraes|\bMoraes\b", "Alexandre de Moraes"), (r"Mendonça", "André Mendonça"),
    (r"Toffoli", "Dias Toffoli"), (r"Gilmar", "Gilmar Mendes"), (r"\bFux\b", "Luiz Fux"),
    (r"Vorcaro|Banco Master", "Banco Master"), (r"Polícia Federal|\bPF\b", "Polícia Federal viatura"),
    (r"\bBRB\b", "Banco de Brasília"), (r"\bSTF\b|Supremo", "Supremo Tribunal Federal plenário"),
    (r"Praça dos Três Poderes", "Praça dos Três Poderes"),
    (r"\bLula\b", "Luiz Inácio Lula da Silva 2025"), (r"Flávio Bolsonaro", "Flávio Bolsonaro"),
    (r"Ibovespa|\bBolsa\b|\bB3\b", "B3 Brasil Bolsa Balcão"), (r"dólar", "dollar banknotes"),
    (r"Banco Central|Focus|inflação", "Banco Central do Brasil edifício"), (r"urna|eleiç|eleitor", "urna eletrônica"),
]
LICENCAS_OK = ("CC BY", "CC0", "Public domain", "PD", "CC-BY")


def secao(md, titulo):
    m = re.search(rf"^## {re.escape(titulo)}[^\n]*\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def blocos(md):
    """[(bloco, texto)] do roteiro narrado, sem deixas visuais nem marcação."""
    bloco, saida = "ABERTURA", []
    for par in re.split(r"\n\s*\n", secao(md, "Roteiro narrado")):
        par = par.strip()
        cab = re.match(r"\*\*(.+?)\*\*\s*(?:\n|$)", par)
        if cab:
            bloco = re.sub(r"\s*\(.*?\)\s*$", "", cab.group(1))
            par = par[cab.end():].strip()
        fala = re.sub(r"\[[^\]]*\]", "", par)
        fala = re.sub(r"\*\*(.+?)\*\*", r"\1", fala).replace("(pausa)", "").strip()
        if len(fala) > 3:
            saida.append((bloco, fala))
    return saida


def frases(texto):
    """Frases curtas (≤ 110 caracteres) para legenda de leitura fácil; corta em pontuação."""
    saida = []
    for frase in re.split(r"(?<=[.!?…])\s+", re.sub(r"\s+", " ", texto)):
        pedacos, atual = [], ""
        for trecho in re.split(r"(?<=[,;:—])\s+", frase):
            if atual and len(atual) + len(trecho) > 110:
                pedacos.append(atual)
                atual = trecho
            else:
                atual = f"{atual} {trecho}".strip()
        saida += pedacos + [atual]
    return [p for p in saida if len(p) > 1]


def assunto(bloco):
    b = re.sub(r"^BLOCO \d+\s*[—-]\s*", "", bloco.upper())
    return {"GANCHO": "DESTAQUE", "PROMESSA": "NESTA EDIÇÃO"}.get(b, b)


# ---------- imagens ----------
class Fotos:
    def __init__(self, pasta):
        self.pasta, self.cache, self.usadas = pasta, {}, {}
        self.s = requests.Session()
        self.s.headers.update(UA)

    def buscar(self, consulta):
        if consulta in self.cache:
            return self.cache[consulta]
        achadas = []
        try:
            r = self.s.get("https://commons.wikimedia.org/w/api.php", timeout=20, params=dict(
                action="query", generator="search", gsrsearch=f"{consulta} filetype:bitmap", gsrnamespace=6,
                gsrlimit=8, prop="imageinfo", iiprop="url|extmetadata|size", iiurlwidth=1920, format="json")).json()
            for p in sorted((r.get("query", {}).get("pages", {}) or {}).values(), key=lambda p: p.get("index", 99)):
                ii = p["imageinfo"][0]
                meta = ii.get("extmetadata", {})
                lic = meta.get("LicenseShortName", {}).get("value", "")
                # canal monetizado: só licenças que permitem uso comercial e edição (nada de NC/ND)
                if (not lic.startswith(LICENCAS_OK) or re.search(r"\bNC\b|\bND\b", lic)
                        or ii.get("width", 0) < 900 or ii["width"] < ii["height"] * 0.9):
                    continue
                autor = html.unescape(re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", ""))).strip()
                achadas.append({"url": ii["thumburl"], "credito": f"Foto: {autor[:60] or 'Wikimedia Commons'} · {lic} · Wikimedia Commons"})
        except Exception as erro:  # sem foto, o âncora assume
            print("commons:", consulta, erro)
        self.cache[consulta] = achadas
        return achadas

    def para(self, texto):
        for padrao, consulta in ENTIDADES:
            if re.search(padrao, texto, re.I):
                opcoes = self.buscar(consulta)
                if opcoes:
                    i = self.usadas.get(consulta, 0) % len(opcoes)
                    self.usadas[consulta] = self.usadas.get(consulta, 0) + 1
                    try:
                        return self.baixar(opcoes[i])
                    except Exception as erro:  # falha de rede: segue com o âncora
                        print("foto:", consulta, erro)
                        return None
        return None

    def baixar(self, foto):
        destino = self.pasta / (hashlib.sha1(foto["url"].encode()).hexdigest()[:16] + ".jpg")
        if not destino.exists():
            img = Image.open(io.BytesIO(self.s.get(foto["url"], timeout=30).content)).convert("RGB")
            preencher(img).save(destino, quality=90)
        return destino, foto["credito"]


def preencher(img):
    r = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x, y = (img.width - W) // 2, max(0, (img.height - H) // 3)
    return img.crop((x, y, x + W, y + H))


# ---------- composição ----------
def f(caminho, tam):
    return ImageFont.truetype(caminho, tam)


def quebrar(d, texto, fonte, largura):
    linhas, atual = [], ""
    for p in texto.split():
        t = f"{atual} {p}".strip()
        if d.textlength(t, font=fonte) <= largura:
            atual = t
        else:
            linhas.append(atual)
            atual = p
    return linhas + ([atual] if atual else [])


def legenda_curta(frase, limite=95):
    return [p.strip() for p in textwrap.wrap(frase, limite)]


def quadro(fundo, credito, manchete, assunto_txt, legenda, destino, eh_ancora):
    img = Image.open(fundo).convert("RGB")
    if not eh_ancora:
        img = Image.eval(img, lambda v: int(v * 0.82))
    base = img.convert("RGBA")
    cam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    # degradê inferior para leitura
    for i in range(420):
        d.line([(0, H - 420 + i), (W, H - 420 + i)], fill=(0, 8, 24, int(230 * i / 420)))
    # selo do jornal (canto superior esquerdo)
    fs = f(FB, 50)
    ls = d.textlength(MARCA, font=fs) + 48
    d.rectangle([60, 50, 60 + ls, 128], fill=VERMELHO)
    d.text((84, 62), MARCA, font=fs, fill=BRANCO)
    d.rectangle([60, 128, 60 + ls, 158], fill=AZUL)
    d.text((84, 131), SLOGAN, font=f(FB, 20), fill=CINZA)
    # legenda (o que está sendo falado): até 2 linhas, fonte reduz se precisar
    for tam in (46, 40, 34):
        fl = f(FB, tam)
        linhas_l = quebrar(d, legenda, fl, W - 280)
        if len(linhas_l) <= 2:
            break
    linhas_l = linhas_l[:3]
    alt_l = int(tam * 1.3)
    yl = H - 50 - alt_l * len(linhas_l)
    # manchete (qual notícia) e faixa do assunto, empilhadas acima da legenda
    fm = f(FB, 60)
    linhas_m = quebrar(d, manchete.upper(), fm, W - 200)[:2]
    fa = f(FB, 38)
    ya = yl - 30 - 60
    y0 = ya - 16 - 76 * len(linhas_m)
    d.rectangle([60, y0 - 12, W - 60, y0 + 76 * len(linhas_m) + 2], fill=AZUL + (235,))
    d.rectangle([60, y0 - 12, 76, y0 + 76 * len(linhas_m) + 2], fill=VERMELHO)
    for i, l in enumerate(linhas_m):
        d.text((100, y0 + i * 76), l, font=fm, fill=BRANCO)
    d.rectangle([60, ya, 100 + d.textlength(assunto_txt, font=fa) + 40, ya + 60], fill=VERMELHO + (245,))
    d.text((100, ya + 8), assunto_txt, font=fa, fill=BRANCO)
    for i, l in enumerate(linhas_l):
        largura = d.textlength(l, font=fl)
        x = (W - largura) / 2
        y = yl + i * alt_l
        d.rectangle([x - 18, y - 4, x + largura + 18, y + alt_l - 2], fill=(0, 0, 0, 185))
        d.text((x, y), l, font=fl, fill=(255, 236, 120))
    if credito:
        d.text((W - 60 - d.textlength(credito, font=f(FR, 20)), 60), credito, font=f(FR, 20), fill=CINZA)
    Image.alpha_composite(base, cam).convert("RGB").save(destino, quality=92)


def miniatura(fundo, texto, destino):
    img = Image.open(fundo).convert("RGB").resize((1280, 720))
    img = Image.eval(img, lambda v: int(v * 0.6))
    d = ImageDraw.Draw(img)
    fonte = f(FB, 118)
    linhas = quebrar(d, texto.strip('"“”').upper(), fonte, 1150)
    y = 360 - len(linhas) * 70
    for l in linhas:
        d.text((60, y), l, font=fonte, fill=BRANCO, stroke_width=6, stroke_fill=VERMELHO)
        y += 140
    d.rectangle([0, 640, 1280, 720], fill=VERMELHO)
    d.text((40, 652), MARCA, font=f(FB, 52), fill=BRANCO)
    img.save(destino, quality=90)


# ---------- áudio ----------
async def falar(texto, destino):
    for tentativa in range(4):
        try:
            await edge_tts.Communicate(texto, VOZ, rate=VELOCIDADE, pitch=TOM).save(str(destino))
            return
        except Exception:
            if tentativa == 3:
                raise
            await asyncio.sleep(3 * (tentativa + 1))


def duracao(arq):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(arq)], capture_output=True, text=True).stdout or 0)


def abertura(manchete):
    return ("Olá! Seja muito bem-vindo ao RADAR 360. "
            "Obrigado, de coração, pela sua presença e pela sua atenção — é por você que a gente trabalha todos os dias "
            "para trazer a informação checada, com fonte, do jeito que ela é. "
            "Agradeço também a cada pessoa que se inscreve, comenta e compartilha: vocês fazem este jornal. "
            f"E a notícia de agora é esta: {manchete}.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("saida")
    ap.add_argument("--ancora", required=True)
    ap.add_argument("--inicio", type=int, default=0, help="retomar a partir da frase N")
    a = ap.parse_args()
    md = Path(a.roteiro).read_text(encoding="utf-8")
    nome = Path(a.roteiro).stem
    out = Path(a.saida)
    tmp = out / f"{nome}_v2"
    (tmp / "fotos").mkdir(parents=True, exist_ok=True)
    manchete = re.sub(r"^\s*1\.\s*", "", secao(md, "Títulos").splitlines()[0]).strip()
    ancora = tmp / "fotos" / "ancora.jpg"
    preencher(Image.open(a.ancora).convert("RGB")).save(ancora, quality=92)
    fotos = Fotos(tmp / "fotos")

    itens = [("ABERTURA", s) for s in frases(abertura(manchete))]
    for bloco, fala in blocos(md):
        itens += [(bloco, s) for s in frases(fala)]

    creditos = set()
    for i, (bloco, frase) in enumerate(itens):
        if i < a.inicio or (tmp / f"{i:03}.mp4").exists():
            continue
        mp3, png, mp4 = tmp / f"{i:03}.mp3", tmp / f"{i:03}.png", tmp / f"{i:03}.mp4"
        asyncio.run(falar(frase, mp3))
        achou = None if bloco == "ABERTURA" else fotos.para(frase)
        fundo, credito = achou if achou else (ancora, "Apresentador virtual (imagem gerada por IA)")
        quadro(fundo, credito, manchete, assunto(bloco), frase, png, achou is None)
        # imagem fixa por frase (a troca de quadro a cada frase dá o ritmo); render rápido para o servidor grátis
        seg = duracao(mp3) + 0.25
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25", "-t", f"{seg:.2f}",
                        "-i", str(png), "-i", str(mp3),
                        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-af", "apad", "-t", f"{seg:.2f}", str(mp4)],
                       check=True)
    partes = sorted(tmp.glob("[0-9][0-9][0-9].mp4"))
    (tmp / "lista.txt").write_text("".join(f"file '{p.name}'\n" for p in partes))
    final = out / f"{nome}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "lista.txt"),
                    "-c", "copy", "-movflags", "+faststart", str(final)], check=True)
    fundo_mini = next((p for p in (tmp / "fotos").glob("*.jpg") if p.name != "ancora.jpg"), ancora)
    miniatura(fundo_mini, secao(md, "Texto da miniatura") or manchete, out / f"{nome}.jpg")
    print(json.dumps({"video": str(final), "frases": len(itens), "partes": len(partes),
                      "segundos": round(duracao(final))}))


if __name__ == "__main__":
    main()
