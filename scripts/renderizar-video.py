"""Renderiza um roteiro (video-N.md) no padrão telejornal do RADAR365, sem custo de licença.

Saídas, cada uma no limite de cada plataforma:
- video-N.mp4            1920x1080, duração livre: YouTube e Facebook.
- video-N-vertical.mp4   1080x1920, até ~58 s, começa no gancho: Reels, TikTok e Shorts.
- video-N.jpg            miniatura 1280x720 (YouTube).
- video-N-capitulos.txt  capítulos do YouTube (00:00 ...) para colar na descrição.

Imagem de fundo de cada frase, em ordem de prioridade:
1. Trecho indicado no roteiro: [TRECHO: ... https://commons.wikimedia.org/wiki/File:... · licença].
2. Pessoa ou lugar citado na frase (lista ENTIDADES) ou marcado com "pessoa:" no roteiro:
   só Wikimedia Commons, nunca banco genérico (não trocar uma pessoa real por figurante).
3. Busca do roteiro "[B-ROLL: ... | busca: termo em inglês]": vídeos e fotos de bancos livres
   (Pexels, se houver PEXELS_API_KEY; Wikimedia Commons sempre).
4. Continua o clipe anterior; sem nada, entra o apresentador-âncora.
Vídeo tem prioridade sobre foto; foto ganha movimento lento (pan) para não ficar parada.

Uso: python renderizar-video.py video-1.md saida_dir --ancora ancora.jpg [--teste]
"""
import argparse, asyncio, hashlib, html, io, json, os, re, subprocess, textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

LAYOUTS = {"h": (1920, 1080), "v": (1080, 1920)}
VERTICAL_MAX = 58.0  # segundos: cabe em Reels, TikTok e Shorts
MARCA = "RADAR365"
SLOGAN = "O MUNDO COMO ELE É"
CANAL = "RADAR365 | Ciência e Mundo"
AZUL, AZUL2, VERMELHO, BRANCO, CINZA = (6, 28, 64), (12, 60, 130), (214, 31, 38), (255, 255, 255), (205, 212, 224)
AMARELO = (255, 236, 120)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
VOZ, VELOCIDADE, TOM = "pt-BR-AntonioNeural", "-6%", "-2Hz"
UA = {"User-Agent": "Radar365Bot/1.0 (jornalismo; viniciusmedvet@gmail.com)"}
FPS = 25
CLIPE_MAX = 12.0  # segundos máximos no mesmo clipe antes de trocar

