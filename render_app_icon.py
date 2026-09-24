"""Render the flashcard icon at PWA, iPhone, and favicon sizes."""

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
SCALE = 4
CANVAS = 512 * SCALE


def point(xy):
    return tuple(round(value * SCALE) for value in xy)


def polygon(draw, points, fill):
    draw.polygon([point(xy) for xy in points], fill=fill)


def quadratic(start, control, end):
    return [
        point((
            (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t ** 2 * end[0],
            (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t ** 2 * end[1],
        ))
        for t in (index / 40 for index in range(41))
    ]


def wave(draw, start, control, end):
    color = "#288f88"
    width = 11 * SCALE
    points = quadratic(start, control, end)
    draw.line(points, fill=color, width=width, joint="curve")
    radius = width // 2
    for x, y in (points[0], points[-1]):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def render():
    image = Image.new("RGB", (CANVAS, CANVAS), "#172329")

    back = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    back_draw = ImageDraw.Draw(back)
    back_draw.rounded_rectangle((*point((151, 97)), *point((419, 412))), radius=24 * SCALE, fill="#61c5ae")
    back = back.rotate(-8, resample=Image.Resampling.BICUBIC, center=point((283, 252)))
    image.paste(back, (0, 0), back)

    front = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    front_draw = ImageDraw.Draw(front)
    front_draw.rounded_rectangle((*point((100, 143)), *point((386, 445))), radius=24 * SCALE, fill="#f7faf6")
    polygon(front_draw, [(133, 143), (172, 143), (172, 197), (152.5, 186), (133, 197)], "#f07f72")
    polygon(front_draw, [
        (148, 355), (194, 214), (201, 199), (219, 199), (226, 214),
        (273, 355), (245, 355), (233, 318), (187, 318), (175, 355),
    ], "#17343a")
    polygon(front_draw, [(196, 293), (225, 293), (210, 246)], "#f7faf6")
    wave(front_draw, (282, 259), (301, 280), (282, 302))
    wave(front_draw, (304, 242), (337, 281), (304, 319))
    front = front.rotate(6, resample=Image.Resampling.BICUBIC, center=point((243, 293)))
    image.paste(front, (0, 0), front)

    base = image.resize((512, 512), Image.Resampling.LANCZOS)
    base.save(ROOT / "icon-512-v2.png", optimize=True)
    base.resize((192, 192), Image.Resampling.LANCZOS).save(ROOT / "icon-192-v2.png", optimize=True)
    base.resize((180, 180), Image.Resampling.LANCZOS).save(ROOT / "apple-touch-icon-v2.png", optimize=True)
    base.save(ROOT / "favicon-v2.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])


if __name__ == "__main__":
    render()
