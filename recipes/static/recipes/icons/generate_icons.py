"""Generate app icons from SVG using Pillow."""

from PIL import Image, ImageDraw, ImageFont
import math
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def create_icon(size):
    """Create a meal planner app icon at the given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background: rounded rectangle with gradient-like effect
    # Base: dark teal matching the app's primary color
    bg_color = (26, 26, 46)  # --bg: #1a1a2e
    primary = (124, 185, 168)  # --primary: #7cb9a8
    accent = (255, 213, 154)  # --accent: #ffd59a

    # Draw rounded rectangle background
    radius = size // 5
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=radius, fill=bg_color)

    # Draw a subtle gradient overlay (top-left corner glow)
    for i in range(size // 3):
        alpha = int(12 * (1 - i / (size // 3)))
        if alpha <= 0:
            continue
        x0 = i
        y0 = i
        x1 = size // 2 - i
        y1 = size // 2 - i
        if x1 <= x0 or y1 <= y0:
            continue
        overlay_color = (primary[0], primary[1], primary[2], alpha)
        draw.ellipse([(x0, y0), (x1, y1)], fill=overlay_color)

    # Draw a stylized plate/bowl shape
    center_x = size // 2
    center_y = size // 2 + size // 20

    # Plate circle (teal outline)
    plate_r = int(size * 0.30)
    plate_width = max(size // 30, 2)
    draw.ellipse(
        [
            (center_x - plate_r, center_y - plate_r),
            (center_x + plate_r, center_y + plate_r),
        ],
        outline=primary,
        width=plate_width,
    )

    # Inner plate circle (subtle)
    inner_r = int(size * 0.22)
    inner_color = (primary[0], primary[1], primary[2], 40)
    draw.ellipse(
        [
            (center_x - inner_r, center_y - inner_r),
            (center_x + inner_r, center_y + inner_r),
        ],
        outline=(primary[0], primary[1], primary[2], 80),
        width=max(plate_width // 2, 1),
    )

    # Fork (left side) - simplified as lines
    fork_x = center_x - int(size * 0.12)
    fork_top = center_y - int(size * 0.28)
    fork_bottom = center_y + int(size * 0.05)
    prong_len = int(size * 0.12)
    prong_gap = int(size * 0.04)
    line_w = max(size // 40, 2)

    # Fork handle
    draw.line(
        [(fork_x, fork_bottom), (fork_x, fork_top + prong_len)],
        fill=accent,
        width=line_w,
    )
    # Fork prongs (3)
    for offset in [-prong_gap, 0, prong_gap]:
        draw.line(
            [(fork_x + offset, fork_top + prong_len), (fork_x + offset, fork_top)],
            fill=accent,
            width=max(line_w - 1, 1),
        )
    # Fork prong connector
    draw.line(
        [
            (fork_x - prong_gap, fork_top + prong_len),
            (fork_x + prong_gap, fork_top + prong_len),
        ],
        fill=accent,
        width=max(line_w - 1, 1),
    )

    # Knife (right side)
    knife_x = center_x + int(size * 0.12)
    knife_top = center_y - int(size * 0.28)
    knife_bottom = center_y + int(size * 0.05)

    # Knife blade
    draw.line(
        [(knife_x, knife_bottom), (knife_x, knife_top)],
        fill=accent,
        width=line_w,
    )
    # Knife edge (thicker on one side)
    draw.line(
        [(knife_x + line_w, knife_top), (knife_x + line_w, knife_top + int(size * 0.18))],
        fill=accent,
        width=max(line_w // 2, 1),
    )

    # Calendar dots at top (representing weekly planning)
    dot_y = center_y - int(size * 0.35)
    dot_r = max(size // 35, 2)
    dot_spacing = int(size * 0.06)
    start_x = center_x - 3 * dot_spacing
    for i in range(7):
        dx = start_x + i * dot_spacing
        color = accent if i == 3 else (primary[0], primary[1], primary[2], 120)
        draw.ellipse(
            [(dx - dot_r, dot_y - dot_r), (dx + dot_r, dot_y + dot_r)],
            fill=color,
        )

    return img


def main():
    sizes = {
        "icon-16.png": 16,
        "icon-32.png": 32,
        "icon-180.png": 180,  # Apple touch icon
        "icon-192.png": 192,  # PWA standard
        "icon-512.png": 512,  # PWA large
        "favicon.ico": 32,
    }

    for filename, size in sizes.items():
        icon = create_icon(size)
        filepath = os.path.join(OUTPUT_DIR, filename)
        if filename.endswith(".ico"):
            icon.save(filepath, format="ICO")
        else:
            icon.save(filepath, format="PNG")
        print(f"  Created {filename} ({size}x{size})")

    print("Done!")


if __name__ == "__main__":
    main()