# Termo na fala -> (busca, genérico?). Genérico = pode usar banco de vídeos (cena, objeto, profissão).
# Pessoas e lugares específicos: só Wikimedia Commons.
ENTIDADES = [
    (r"\bZelensk", "Volodymyr Zelensky", False), (r"\bPutin\b", "Vladimir Putin", False),
    (r"\bTrump\b", "Donald Trump 2025", False), (r"\bLavrov\b", "Sergey Lavrov", False),
    (r"\bKiev\b|\bKyiv\b", "Kyiv Maidan Nezalezhnosti", False), (r"\bPatriot\b", "MIM-104 Patriot launcher", False),
    (r"Assembleia-Geral|\bONU\b", "United Nations General Assembly hall", False),
    (r"Ormuz|Hormuz", "Strait of Hormuz", False), (r"Guarda Revolucionária|IRGC", "Islamic Revolutionary Guard Corps", False),
    (r"\bIrã\b|Teerã", "Tehran skyline", False), (r"Departamento de Estado", "Harry S Truman Building", False),
    (r"Alexandre de Moraes|\bMoraes\b", "Alexandre de Moraes", False), (r"Mendonça", "André Mendonça", False),
    (r"Toffoli", "Dias Toffoli", False), (r"Gilmar", "Gilmar Mendes", False), (r"\bFux\b", "Luiz Fux", False),
    (r"Vorcaro|Banco Master", "Banco Master", False), (r"\bBRB\b", "Banco de Brasília", False),
    (r"\bSTF\b|Supremo", "Supremo Tribunal Federal plenário", False),
    (r"Praça dos Três Poderes", "Praça dos Três Poderes", False), (r"Congresso|Câmara dos Deputados", "Congresso Nacional Brasília", False),
    (r"\bLula\b", "Luiz Inácio Lula da Silva 2025", False), (r"Flávio Bolsonaro", "Flávio Bolsonaro", False),
    (r"Banco Central", "Banco Central do Brasil edifício", False), (r"Ibovespa|\bB3\b", "B3 Brasil Bolsa Balcão", False),
    (r"\bOMS\b|Organização Mundial da Saúde", "World Health Organization headquarters", False),
    (r"\bANVISA\b|Anvisa", "Anvisa sede Brasília", False),
    # cenas genéricas (banco de vídeos permitido)
    (r"fertilizant|adubo|lavoura|safra", "soybean harvest", True), (r"\bporto\b|portos|contêiner", "container port ship", True),
    (r"petroleiro|barril|petróleo", "oil tanker ship", True), (r"combustível|posto|diesel|gasolina", "gas station fuel pump", True),
    (r"míssil|mísseis|drone", "military drone", True), (r"dólar|câmbio", "dollar banknotes", True),
    (r"inflação|supermercado|preço", "supermarket shopping", True), (r"urna|eleiç|eleitor", "voting ballot", True),
    (r"\bgatos?\b|felino", "cat veterinary clinic", True), (r"\bcães\b|\bcão\b|cachorro|canino", "dog veterinary clinic", True),
    (r"veterinári", "veterinarian examining pet", True), (r"ração|alimento|nutri|dieta", "pet food bowl", True),
    (r"obesidade|sobrepeso|escore corporal", "overweight dog", True), (r"\brim\b|renal|rins", "kidney anatomy medical", True),
    (r"vacina", "vaccine injection", True), (r"bactéria|antimicrobian|antibiótic", "bacteria microscope", True),
    (r"vírus|viral|zoonose", "virus microscope", True), (r"hospital|UTI|internação", "hospital corridor", True),
    (r"enfermeir", "nurse hospital", True), (r"médic", "doctor patient", True), (r"laboratório|pesquisador", "scientist laboratory", True),
    (r"\bDNA\b|genétic|genoma", "DNA helix", True), (r"inteligência artificial|\bIA\b|algoritmo", "artificial intelligence technology", True),
    (r"célula|celular", "cells microscope", True), (r"exame|diagnóstic", "medical diagnosis", True),
]
LICENCAS_OK = ("CC BY", "CC0", "Public domain", "PD", "CC-BY", "Domínio público")


