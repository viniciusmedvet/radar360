"""Gera a identidade visual do canal: banner do YouTube (2560x1440) e foto de perfil (800x800).
Uso: python3 scripts/gerar-identidade.py  ->  assets/canal/banner-youtube.png, assets/canal/perfil.png"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AZUL, AZUL2, VERMELHO, BRANCO, CINZA = (6, 28, 64), (12, 60, 130), (214, 31, 38), (255, 255, 255), (205, 212, 224)
VERDE = (64, 214, 170)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SAIDA = Path(__file__).resolve().parent.parent / "assets" / "canal"


def f(c, t):
    return ImageFont.truetype(c, t)


def fundo(w, h):
    img = Image.new("RGB", (w, h), AZUL)
    d = ImageDraw.Draw(img)
    for y in range(h):  # degradê vertical azul-escuro -> azul
        k = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(AZUL[i] + (AZUL2[i] - AZUL[i]) * k * 0.55) for i in range(3)))
    return img


def radar(img, cx, cy, r, aneis=4, varredura=True):
    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    for i in range(1, aneis + 1):
        ri = r * i / aneis
        d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], outline=VERDE + (70 + 25 * i,), width=max(2, r // 120))
    d.line([(cx - r, cy), (cx + r, cy)], fill=VERDE + (60,), width=max(1, r // 200))
    d.line([(cx, cy - r), (cx, cy + r)], fill=VERDE + (60,), width=max(1, r // 200))
    if varredura:
        for a in range(0, 60):  # rastro do feixe
            ang = math.radians(-40 - a)
            d.line([(cx, cy), (cx + r * math.cos(ang), cy + r * math.sin(ang))], fill=VERDE + (int(120 * (1 - a / 60)),), width=max(2, r // 90))
    for px, py, cor in [(0.45, -0.30, VERMELHO), (-0.55, 0.20, BRANCO), (0.15, 0.62, VERDE)]:  # alvos
        x, y, s = cx + px * r, cy + py * r, max(6, r // 28)
        d.ellipse([x - s, y - s, x + s, y + s], fill=cor + (255,))
    brilho = camada.filter(ImageFilter.GaussianBlur(r // 60 or 1))
    img.paste(Image.alpha_composite(Image.alpha_composite(img.convert("RGBA"), brilho), camada).convert("RGB"))


def centro(d, y, texto, fonte, w, cor):
    d.text(((w - d.textlength(texto, font=fonte)) / 2, y), texto, font=fonte, fill=cor)


def banner():
    W, H = 2560, 1440
    img = fundo(W, H)
    radar(img, 2050, 720, 620)
    radar(img, 480, 760, 360, aneis=3, varredura=False)
    vidro = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x0, y0 = (W - 1546) // 2, (H - 423) // 2
    ImageDraw.Draw(vidro).rounded_rectangle([x0 - 40, y0 - 10, x0 + 1586, y0 + 433], radius=36, fill=AZUL + (215,))
    img.paste(Image.alpha_composite(img.convert("RGBA"), vidro).convert("RGB"))
    d = ImageDraw.Draw(img)
    # área segura do YouTube (aparece em todos os aparelhos): 1546x423 centralizada
    x0, y0 = (W - 1546) // 2, (H - 423) // 2
    centro(d, y0 + 18, "RADAR 360", f(FB, 150), W, BRANCO)
    d.rectangle([W // 2 - 300, y0 + 192, W // 2 + 300, y0 + 200], fill=VERMELHO)
    centro(d, y0 + 222, "CIÊNCIA · SAÚDE · GEOPOLÍTICA · DINHEIRO", f(FB, 50), W, BRANCO)
    centro(d, y0 + 300, "O mundo como ele é — com fonte.", f(FR, 46), W, CINZA)
    centro(d, y0 + 362, "Vídeos novos todos os dias", f(FB, 34), W, VERDE)
    img.save(SAIDA / "banner-youtube.png", optimize=True)


def perfil():
    S = 800
    img = fundo(S, S)
    radar(img, S // 2, S // 2, 360)
    d = ImageDraw.Draw(img)
    d.ellipse([S // 2 - 250, S // 2 - 190, S // 2 + 250, S // 2 + 190], fill=AZUL)
    centro(d, S // 2 - 128, "RADAR", f(FB, 96), S, BRANCO)
    d.rectangle([S // 2 - 150, S // 2 - 14, S // 2 + 150, S // 2 - 6], fill=VERMELHO)
    centro(d, S // 2 + 2, "360", f(FB, 130), S, VERDE)
    img.save(SAIDA / "perfil.png", optimize=True)


if __name__ == "__main__":
    SAIDA.mkdir(parents=True, exist_ok=True)
    banner()
    perfil()
    print("ok:", *sorted(p.name for p in SAIDA.glob("*.png")))
