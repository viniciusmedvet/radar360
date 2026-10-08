"""Renderiza um roteiro (video-N.md) no padrão telejornal do RADAR365, sem custo de licença:

- Narração: voz neural pt-BR (edge-tts, pt-BR-AntonioNeural), frase a frase, para legenda sincronizada.
- Fundo: imagens reais, trocadas a cada frase: fotos e vídeos de licença livre do Wikimedia Commons
  (os mais recentes entre os relevantes), foto principal de páginas de fontes licenciadas ([FOTO: url | crédito])
  e trechos de vídeo ([TRECHO: ...]: YouTube só com licença Creative Commons conferida no download).
  Crédito sempre na tela e em video-N-creditos.txt. O apresentador-âncora aparece só na saudação.
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
MARCA = "RADAR365"
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
    (r"Mar Negro", "Black Sea coast"), (r"Romênia|Sfântu Gheorghe|Tulcea", "Danube Delta Sfantu Gheorghe"),
    (r"navio|cargueiro|tripulant", "general cargo ship"), (r"\bmilho\b", "maize field"),
    (r"Sumy", "Sumy city Ukraine"), (r"fábrica|farmacêutic|medicament|remédio", "pharmaceutical factory"),
    (r"Ghalibaf", "Mohammad Bagher Ghalibaf"), (r"Araghchi", "Abbas Araghchi"), (r"Pezeshkian", "Masoud Pezeshkian"),
    (r"bombardeiro|RAF Fairford|B-1", "B-1B Lancer"), (r"Omã", "Gulf of Oman tanker"),
    (r"Tarcísio", "Tarcísio de Freitas"), (r"Augusto Cury", "Augusto Cury"), (r"Congresso", "Congresso Nacional Brasília"),
    (r"\bSUS\b|hospital", "hospital Brazil"), (r"ANVISA", "Anvisa sede"),
    (r"Irkutsk|Shelekhov", "Irkutsk"), (r"Sibéria|Siberian", "Siberia landscape"), (r"Buriácia", "Buryatia"),
    (r"\bpeste\b|Yersinia", "Yersinia pestis"), (r"roedor|pulga", "marmot Siberia"), (r"Peskov|Kremlin", "Moscow Kremlin"),
    (r"laboratório|biossegurança|tubo de ensaio", "biosafety laboratory"),
    (r"Rubio", "Marco Rubio"), (r"Klitschko", "Vitali Klitschko"), (r"Pryluky|Chernihiv", "Pryluky"),
    (r"Flávio Dino|\bDino\b", "Flávio Dino"), (r"Cármen Lúcia", "Cármen Lúcia"), (r"Fachin", "Edson Fachin"),
    (r"Zanin", "Cristiano Zanin"), (r"Nunes Marques", "Nunes Marques"), (r"Federal Reserve|\bFed\b", "Marriner S. Eccles Federal Reserve Board Building"),
    (r"malária|Plasmodium", "Plasmodium vivax"), (r"Catar|Madinat", "Qatar coast"),
    (r"clínica|consultório", "veterinary clinic"), (r"juros|DI\b|Selic", "Banco Central do Brasil edifício"),
]
LICENCAS_OK = ("CC BY", "CC0", "Public domain", "PD", "CC-BY")
# Páginas de onde [FOTO: url | crédito] pode puxar a imagem principal (licença de uso comercial com crédito,
# conforme config/fontes-midia.json). Qualquer outro domínio é ignorado.
DOMINIOS_FOTO = ("agenciabrasil.ebc.com.br", "kremlin.ru", "whitehouse.gov", "defense.gov", "dvidshub.net",
                 "state.gov", "stf.jus.br", "senado.leg.br", "camara.leg.br", "commons.wikimedia.org")
# Vídeo direto (arquivo .mp4/.webm) só destes domínios; do YouTube, só com licença CC BY conferida no download.
DOMINIOS_VIDEO = ("dvidshub.net", "kremlin.ru", "upload.wikimedia.org", "defense.gov", "whitehouse.gov")
ANCORA_CREDITO = "Apresentador virtual (imagem gerada por IA)"


def secao(md, titulo):
    m = re.search(rf"^## {re.escape(titulo)}[^\n]*\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def marcas(par):
    """Deixas visuais do parágrafo, na ordem: busca, pessoa, foto de página licenciada e trecho de vídeo."""
    out = []
    for m in re.finditer(r"\[(B-ROLL|FOTO|TRECHO):([^\]]*)\]", par):
        tipo, corpo = m.group(1), m.group(2)
        if tipo == "B-ROLL":
            k = re.search(r"\|\s*(busca|pessoa):\s*(.+)$", corpo)
            if k:
                out.append({"tipo": k.group(1), "q": k.group(2).strip()})
        elif tipo == "FOTO":
            partes = [p.strip() for p in corpo.split("|")]
            if partes and partes[0].startswith("http") and len(partes) > 1:
                out.append({"tipo": "foto", "url": partes[0], "credito": partes[1]})
        else:  # TRECHO: fonte · título · data · URL · licença [| início: SS]
            url = re.search(r"https?://\S+?(?=\s*[·|]|\s*$)", corpo)
            ini = re.search(r"in[ií]cio:\s*(\d+)", corpo)
            if url:
                campos = [c.strip() for c in corpo.split("|")[0].split("·")]
                out.append({"tipo": "trecho", "url": url.group(0), "inicio": int(ini.group(1)) if ini else 0,
                            "credito": "Trecho: " + " · ".join(c for c in campos if not c.startswith("http"))})
    return out


def blocos(md):
    """[(bloco, texto, deixas)] do roteiro narrado, sem deixas visuais nem marcação na fala."""
    bloco, saida = "ABERTURA", []
    for par in re.split(r"\n\s*\n", secao(md, "Roteiro narrado")):
        par = par.strip()
        cab = re.match(r"\*\*(.+?)\*\*\s*(?:\n|$)", par)
        if cab:
            bloco = re.sub(r"\s*\(.*?\)\s*$", "", cab.group(1))
            par = par[cab.end():].strip()
        deixas = marcas(par)
        fala = re.sub(r"\[[^\]]*\]", "", par)
        fala = re.sub(r"\*\*(.+?)\*\*", r"\1", fala).replace("(pausa)", "").strip()
        if len(fala) > 3:
            saida.append((bloco, fala, deixas))
        elif deixas and saida:  # deixa solta antes do próximo parágrafo: vale para ele
            saida.append((bloco, "", deixas))
    # junta deixas soltas ao parágrafo seguinte
    # parágrafo sem deixa herda as do anterior, para a imagem continuar mudando a cada frase
    final, pend, herdada = [], [], []
    for b, fala, d in saida:
        if not fala:
            pend += d
            continue
        d = pend + d or herdada
        herdada, pend = d, []
        final.append((b, fala, d))
    return final


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


# ---------- imagens e trechos ----------
class Midia:
    """Busca e baixa fotos e vídeos de licença livre. Cada item: {"tipo": "foto"|"video", "arq", "credito"}."""

    def __init__(self, pasta):
        self.pasta, self.cache, self.giro = pasta, {}, {}
        self.s = requests.Session()
        self.s.headers.update(UA)

    def _commons(self, consulta, filtro, limite):
        achadas = []
        try:
            r = self.s.get("https://commons.wikimedia.org/w/api.php", timeout=20, params=dict(
                action="query", generator="search", gsrsearch=f"{consulta} {filtro}", gsrnamespace=6,
                gsrlimit=limite, prop="imageinfo", iiprop="url|extmetadata|size|mediatype|timestamp",
                iiurlwidth=1920, format="json")).json()
            for p in sorted((r.get("query", {}).get("pages", {}) or {}).values(), key=lambda p: p.get("index", 99)):
                ii = p["imageinfo"][0]
                meta = ii.get("extmetadata", {})
                lic = meta.get("LicenseShortName", {}).get("value", "")
                # canal monetizado: só licenças que permitem uso comercial e edição (nada de NC/ND)
                if not lic.startswith(LICENCAS_OK) or re.search(r"\bNC\b|\bND\b", lic):
                    continue
                autor = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")))).strip()
                credito = f"{autor[:60] or 'Wikimedia Commons'} · {lic} · Wikimedia Commons"
                data = (meta.get("DateTimeOriginal", {}).get("value") or ii.get("timestamp", ""))[:40]
                if filtro == "filetype:video":
                    if ii.get("size", 0) > 80_000_000 or ii.get("width", 0) < 640:
                        continue
                    achadas.append({"tipo": "video", "url": ii["url"], "credito": "Vídeo: " + credito, "data": data})
                else:
                    if ii.get("width", 0) < 900 or ii["width"] < ii["height"] * 0.9:
                        continue
                    achadas.append({"tipo": "foto", "url": ii["thumburl"], "credito": "Foto: " + credito, "data": data})
        except Exception as erro:
            print("commons:", consulta, erro)
        # entre as relevantes, as mais recentes primeiro
        return sorted(achadas, key=lambda a: re.sub(r"\D", "", a["data"])[:8] or "0", reverse=True)

    def busca(self, consulta, com_video=True):
        chave = (consulta, com_video)
        if chave not in self.cache:
            fotos = self._commons(consulta, "filetype:bitmap", 10)
            videos = self._commons(consulta, "filetype:video", 4) if com_video else []
            mistura = []
            for i in range(max(len(fotos), len(videos))):
                mistura += videos[i:i + 1] + fotos[i:i + 1]
            self.cache[chave] = mistura
        return self.cache[chave]

    def pagina(self, item):
        """[FOTO: url | crédito]: imagem principal (og:image) de uma página de fonte licenciada."""
        if not any(d in item["url"] for d in DOMINIOS_FOTO):
            print("foto fora da lista de fontes permitidas:", item["url"])
            return []
        try:
            t = self.s.get(item["url"], timeout=25).text
            m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', t) or \
                re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', t)
            if m:
                return [{"tipo": "foto", "url": html.unescape(m.group(1)), "credito": "Foto: " + item["credito"]}]
        except Exception as erro:
            print("pagina:", item["url"], erro)
        return []

    def trecho(self, item):
        """[TRECHO: ...]: YouTube só com licença Creative Commons conferida; arquivo direto só de domínio permitido."""
        url = item["url"]
        destino = self.pasta / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".mp4")
        if destino.exists():
            return [{"tipo": "video", "arq": destino, "credito": item["credito"], "inicio": item["inicio"]}]
        try:
            if "youtube.com" in url or "youtu.be" in url:
                info = json.loads(subprocess.run(["yt-dlp", "-J", "--no-warnings", url], capture_output=True,
                                                 text=True, timeout=90).stdout or "{}")
                if "creative commons" not in (info.get("license") or "").lower():
                    print("trecho recusado (sem licença CC no YouTube):", url, info.get("license"))
                    return []
                ini = item["inicio"]
                subprocess.run(["yt-dlp", "-q", "-f", "bv*[height<=720][ext=mp4]+ba/b[height<=720]/b",
                                "--merge-output-format", "mp4", "--download-sections", f"*{ini}-{ini + 40}",
                                "-o", str(destino), url], timeout=240, check=True)
                return [{"tipo": "video", "arq": destino, "credito": item["credito"], "inicio": 0}]
            if any(d in url for d in DOMINIOS_VIDEO):
                destino.write_bytes(self.s.get(url, timeout=120).content)
                return [{"tipo": "video", "arq": destino, "credito": item["credito"], "inicio": item["inicio"]}]
            print("trecho fora da lista de fontes permitidas:", url)
        except Exception as erro:
            print("trecho:", url, erro)
        return []

    def resolver(self, deixa):
        if deixa["tipo"] == "foto":
            return self.pagina(deixa)
        if deixa["tipo"] == "trecho":
            return self.trecho(deixa)
        return self.busca(deixa["q"], com_video=deixa["tipo"] == "busca")

    def entidade(self, texto):
        for padrao, consulta in ENTIDADES:
            if re.search(padrao, texto, re.I):
                return consulta
        return None

    def proximo(self, chave, opcoes):
        """Gira entre as opções de uma mesma chave e baixa; pula as que falharem."""
        for _ in range(len(opcoes)):
            i = self.giro.get(chave, 0) % len(opcoes)
            self.giro[chave] = self.giro.get(chave, 0) + 1
            pronto = self.baixar(opcoes[i])
            if pronto:
                return pronto
        return None

    def baixar(self, item):
        if item.get("arq"):
            return item
        try:
            ext = ".jpg" if item["tipo"] == "foto" else Path(item["url"].split("?")[0]).suffix or ".webm"
            destino = self.pasta / (hashlib.sha1(item["url"].encode()).hexdigest()[:16] + ext)
            if not destino.exists():
                conteudo = self.s.get(item["url"], timeout=90).content
                if item["tipo"] == "foto":
                    preencher(Image.open(io.BytesIO(conteudo)).convert("RGB")).save(destino, quality=90)
                else:
                    destino.write_bytes(conteudo)
                    if duracao(destino) < 2:
                        return None
            return {**item, "arq": destino, "inicio": item.get("inicio", 0)}
        except Exception as erro:
            print("baixar:", item.get("url"), erro)
            return None


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


def camada(credito, manchete, assunto_txt, legenda):
    """Grafismo do telejornal em camada transparente (vai por cima de foto ou de vídeo)."""
    cam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    for i in range(420):  # degradê inferior para leitura
        d.line([(0, H - 420 + i), (W, H - 420 + i)], fill=(0, 8, 24, int(230 * i / 420)))
    fs = f(FB, 50)
    ls = d.textlength(MARCA, font=fs) + 48
    d.rectangle([60, 50, 60 + ls, 128], fill=VERMELHO)
    d.text((84, 62), MARCA, font=fs, fill=BRANCO)
    d.rectangle([60, 128, 60 + ls, 158], fill=AZUL)
    d.text((84, 131), SLOGAN, font=f(FB, 20), fill=CINZA)
    for tam in (46, 40, 34):
        fl = f(FB, tam)
        linhas_l = quebrar(d, legenda, fl, W - 280)
        if len(linhas_l) <= 2:
            break
    linhas_l = linhas_l[:3]
    alt_l = int(tam * 1.3)
    yl = H - 50 - alt_l * len(linhas_l)
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
        fc = f(FR, 22)
        credito = re.sub(r"\s+", " ", credito).strip()[:150]  # crédito do Commons pode vir com quebra de linha
        lc = d.textlength(credito, font=fc)
        d.rectangle([W - 72 - lc, 52, W - 48, 86], fill=(0, 0, 0, 160))
        d.text((W - 60 - lc, 56), credito, font=fc, fill=BRANCO)
    return cam


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
    try:
        return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                     str(arq)], capture_output=True, text=True).stdout or 0)
    except ValueError:
        return 0.0


def abertura(manchete):
    return ("Olá! Seja muito bem-vindo ao RADAR365. "
            "Obrigado, de coração, pela sua presença e pela sua atenção — é por você que a gente trabalha todos os dias "
            "para trazer a informação checada, com fonte, do jeito que ela é. "
            "Agradeço também a cada pessoa que se inscreve, comenta e compartilha: vocês fazem este jornal. "
            f"E a notícia de agora é esta: {manchete}.")


ENC = ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-r", "25",
       "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", "-af", "apad"]


def segmento(item, png, mp3, seg, mp4, avanco=0.0):
    if item and item["tipo"] == "video":
        ini = item.get("inicio", 0) + avanco
        total = duracao(item["arq"])
        if total and ini + 1 > total:
            ini = 0
        filtro = ("[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=25,"
                  "eq=brightness=-0.07,format=rgba[b];[b][1:v]overlay=0:0,format=yuv420p[v]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-ss", f"{ini:.2f}",
                        "-i", str(item["arq"]), "-i", str(png), "-i", str(mp3), "-filter_complex", filtro,
                        "-map", "[v]", "-map", "2:a", "-t", f"{seg:.2f}", *ENC, "-t", f"{seg:.2f}", str(mp4)],
                       check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25", "-t", f"{seg:.2f}",
                        "-i", str(png), "-i", str(mp3), "-tune", "stillimage", *ENC, "-t", f"{seg:.2f}", str(mp4)],
                       check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("saida")
    ap.add_argument("--ancora", required=True)
    a = ap.parse_args()
    md = Path(a.roteiro).read_text(encoding="utf-8")
    nome = Path(a.roteiro).stem
    out = Path(a.saida)
    tmp = out / f"{nome}_v3"
    (tmp / "midia").mkdir(parents=True, exist_ok=True)
    manchete = re.sub(r"^\s*1\.\s*", "", secao(md, "Títulos").splitlines()[0]).strip()
    ancora = tmp / "midia" / "ancora.jpg"
    preencher(Image.open(a.ancora).convert("RGB")).save(ancora, quality=92)
    ancora_item = {"tipo": "foto", "arq": ancora, "credito": ANCORA_CREDITO}
    midia = Midia(tmp / "midia")

    pars = blocos(md)
    # (bloco, frase, deixas do parágrafo, id do parágrafo); a abertura usa as imagens do primeiro parágrafo
    itens = [("ABERTURA", s, pars[0][2] if pars else [], 0) for s in frases(abertura(manchete))]
    for k, (bloco, fala, deixas) in enumerate(pars):
        itens += [(bloco, s, deixas, k) for s in frases(fala)]

    creditos, usados, n_ancora, avanco = [], [], 0, {}
    for i, (bloco, frase, deixas, k) in enumerate(itens):
        mp3, png, mp4 = tmp / f"{i:03}.mp3", tmp / f"{i:03}.png", tmp / f"{i:03}.mp4"
        asyncio.run(falar(frase, mp3))
        seg = duracao(mp3) + 0.25
        item = None
        if i == 0:  # o âncora só aparece na saudação
            item = ancora_item
        if not item:  # pessoa/lugar citado nesta frase
            q = midia.entidade(frase)
            if q:
                item = midia.proximo(("ent", q), midia.busca(q, com_video=False) or [])
        if not item and deixas:  # deixas visuais do parágrafo (busca, foto de fonte, trecho)
            opcoes = [o for d in deixas for o in midia.resolver(d)]
            if opcoes:
                item = midia.proximo(("par", json.dumps(deixas, sort_keys=True)), opcoes)
        if not item and not usados:  # começo sem imagem: adianta a primeira imagem real dos parágrafos seguintes
            for _, _, d_seg in pars[k + 1:k + 6]:
                opcoes = [o for d in d_seg for o in midia.resolver(d)]
                item = midia.proximo(("par", json.dumps(d_seg, sort_keys=True)), opcoes) if opcoes else None
                if item:
                    break
        if not item and usados:  # repete a última imagem real do vídeo antes de cair no âncora
            item = usados[-1]
        if not item:
            item, n_ancora = ancora_item, n_ancora + 1
        if item is not ancora_item:
            usados.append(item)
            if item["credito"] not in creditos:
                creditos.append(item["credito"])
        if item["tipo"] == "foto":
            fundo = Image.open(item["arq"]).convert("RGB")
            if item is not ancora_item:
                fundo = Image.eval(fundo, lambda v: int(v * 0.82))
            Image.alpha_composite(fundo.convert("RGBA"), camada(item["credito"], manchete, assunto(bloco), frase)) \
                .convert("RGB").save(png.with_suffix(".jpg"), quality=92)
            segmento(item, png.with_suffix(".jpg"), mp3, seg, mp4)
        else:
            camada(item["credito"], manchete, assunto(bloco), frase).save(png)
            try:
                # o mesmo vídeo continua de onde parou quando volta a aparecer
                segmento(item, png, mp3, seg, mp4, avanco.get(item["arq"], 0.0))
            except subprocess.CalledProcessError as erro:  # vídeo ilegível: usa o âncora nesta frase
                print("segmento de vídeo falhou:", item["arq"], erro)
                Image.alpha_composite(Image.open(ancora).convert("RGBA"),
                                      camada(ANCORA_CREDITO, manchete, assunto(bloco), frase)).convert("RGB") \
                    .save(png.with_suffix(".jpg"), quality=92)
                segmento(ancora_item, png.with_suffix(".jpg"), mp3, seg, mp4)
            avanco[item["arq"]] = avanco.get(item["arq"], 0.0) + seg

    partes = sorted(tmp.glob("[0-9][0-9][0-9].mp4"))
    (tmp / "lista.txt").write_text("".join(f"file '{p.name}'\n" for p in partes))
    final = out / f"{nome}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "lista.txt"),
                    "-c", "copy", "-movflags", "+faststart", str(final)], check=True)
    fotos_reais = [u["arq"] for u in usados if u["tipo"] == "foto"]
    miniatura(fotos_reais[0] if fotos_reais else ancora, secao(md, "Texto da miniatura") or manchete, out / f"{nome}.jpg")
    (out / f"{nome}-creditos.txt").write_text("Créditos de imagens e trechos:\n" + "\n".join(f"- {c}" for c in creditos),
                                             encoding="utf-8")
    n_video = sum(1 for u in usados if u["tipo"] == "video")
    print(json.dumps({"video": str(final), "frases": len(itens), "segundos": round(duracao(final)),
                      "ancora": n_ancora + 1, "fotos": len(usados) - n_video, "trechos_video": n_video}))


if __name__ == "__main__":
    main()