# ---------- roteiro ----------
def secao(md, titulo):
    m = re.search(rf"^## {re.escape(titulo)}[^\n]*\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def marcas(par):
    """Pistas visuais de um parágrafo: buscas genéricas, pessoas e arquivos do Commons."""
    m = {"buscas": [], "pessoas": [], "arquivos": []}
    for dentro in re.findall(r"\[([^\]]+)\]", par):
        m["buscas"] += [b.strip(' "“”') for b in re.findall(r"busca:\s*([^|\]]+)", dentro, re.I)]
        m["pessoas"] += [p.strip(' "“”') for p in re.findall(r"pessoa:\s*([^|\]]+)", dentro, re.I)]
        m["arquivos"] += re.findall(r"commons\.wikimedia\.org/wiki/(File:[^\s·|\]]+)", dentro)
    return m


def blocos(md):
    """[(bloco, texto, marcas)] do roteiro narrado. Marcas soltas valem para o parágrafo seguinte."""
    bloco, saida, pendentes = "ABERTURA", [], {"buscas": [], "pessoas": [], "arquivos": []}
    for par in re.split(r"\n\s*\n", secao(md, "Roteiro narrado")):
        par = par.strip()
        cab = re.match(r"\*\*(.+?)\*\*\s*(?:\n|$)", par)
        if cab:
            bloco = re.sub(r"\s*\(.*?\)\s*$", "", cab.group(1))
            par = par[cab.end():].strip()
        m = marcas(par)
        for k in pendentes:
            pendentes[k] += m[k]
        fala = re.sub(r"\[[^\]]*\]", "", par)
        fala = re.sub(r"\*\*(.+?)\*\*", r"\1", fala).replace("(pausa)", "").strip()
        if len(fala) > 3:
            saida.append((bloco, fala, pendentes))
            pendentes = {"buscas": [], "pessoas": [], "arquivos": []}
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


# ---------- mídia (vídeos e fotos de licença livre) ----------
def licenca_ok(lic):
    return lic.startswith(LICENCAS_OK) and not re.search(r"\bNC\b|\bND\b", lic)


class Midia:
    def __init__(self, pasta, teste=False):
        self.pasta, self.teste, self.cache, self.usadas = pasta, teste, {}, {}
        self.s = requests.Session()
        self.s.headers.update(UA)
        self.pexels = os.environ.get("PEXELS_API_KEY", "")

    # --- fontes ---
    def _commons(self, consulta, tipo):
        filtro = "filetype:video" if tipo == "video" else "filetype:bitmap"
        prop = "videoinfo" if tipo == "video" else "imageinfo"
        r = self.s.get("https://commons.wikimedia.org/w/api.php", timeout=20, params={
            "action": "query", "generator": "search", "gsrsearch": f"{consulta} {filtro}", "gsrnamespace": 6,
            "gsrlimit": 8, "prop": prop, "format": "json", "iiurlwidth": 1920,
            ("viprop" if tipo == "video" else "iiprop"): "url|extmetadata|size" + ("|derivatives" if tipo == "video" else "")}).json()
        return [self._item_commons(p, tipo) for p in sorted((r.get("query", {}).get("pages", {}) or {}).values(),
                                                              key=lambda p: p.get("index", 99))]

    def _item_commons(self, p, tipo):
        info = (p.get("videoinfo") or p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        if not licenca_ok(lic):
            return None
        autor = html.unescape(re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", ""))).strip()[:50] or "Wikimedia Commons"
        if tipo == "video":
            if float(info.get("duration") or 0) < 4:
                return None
            opcoes = [d for d in info.get("derivatives", []) if re.search(r"webm|mp4", d.get("type", ""))
                      and 360 <= int(d.get("height") or 0) <= 1080]
            opcoes.sort(key=lambda d: abs(int(d.get("height") or 0) - 720))
            url = opcoes[0]["src"] if opcoes else (info["url"] if info.get("size", 0) < 80e6 else None)
            if not url:
                return None
            return {"tipo": "video", "url": url, "credito": f"Vídeo: {autor} · {lic} · Wikimedia Commons"}
        if info.get("width", 0) < 900:
            return None
        return {"tipo": "foto", "url": info.get("thumburl") or info["url"], "credito": f"Foto: {autor} · {lic} · Wikimedia Commons"}

    def _pexels(self, consulta, tipo):
        if not self.pexels:
            return []
        cab = {"Authorization": self.pexels}
        if tipo == "video":
            r = self.s.get("https://api.pexels.com/videos/search", headers=cab, timeout=20,
                           params={"query": consulta, "per_page": 8, "size": "medium"}).json()
            saida = []
            for v in r.get("videos", []):
                arqs = [a for a in v.get("video_files", []) if a.get("file_type") == "video/mp4" and (a.get("height") or 0) >= 720]
                arqs.sort(key=lambda a: abs((a.get("width") or 0) - 1920))
                if arqs and (v.get("duration") or 0) >= 4:
                    saida.append({"tipo": "video", "url": arqs[0]["link"],
                                  "credito": f"Vídeo: {v.get('user', {}).get('name', 'Pexels')[:40]} · Pexels"})
            return saida
        r = self.s.get("https://api.pexels.com/v1/search", headers=cab, timeout=20,
                       params={"query": consulta, "per_page": 8}).json()
        return [{"tipo": "foto", "url": f["src"]["large2x"], "credito": f"Foto: {f.get('photographer', 'Pexels')[:40]} · Pexels"}
                for f in r.get("photos", [])]

    def arquivo_commons(self, titulo):
        r = self.s.get("https://commons.wikimedia.org/w/api.php", timeout=20, params={
            "action": "query", "titles": titulo, "prop": "videoinfo|imageinfo", "format": "json", "iiurlwidth": 1920,
            "viprop": "url|extmetadata|size|derivatives", "iiprop": "url|extmetadata|size"}).json()
        paginas = list((r.get("query", {}).get("pages", {}) or {}).values())
        if not paginas:
            return None
        return self._item_commons(paginas[0], "video" if paginas[0].get("videoinfo") else "foto")

    def buscar(self, consulta, generico):
        chave = (consulta, generico)
        if chave not in self.cache:
            achados = []
            fontes = [("pexels", "video"), ("commons", "video"), ("commons", "foto"), ("pexels", "foto")] if generico \
                else [("commons", "video"), ("commons", "foto")]
            for fonte, tipo in fontes:
                try:
                    achados += [x for x in (self._pexels if fonte == "pexels" else self._commons)(consulta, tipo) if x]
                except Exception as erro:  # sem mídia, segue para a próxima fonte
                    print("busca:", fonte, tipo, consulta, erro)
            self.cache[chave] = achados
        return self.cache[chave]

    def proximo(self, consulta, generico):
        opcoes = self.buscar(consulta, generico)
        if not opcoes:
            return None
        i = self.usadas.get(consulta, 0)
        self.usadas[consulta] = i + 1
        return self.baixar(opcoes[i % len(opcoes)])

    def baixar(self, item):
        if not item:
            return None
        ext = ".mp4" if item["tipo"] == "video" else ".jpg"
        destino = self.pasta / (hashlib.sha1(item["url"].encode()).hexdigest()[:16] + ext)
        try:
            if not destino.exists():
                conteudo = self.s.get(item["url"], timeout=90).content
                if item["tipo"] == "video":
                    bruto = destino.with_suffix(".bruto")
                    bruto.write_bytes(conteudo)
                    # normaliza: 25 fps, até 30 s, sem áudio (a narração é a trilha)
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(bruto), "-t", "30", "-an",
                                    "-vf", f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps={FPS}",
                                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(destino)], check=True)
                    bruto.unlink()
                else:
                    Image.open(io.BytesIO(conteudo)).convert("RGB").save(destino, quality=92)
            return {"tipo": item["tipo"], "arq": destino, "credito": item["credito"],
                    "dur": duracao(destino) if item["tipo"] == "video" else 0}
        except Exception as erro:  # falha de rede ou arquivo corrompido: segue sem esta mídia
            print("download:", item["url"][:80], erro)
            return None

    def para(self, frase, pistas, anterior):
        """Escolhe a mídia da frase seguindo a ordem de prioridade descrita no topo do arquivo."""
        if self.teste:
            return self._teste(frase)
        while pistas["arquivos"]:
            m = self.baixar(self.arquivo_commons(pistas["arquivos"].pop(0)))
            if m:
                return m
        for padrao, consulta, generico in ENTIDADES:
            if re.search(padrao, frase, re.I):
                m = self.proximo(consulta, generico)
                if m:
                    return m
        for consulta in pistas["pessoas"]:
            m = self.proximo(consulta, False)
            if m:
                return m
        if anterior and anterior["tipo"] != "ancora" and anterior.get("usado", 0) < CLIPE_MAX:
            return anterior  # continua o mesmo clipe/foto
        for consulta in pistas["buscas"][-1:] + pistas["buscas"][:-1]:
            pistas["buscas"].append(pistas["buscas"].pop(0))  # rodízio entre as buscas do parágrafo
            m = self.proximo(consulta, True)
            if m:
                return m
        return None

    def _teste(self, frase):
        """Mídia sintética para testar a montagem sem rede."""
        n = len(frase) % 3
        destino = self.pasta / f"teste{n}.{'mp4' if n else 'jpg'}"
        if not destino.exists():
            if n:
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                f"testsrc2=size=1280x720:rate={FPS}:duration=8", "-c:v", "libx264", "-preset", "ultrafast",
                                str(destino)], check=True)
            else:
                Image.new("RGB", (1600, 1000), (30, 90, 60)).save(destino)
        return {"tipo": "video" if n else "foto", "arq": destino, "credito": "Mídia de teste",
                "dur": 8.0 if n else 0}


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


