"""Renderiza um roteiro (video-N.md) em MP4 1920x1080 + miniatura 1280x720, sem custo:
narração com Piper TTS (voz pt_BR-faber-medium) e telas geradas com Pillow + ffmpeg.

Uso: python renderizar-video.py video-1.md saida_dir --voz pt_BR-faber-medium.onnx
"""
import argparse, json, re, subprocess, textwrap, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FUNDO, DESTAQUE, TEXTO, SUAVE = (12, 18, 32), (230, 57, 70), (245, 245, 245), (160, 170, 190)
FONTE_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONTE_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
MARCA = "VINÍCIUS ROCHA · NOTÍCIAS SEM FILTRO"


def secao(md, titulo):
    m = re.search(rf"^## {re.escape(titulo)}\s*\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def segmentos(md):
    """Divide o roteiro em parágrafos narráveis, cada um com o bloco e a deixa visual vigente."""
    bloco, deixa, saida = "", "", []
    for par in re.split(r"\n\s*\n", secao(md, "Roteiro narrado")):
        par = par.strip()
        if not par:
            continue
        cab = re.match(r"\*\*(.+?)\*\*\s*(?:\n|$)", par)
        if cab:
            bloco = re.sub(r"\s*\(.*?\)\s*$", "", cab.group(1))
            par = par[cab.end():].strip()
            if not par:
                continue
        cues = re.findall(r"\[(?:B-ROLL|GRÁFICO|TELA):\s*([^\]]+)\]", par)
        if cues:
            deixa = cues[-1]
        fala = re.sub(r"\[[^\]]*\]", "", par)
        fala = re.sub(r"\*\*(.+?)\*\*", r"\1", fala)
        fala = fala.replace("(pausa)", "…").strip()
        if len(fala) > 3:
            saida.append({"bloco": bloco, "deixa": deixa, "fala": fala})
    return saida


def fonte(caminho, tam):
    return ImageFont.truetype(caminho, tam)


def quebrar(draw, texto, f, largura):
    linhas, atual = [], ""
    for p in texto.split():
        teste = f"{atual} {p}".strip()
        if draw.textlength(teste, font=f) <= largura:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def frase_chave(fala, limite=150):
    frase = re.split(r"(?<=[.!?…])\s", fala)[0]
    return frase if len(frase) <= limite else textwrap.shorten(fala, limite, placeholder="…")


def tela(seg, titulo, caminho):
    img = Image.new("RGB", (W, H), FUNDO)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=DESTAQUE)
    d.text((80, 60), MARCA, font=fonte(FONTE_B, 30), fill=DESTAQUE)
    d.text((80, 110), textwrap.shorten(titulo, 80, placeholder="…"), font=fonte(FONTE_R, 30), fill=SUAVE)
    if seg["bloco"]:
        f = fonte(FONTE_B, 34)
        rot = seg["bloco"].upper()
        d.rounded_rectangle([80, 220, 80 + d.textlength(rot, font=f) + 48, 290], 12, fill=DESTAQUE)
        d.text((104, 232), rot, font=f, fill=TEXTO)
    f = fonte(FONTE_B, 66)
    y = 360
    for linha in quebrar(d, frase_chave(seg["fala"]), f, W - 160)[:5]:
        d.text((80, y), linha, font=f, fill=TEXTO)
        y += 84
    if seg["deixa"]:
        d.text((80, H - 130), textwrap.shorten(seg["deixa"], 110, placeholder="…"), font=fonte(FONTE_R, 30), fill=SUAVE)
    d.text((80, H - 80), "Fontes na descrição · Conteúdo verificado", font=fonte(FONTE_R, 26), fill=SUAVE)
    img.save(caminho)


def miniatura(texto, caminho):
    img = Image.new("RGB", (1280, 720), FUNDO)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1280, 20], fill=DESTAQUE)
    f = fonte(FONTE_B, 120)
    linhas = quebrar(d, texto.strip('"“”').upper(), f, 1160)
    y = (720 - len(linhas) * 140) // 2
    for linha in linhas:
        d.text((60, y), linha, font=f, fill=TEXTO, stroke_width=4, stroke_fill=DESTAQUE)
        y += 140
    d.text((60, 640), MARCA, font=fonte(FONTE_B, 30), fill=DESTAQUE)
    img.save(caminho, quality=90)


def duracao(wav):
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("saida")
    ap.add_argument("--voz", required=True)
    a = ap.parse_args()
    md = Path(a.roteiro).read_text(encoding="utf-8")
    nome = Path(a.roteiro).stem
    out = Path(a.saida)
    tmp = out / f"{nome}_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    titulo = re.sub(r"^\s*1\.\s*", "", secao(md, "Títulos (3 opções, até 70 caracteres)").splitlines()[0])
    partes = []
    for i, seg in enumerate(segmentos(md)):
        wav, png, mp4 = tmp / f"{i:03}.wav", tmp / f"{i:03}.png", tmp / f"{i:03}.mp4"
        subprocess.run(["python3", "-m", "piper", "-m", a.voz, "-f", str(wav), "--sentence-silence", "0.35"],
                       input=seg["fala"].encode(), check=True, capture_output=True)
        tela(seg, titulo, png)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "2", "-i", str(png),
                        "-i", str(wav), "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                        "-r", "24", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                        "-t", f"{duracao(wav) + 0.6:.2f}", "-af", "apad", str(mp4)], check=True)
        partes.append(mp4)
    lista = tmp / "lista.txt"
    lista.write_text("".join(f"file '{p.name}'\n" for p in partes))
    final = out / f"{nome}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-c", "copy", "-movflags", "+faststart", str(final)], check=True)
    miniatura(secao(md, "Texto da miniatura (até 4 palavras)") or titulo, out / f"{nome}.jpg")
    seg_total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                      str(final)], capture_output=True, text=True).stdout)
    print(json.dumps({"video": str(final), "miniatura": str(out / f"{nome}.jpg"), "segundos": round(seg_total),
                      "partes": len(partes)}))


if __name__ == "__main__":
    main()
