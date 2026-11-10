#!/usr/bin/env python3
"""Generate H.U.M.A.N.S Plymouth splash frames from the supplied visual direction."""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH = 800
HEIGHT = 450
SCALE = 2
FRAME_COUNT = 54
INTRO_FRAMES = 10
TAU = math.tau
PALETTE = ((212, 175, 55), (255, 59, 48), (52, 120, 246), (212, 175, 55))


def smooth(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def mix(a: float, b: float, amount: float) -> float:
    return a + (b - a) * amount


def spectrum(seconds: float) -> tuple[int, int, int]:
    phase = (seconds % 9.0) / 3.0
    segment = min(2, int(phase))
    blend = smooth(phase - segment)
    start = PALETTE[segment]
    end = PALETTE[segment + 1]
    return tuple(round(mix(start[i], end[i], blend)) for i in range(3))


def figure_eight(angle: float, radius: float, cx: float, cy: float) -> tuple[float, float]:
    sine = math.sin(angle)
    cosine = math.cos(angle)
    divisor = 1 + sine * sine
    return (cx + radius * cosine / divisor, cy + radius * sine * cosine / divisor)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for name in names:
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default(size=size)


def draw_frame(frame_index: int) -> Image.Image:
    width, height = WIDTH * SCALE, HEIGHT * SCALE
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    orbit_glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sharp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(orbit_glow)
    draw = ImageDraw.Draw(sharp)

    if frame_index < INTRO_FRAMES:
        intro = smooth(frame_index / (INTRO_FRAMES - 1))
        radius = mix(205, 116, intro) * SCALE
        cy = mix(HEIGHT * 0.50, HEIGHT * 0.385, intro) * SCALE
        title_alpha = round(255 * smooth((frame_index - 1) / 7))
        color = PALETTE[0]
        orbit_time = frame_index * 0.13
    else:
        loop_length = FRAME_COUNT - INTRO_FRAMES
        phase = (frame_index - INTRO_FRAMES) / (loop_length - 1)
        radius = 116 * SCALE
        cy = HEIGHT * 0.385 * SCALE
        title_alpha = 255
        color = spectrum(phase * 9.0)
        orbit_time = phase * TAU

    cx = width / 2
    orbit_points = [figure_eight(i * TAU / 360, radius, cx, cy) for i in range(361)]
    orbit_points = [(round(x), round(y)) for x, y in orbit_points]
    glow_color = (*color, 100)
    sharp_color = (*color, 155)
    glow_draw.line(orbit_points, fill=glow_color, width=4 * SCALE, joint="curve")
    draw.line(orbit_points, fill=sharp_color, width=1 * SCALE, joint="curve")

    # Four small orbiting comets keep the mark moving while the background stays true black.
    for comet in range(4):
        head_angle = orbit_time * 1.15 + comet * TAU / 4
        previous = figure_eight(head_angle, radius, cx, cy)
        for tail_step in range(1, 22):
            angle = head_angle - tail_step * 0.055
            point = figure_eight(angle, radius, cx, cy)
            fade = (1 - tail_step / 22) ** 2
            alpha = round(220 * fade)
            bright = tuple(round(component + (255 - component) * 0.68) for component in color)
            glow_draw.line(
                [tuple(map(round, previous)), tuple(map(round, point))],
                fill=(*bright, alpha),
                width=max(2, round((1.2 + 3.4 * fade) * SCALE)),
            )
            draw.line(
                [tuple(map(round, previous)), tuple(map(round, point))],
                fill=(*color, round(alpha * 0.78)),
                width=max(1, round((0.8 + 1.7 * fade) * SCALE)),
            )
            previous = point
        hx, hy = figure_eight(head_angle, radius, cx, cy)
        bright = tuple(round(component + (255 - component) * 0.8) for component in color)
        glow_draw.ellipse((hx - 12, hy - 12, hx + 12, hy + 12), fill=(*bright, 230))
        draw.ellipse((hx - 4, hy - 4, hx + 4, hy + 4), fill=(*bright, 255))

    # A soft bloom preserves the source's luminous orbit without making the black gray.
    bloom = orbit_glow.filter(ImageFilter.GaussianBlur(10 * SCALE))
    canvas.alpha_composite(bloom)
    canvas.alpha_composite(orbit_glow)
    canvas.alpha_composite(sharp)

    text_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    font = load_font(54 * SCALE, bold=True)
    label = "H.U.M.A.N.S"
    bounds = text_draw.textbbox((0, 0), label, font=font, stroke_width=0)
    text_x = (width - (bounds[2] - bounds[0])) / 2 - bounds[0]
    text_y = 287 * SCALE - bounds[1]
    bright = tuple(round(component + (255 - component) * 0.2) for component in color)
    text_draw.text((text_x, text_y), label, font=font, fill=(*bright, title_alpha))
    text_glow = text_layer.filter(ImageFilter.GaussianBlur(13 * SCALE))
    if title_alpha < 255:
        text_glow.putalpha(text_glow.getchannel("A"))
    canvas.alpha_composite(text_glow)
    canvas.alpha_composite(text_layer)

    return canvas.convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def write_progress_images(output: Path) -> None:
    track = Image.new("RGBA", (360, 6), (0, 0, 0, 0))
    track_draw = ImageDraw.Draw(track)
    track_draw.rounded_rectangle((0, 1, 359, 4), radius=2, fill=(212, 175, 55, 58))
    track.save(output / "progress-track.png", optimize=True)

    fill = Image.new("RGBA", (360, 6), (0, 0, 0, 0))
    fill_pixels = fill.load()
    for x in range(fill.width):
        blend = x / max(1, fill.width - 1)
        rgb = tuple(round(mix(a, b, blend)) for a, b in zip((212, 175, 55), (242, 214, 117)))
        for y in range(1, 5):
            fill_pixels[x, y] = (*rgb, 255)
    fill.save(output / "progress-fill.png", optimize=True)



def write_plymouth_script(output: Path) -> None:
    lines = [
        "# H.U.M.A.N.S animated AMOLED boot splash.",
        "Window.SetBackgroundTopColor (0, 0, 0);",
        "Window.SetBackgroundBottomColor (0, 0, 0);",
        "",
        "frames = [];",
    ]
    for index in range(FRAME_COUNT):
        lines.append(f'frames[{index}] = Image("frames/frame-{index:03d}.png");')
    lines.extend([
        "",
        "animation.sprite = Sprite(frames[0]);",
        "animation.x = Window.GetX() + Window.GetWidth() / 2 - frames[0].GetWidth() / 2;",
        "animation.y = Window.GetY() + Window.GetHeight() / 2 - frames[0].GetHeight() / 2;",
        "animation.sprite.SetPosition(animation.x, animation.y, 100);",
        "animation.frame = 0;",
        "animation.ticks = 0;",
        "",
        "fun refresh_callback ()",
        "{",
        "  animation.ticks += 1;",
        "  if (animation.ticks >= 3)",
        "    {",
        "      animation.ticks = 0;",
        "      animation.frame += 1;",
        f"      if (animation.frame >= {FRAME_COUNT})",
        f"        animation.frame = {INTRO_FRAMES};",
        "      animation.sprite.SetImage(frames[animation.frame]);",
        "    }",
        "}",
        "",
        "Plymouth.SetRefreshFunction(refresh_callback);",
        "",
        'track.image = Image("progress-track.png");',
        "track.sprite = Sprite(track.image);",
        "track.x = Window.GetX() + Window.GetWidth() / 2 - track.image.GetWidth() / 2;",
        "track.y = Window.GetY() + Window.GetHeight() * 0.79;",
        "track.sprite.SetPosition(track.x, track.y, 110);",
        'progress.template = Image("progress-fill.png");',
        "progress.sprite = Sprite();",
        "progress.sprite.SetPosition(track.x, track.y, 111);",
        "",
        "fun progress_callback (duration, fraction)",
        "{",
        "  if (fraction < 0)",
        "    fraction = 0;",
        "  if (fraction > 1)",
        "    fraction = 1;",
        "  width = Math.Int(progress.template.GetWidth() * fraction);",
        "  if (width < 1)",
        "    progress.sprite.SetOpacity(0);",
        "  else",
        "    {",
        "      progress.image = progress.template.Scale(width, progress.template.GetHeight());",
        "      progress.sprite.SetImage(progress.image);",
        "      progress.sprite.SetOpacity(1);",
        "    }",
        "}",
        "",
        "Plymouth.SetBootProgressFunction(progress_callback);",
        "",
    ])
    (output / "corpse-os.script").write_text("\n".join(lines), encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "config/includes.chroot/usr/share/plymouth/themes/corpse-os",
        help="directory where the Plymouth theme assets are written",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    frames_dir = output / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for index in range(FRAME_COUNT):
        image = draw_frame(index)
        image.save(frames_dir / f"frame-{index:03d}.png", optimize=True)
    write_progress_images(output)
    write_plymouth_script(output)
    print(f"Generated {FRAME_COUNT} animation frames, progress assets, and Plymouth script in {output}")


if __name__ == "__main__":
    main()