def preencher(img, w, h):
    r = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x, y = (img.width - w) // 2, max(0, (img.height - h) // 3)
    return img.crop((x, y, x + w, y + h))


def selo(d, x, y, escala=1.0):
    fs = f(FB, int(50 * escala))
    ls = d.textlength(MARCA, font=fs) + 48 * escala
    d.rectangle([x, y, x + ls, y + 78 * escala], fill=VERMELHO)
    d.text((x + 24 * escala, y + 12 * escala), MARCA, font=fs, fill=BRANCO)
    d.rectangle([x, y + 78 * escala, x + ls, y + 108 * escala], fill=AZUL)
    d.text((x + 24 * escala, y + 81 * escala), SLOGAN, font=f(FB, int(20 * escala)), fill=CINZA)


def camada(layout, credito, manchete, assunto_txt, legenda, destino):
    """Tudo o que fica por cima da imagem (selo, manchete, assunto, legenda, crédito), em PNG transparente."""
    W, H = LAYOUTS[layout]
    cam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    if layout == "h":
        for i in range(420):  # degradê inferior para leitura
            d.line([(0, H - 420 + i), (W, H - 420 + i)], fill=(0, 8, 24, int(230 * i / 420)))
        selo(d, 60, 50)
        for tam in (46, 40, 34):
            fl = f(FB, tam)
            linhas_l = quebrar(d, legenda, fl, W - 280)
            if len(linhas_l) <= 2:
                break
        linhas_l = linhas_l[:3]
        alt_l = int(tam * 1.3)
        yl = H - 50 - alt_l * len(linhas_l)
        fm, fa = f(FB, 60), f(FB, 38)
        linhas_m = quebrar(d, manchete.upper(), fm, W - 200)[:2]
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
            x, y = (W - largura) / 2, yl + i * alt_l
            d.rectangle([x - 18, y - 4, x + largura + 18, y + alt_l - 2], fill=(0, 0, 0, 185))
            d.text((x, y), l, font=fl, fill=AMARELO)
        if credito:
            fc = f(FR, 22)
            lc = d.textlength(credito, font=fc)
            d.rectangle([W - 72 - lc, 52, W - 48, 86], fill=(0, 0, 0, 150))
            d.text((W - 60 - lc, 56), credito, font=fc, fill=BRANCO)
    else:
        # vertical: respeita as áreas cobertas pela interface (topo ~180 px, base ~420 px, lateral direita ~150 px)
        for i in range(700):
            a = int(200 * max(0, (i - 200)) / 500)
            d.line([(0, H - 700 + i), (W, H - 700 + i)], fill=(0, 8, 24, a))
        selo(d, 60, 190, 0.9)
        fm = f(FB, 56)
        linhas_m = quebrar(d, manchete.upper(), fm, W - 200)[:3]
        y0 = 330
        d.rectangle([60, y0 - 14, W - 60, y0 + 70 * len(linhas_m) + 6], fill=AZUL + (235,))
        d.rectangle([60, y0 - 14, 76, y0 + 70 * len(linhas_m) + 6], fill=VERMELHO)
        for i, l in enumerate(linhas_m):
            d.text((96, y0 + i * 70), l, font=fm, fill=BRANCO)
        if credito:
            fc, yc = f(FR, 24), y0 + 70 * len(linhas_m) + 20
            d.rectangle([60, yc - 4, 84 + d.textlength(credito[:70], font=fc), yc + 32], fill=(0, 0, 0, 150))
            d.text((72, yc), credito[:70], font=fc, fill=BRANCO)
        for tam in (62, 54, 46):
            fl = f(FB, tam)
            linhas_l = quebrar(d, legenda, fl, W - 260)
            if len(linhas_l) <= 4:
                break
        linhas_l = linhas_l[:5]
        alt_l = int(tam * 1.3)
        yl = 1180 - alt_l * len(linhas_l) // 2
        for i, l in enumerate(linhas_l):
            largura = d.textlength(l, font=fl)
            x, y = (W - 150 - largura) / 2 + 20, yl + i * alt_l
            d.rectangle([x - 16, y - 4, x + largura + 16, y + alt_l - 2], fill=(0, 0, 0, 190))
            d.text((x, y), l, font=fl, fill=AMARELO)
        fa = f(FB, 34)
        d.rectangle([60, 1440, 100 + d.textlength(assunto_txt, font=fa) + 30, 1494], fill=VERMELHO + (245,))
        d.text((90, 1446), assunto_txt, font=fa, fill=BRANCO)
    cam.save(destino)


