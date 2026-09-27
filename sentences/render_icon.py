"""Render a distinct, maskable bitmap icon for sentence practice."""

from pathlib import Path

from PIL import Image, ImageDraw


def render(size):
    scale = 4
    canvas = Image.new("RGB", (size * scale, size * scale), "#0c5956")
    draw = ImageDraw.Draw(canvas)
    s = lambda value: round(value * size * scale / 512)
    draw.rounded_rectangle((s(90), s(115), s(422), s(358)), radius=s(45), fill="#ffffff")
    draw.polygon([(s(154), s(344)), (s(154), s(417)), (s(225), s(350))], fill="#ffffff")
    draw.rounded_rectangle((s(145), s(178), s(367), s(202)), radius=s(12), fill="#ec815f")
    draw.rounded_rectangle((s(145), s(229), s(328), s(253)), radius=s(12), fill="#4a9c87")
    draw.rounded_rectangle((s(145), s(280), s(274), s(304)), radius=s(12), fill="#4a9c87")
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "icons"
    target.mkdir(exist_ok=True)
    for dimension in (180, 192, 512):
        render(dimension).save(target / f"icon-{dimension}.png", optimize=True)