def cartao_final(destino):
    """Último quadro do corte vertical: chamada para o vídeo completo."""
    W, H = LAYOUTS["v"]
    img = Image.new("RGB", (W, H), AZUL)
    d = ImageDraw.Draw(img)
    selo(d, (W - 420) // 2, 520, 1.2)
    for i, (t, tam, cor) in enumerate([("Vídeo completo", 74, BRANCO), ("no YouTube", 74, BRANCO),
                                       (CANAL, 44, AMARELO), ("Siga para mais", 44, CINZA)]):
        fo = f(FB, tam)
        d.text(((W - d.textlength(t, font=fo)) / 2, 820 + i * 110), t, font=fo, fill=cor)
    img.save(destino, quality=92)


def miniatura(fundo, texto, destino):
    img = preencher(Image.open(fundo).convert("RGB"), 1280, 720)
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


def montar(midia, png, audio, seg, destino, layout, ordem):
    """Fundo (vídeo, foto com movimento ou âncora) + camada de texto + narração -> trecho .mp4."""
    W, H = LAYOUTS[layout]
    if midia["tipo"] == "video":
        entrada = ["-ss", f"{midia.get('offset', 0):.2f}", "-stream_loop", "-1", "-i", str(midia["arq"])]
        fundo = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},eq=brightness=-0.06"
    elif midia["tipo"] == "foto":
        entrada = ["-loop", "1", "-framerate", str(FPS), "-i", str(midia["arq"])]
        x = f"(iw-ow)*t/{seg:.2f}" if ordem % 2 else f"(iw-ow)*(1-t/{seg:.2f})"  # pan lento, alternando o sentido
        fundo = (f"scale={int(W * 1.12)}:{int(H * 1.12)}:force_original_aspect_ratio=increase,"
                 f"crop={W}:{H}:x='{x}':y='(ih-oh)/3',setsar=1,fps={FPS},eq=brightness=-0.08")
    else:
        entrada = ["-loop", "1", "-framerate", str(FPS), "-i", str(midia["arq"])]
        fundo = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}"
    som = ["-i", str(audio)] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *entrada, "-loop", "1", "-framerate", str(FPS), "-i", str(png),
                    *som, "-filter_complex", f"[0:v]{fundo}[bg];[bg][1:v]overlay=0:0,format=yuv420p[v]",
                    "-map", "[v]", "-map", "2:a", "-af", "apad", "-t", f"{seg:.2f}", "-r", str(FPS),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-video_track_timescale", "12800",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(destino)], check=True)


def concatenar(partes, destino):
    lista = destino.with_suffix(".txt")
    lista.write_text("".join(f"file '{p.resolve()}'\n" for p in partes))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-c", "copy", "-movflags", "+faststart", str(destino)], check=True)
    lista.unlink()


# ---------- áudio ----------
async def _falar(texto, destino):
    import edge_tts
    for tentativa in range(4):
        try:
            await edge_tts.Communicate(texto, VOZ, rate=VELOCIDADE, pitch=TOM).save(str(destino))
            return
        except Exception:
            if tentativa == 3:
                raise
            await asyncio.sleep(3 * (tentativa + 1))


def falar(texto, destino, teste):
    if teste:  # tom com a duração aproximada da fala (≈15 caracteres/s)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        f"sine=frequency=330:duration={max(1.0, len(texto) / 15):.2f}", str(destino)], check=True)
    else:
        asyncio.run(_falar(texto, destino))


def duracao(arq):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(arq)], capture_output=True, text=True).stdout or 0)


def abertura(manchete):
    return ("Olá! Seja muito bem-vindo ao RADAR365. "
            "Obrigado, de coração, pela sua presença e pela sua atenção — é por você que a gente trabalha todos os dias "
            "para trazer a informação checada, com fonte, do jeito que ela é. "
            "Agradeço também a cada pessoa que se inscreve, comenta e compartilha: vocês fazem este jornal. "
            f"E a notícia de agora é esta: {manchete}.")


def hhmmss(s):
    s = int(s)
    return f"{s // 3600}:{s // 60 % 60:02}:{s % 60:02}" if s >= 3600 else f"{s // 60:02}:{s % 60:02}"


def capitulos(marcos, total):
    """Capítulos do YouTube: começa em 00:00, cada um com ≥ 10 s, no mínimo 3."""
    saida = []
    for t, nome in marcos:
        if saida and (t - saida[-1][0] < 10 or nome == saida[-1][1]):
            continue
        saida.append((t, nome))
    if saida and total - saida[-1][0] < 10:
        saida.pop()
    if len(saida) < 3:
        return ""
    saida[0] = (0, saida[0][1])
    return "\n".join(f"{hhmmss(t)} {nome.capitalize()}" for t, nome in saida) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("saida")
    ap.add_argument("--ancora", required=True)
    ap.add_argument("--teste", action="store_true", help="sem rede: voz e mídia sintéticas")
    a = ap.parse_args()
    md = Path(a.roteiro).read_text(encoding="utf-8")
    nome = Path(a.roteiro).stem
    out = Path(a.saida)
    tmp = out / f"{nome}_v3"
    (tmp / "midia").mkdir(parents=True, exist_ok=True)
    manchete = re.sub(r"^\s*1\.\s*", "", secao(md, "Títulos").splitlines()[0]).strip()
    ancora = {"tipo": "ancora", "arq": Path(a.ancora), "credito": "Apresentador virtual (imagem gerada por IA)"}
    midia = Midia(tmp / "midia", a.teste)

    vazio = {"buscas": [], "pessoas": [], "arquivos": []}
    itens = [("ABERTURA", s, vazio) for s in frases(abertura(manchete))]
    for bloco, fala, pistas in blocos(md):
        itens += [(bloco, s, pistas) for s in frases(fala)]

    partes, marcos, registro, t, anterior = [], [], [], 0.0, None
    for i, (bloco, frase, pistas) in enumerate(itens):
        mp3, png, mp4 = tmp / f"{i:03}.mp3", tmp / f"{i:03}.png", tmp / f"{i:03}.mp4"
        if not mp3.exists():
            falar(frase, mp3, a.teste)
        seg = duracao(mp3) + 0.25
        escolha = None if bloco == "ABERTURA" else midia.para(frase, pistas, anterior)
        if escolha is anterior and anterior:
            escolha = dict(anterior, offset=anterior.get("offset", 0) + anterior["ultimo_seg"], usado=anterior.get("usado", 0) + seg)
        elif escolha:
            escolha = dict(escolha, offset=0.0, usado=seg)
        m = escolha or dict(ancora)
        if m["tipo"] == "video" and m.get("dur"):
            m["offset"] = m.get("offset", 0) % max(1.0, m["dur"] - 1)
        m["ultimo_seg"] = seg
        anterior = m if escolha else None
        if not mp4.exists():
            camada("h", m["credito"], manchete, assunto(bloco), frase, png)
            montar(m, png, mp3, seg, mp4, "h", i)
        partes.append(mp4)
        registro.append((bloco, frase, m, mp3, seg))
        marcos.append((t, "Abertura" if bloco == "ABERTURA" else assunto(bloco).lower()))
        t += seg

    final = out / f"{nome}.mp4"
    concatenar(partes, final)
    (out / f"{nome}-capitulos.txt").write_text(capitulos(marcos, t), encoding="utf-8")

    # corte vertical: do gancho em diante, até ~58 s, com chamada final para o vídeo completo
    partes_v, tv = [], 0.0
    for j, (bloco, frase, m, mp3, seg) in enumerate(registro):
        if bloco == "ABERTURA":
            continue
        if tv + seg > VERTICAL_MAX - 3 and partes_v:
            break
        png, mp4 = tmp / f"v{j:03}.png", tmp / f"v{j:03}.mp4"
        camada("v", m["credito"] if m["tipo"] != "ancora" else "", manchete, assunto(bloco), frase, png)
        montar(m, png, mp3, seg, mp4, "v", j)
        partes_v.append(mp4)
        tv += seg
    fim_png, fim_mp4 = tmp / "v_fim.png", tmp / "v_fim.mp4"
    cartao_final(fim_png)
    vazio_png = tmp / "v_vazio.png"
    Image.new("RGBA", LAYOUTS["v"], (0, 0, 0, 0)).save(vazio_png)
    montar({"tipo": "ancora", "arq": fim_png}, vazio_png, None, 3.0, fim_mp4, "v", 0)
    concatenar(partes_v + [fim_mp4], out / f"{nome}-vertical.mp4")

    fundo_mini = next((r[2]["arq"] for r in registro if r[2]["tipo"] == "foto"), None)
    if not fundo_mini:  # sem foto: usa um quadro de vídeo ou o âncora
        clipe = next((r[2] for r in registro if r[2]["tipo"] == "video"), None)
        fundo_mini = tmp / "mini.jpg"
        if clipe:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", str(clipe["arq"]), "-frames:v", "1",
                            str(fundo_mini)], check=True)
        else:
            fundo_mini = Path(a.ancora)
    miniatura(fundo_mini, secao(md, "Texto da miniatura") or manchete, out / f"{nome}.jpg")
    tipos = [r[2]["tipo"] for r in registro]
    print(json.dumps({"video": str(final), "frases": len(itens), "segundos": round(duracao(final)),
                      "vertical_segundos": round(duracao(out / f"{nome}-vertical.mp4")),
                      "trechos_video": tipos.count("video"), "trechos_foto": tipos.count("foto"),
                      "trechos_ancora": tipos.count("ancora")}))


if __name__ == "__main__":
    main()
