import requests
import os
from collections import Counter

# ── Config ──────────────────────────────────────────────────────
print("=" * 50)
print("   🎨 Figma Color & Font Extractor")
print("=" * 50)
FIGMA_TOKEN  = input("\n🔑 Enter your Figma Personal Access Token: ").strip()
FILE_KEY     = input("📁 Enter your Figma File Key: ").strip()
TOP_COLORS   = 300  # Keep top 300 most used colors
print("\n✅ Keys received! Starting extraction...\n")
print("=" * 50)

HEADERS     = {"X-FIGMA-TOKEN": FIGMA_TOKEN}
COLORS_DIR  = "assets_helper"
COLORS_FILE = os.path.join(COLORS_DIR, "app_colors.dart")
FONTS_FILE  = os.path.join(COLORS_DIR, "app_fonts.dart")


# ── 1. Fetch the full Figma file ─────────────────────────────────
def get_file():
    print("\n📡 Fetching Figma file...")
    url = f"https://api.figma.com/v1/files/{FILE_KEY}"
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
    except requests.HTTPError:
        if r.status_code == 403:
            print("❌ Invalid token — check your Figma Personal Access Token")
        elif r.status_code == 404:
            print("❌ File not found — check your FILE_KEY")
        else:
            print(f"❌ HTTP error {r.status_code}")
        exit(1)
    return r.json()


# ── 2. Opacity → alpha byte ───────────────────────────────────────
#
# Figma gives two separate opacity values:
#   fill["opacity"]      → layer-level opacity (0.0–1.0), default 1.0
#   fill["color"]["a"]   → per-channel alpha   (0.0–1.0), default 1.0
#
# Final alpha = layer opacity × color alpha, clamped to 0–255.
# Written as Color(0xAARRGGBB) so Flutter respects transparency.
#
# Example:
#   fill opacity = 0.5, color alpha = 1.0  → alpha = 128 → 0x80RRGGBB
#   fill opacity = 1.0, color alpha = 0.5  → alpha = 128 → 0x80RRGGBB
#   fill opacity = 1.0, color alpha = 1.0  → alpha = 255 → 0xFFRRGGBB  (fully opaque)

def rgba_to_dart_color(r, g, b, fill_opacity=1.0, color_alpha=1.0):
    """
    Returns (dart_hex, is_opaque) where dart_hex is the 8-char AARRGGBB string.
    is_opaque is True when alpha == 0xFF — used to pick the Color() prefix.
    """
    alpha     = fill_opacity * color_alpha          # combine both opacities
    alpha_int = max(0, min(255, int(round(alpha * 255))))
    r_int     = int(round(r * 255))
    g_int     = int(round(g * 255))
    b_int     = int(round(b * 255))

    aa_hex   = f"{alpha_int:02X}"
    rgb_hex  = f"{r_int:02X}{g_int:02X}{b_int:02X}"
    dart_hex = aa_hex + rgb_hex          # "FFRRGGBB" or "80RRGGBB"

    return dart_hex, alpha_int == 0xFF


# ── 3. Extract colors with frequency count ────────────────────────
def extract_colors_with_count(node, color_counter=None):
    if color_counter is None:
        color_counter = Counter()

    for fill in node.get("fills", []):
        if fill.get("type") == "SOLID" and "color" in fill:
            c            = fill["color"]
            fill_opacity = fill.get("opacity", 1.0)   # layer-level opacity
            color_alpha  = c.get("a", 1.0)            # per-channel alpha
            dart_hex, _  = rgba_to_dart_color(
                c["r"], c["g"], c["b"],
                fill_opacity=fill_opacity,
                color_alpha=color_alpha,
            )
            color_counter[dart_hex] += 1

    for stroke in node.get("strokes", []):
        if stroke.get("type") == "SOLID" and "color" in stroke:
            c            = stroke["color"]
            fill_opacity = stroke.get("opacity", 1.0)
            color_alpha  = c.get("a", 1.0)
            dart_hex, _  = rgba_to_dart_color(
                c["r"], c["g"], c["b"],
                fill_opacity=fill_opacity,
                color_alpha=color_alpha,
            )
            color_counter[dart_hex] += 1

    for child in node.get("children", []):
        extract_colors_with_count(child, color_counter)

    return color_counter


# ── 4. Extract text styles ────────────────────────────────────────
FONT_WEIGHT_MAP = {
    100: "FontWeight.w100",
    200: "FontWeight.w200",
    300: "FontWeight.w300",
    400: "FontWeight.w400",
    500: "FontWeight.w500",
    600: "FontWeight.w600",
    700: "FontWeight.w700",
    800: "FontWeight.w800",
    900: "FontWeight.w900",
}


def font_family_to_google_fonts_method(family):
    parts = family.strip().split()
    if len(parts) == 1:
        return parts[0][0].lower() + parts[0][1:]
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def extract_text_styles(node, style_map=None):
    if style_map is None:
        style_map = {}

    if node.get("type") == "TEXT":
        style       = node.get("style", {})
        fills       = node.get("fills", [])
        font_size   = style.get("fontSize")
        font_weight = style.get("fontWeight")
        font_family = style.get("fontFamily", "Inter")

        dart_hex = None
        for fill in fills:
            if fill.get("type") == "SOLID" and "color" in fill:
                c            = fill["color"]
                fill_opacity = fill.get("opacity", 1.0)
                color_alpha  = c.get("a", 1.0)
                dart_hex, _  = rgba_to_dart_color(
                    c["r"], c["g"], c["b"],
                    fill_opacity=fill_opacity,
                    color_alpha=color_alpha,
                )
                break

        if font_size and font_weight:
            key = (int(font_size), int(font_weight), font_family)
            if key not in style_map:
                style_map[key] = Counter()
            if dart_hex:
                style_map[key][dart_hex] += 1

    for child in node.get("children", []):
        extract_text_styles(child, style_map)

    return style_map


# ── 5. Write app_colors.dart ──────────────────────────────────────
def write_dart_colors(color_counter):
    os.makedirs(COLORS_DIR, exist_ok=True)

    top_colors = [hex for hex, _ in color_counter.most_common(TOP_COLORS)]

    lines = []
    lines.append("import 'package:flutter/material.dart';")
    lines.append("")
    lines.append("class AppColors {")
    lines.append("  AppColors._();")
    lines.append("")

    for dart_hex in sorted(top_colors):
        count      = color_counter[dart_hex]
        is_opaque  = dart_hex[:2].upper() == "FF"
        # Fully opaque → Color(0xFFRRGGBB)
        # Transparent  → Color(0xAARRGGBB) with comment showing opacity %
        if is_opaque:
            color_expr = f"Color(0x{dart_hex})"
            comment    = f"// used {count}x"
        else:
            alpha_pct  = round(int(dart_hex[:2], 16) / 255 * 100)
            color_expr = f"Color(0x{dart_hex})"
            comment    = f"// used {count}x  opacity {alpha_pct}%"

        lines.append(f"  static const Color c{dart_hex} = {color_expr}; {comment}")

    lines.append("}")
    lines.append("")

    with open(COLORS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n🎨 Top {len(top_colors)} colors written to {COLORS_FILE}")
    print("\n--- Preview (top 5 most used) ---")
    for dart_hex, count in color_counter.most_common(5):
        is_opaque = dart_hex[:2].upper() == "FF"
        suffix    = "" if is_opaque else f"  (opacity {round(int(dart_hex[:2], 16) / 255 * 100)}%)"
        print(f"  c{dart_hex} → used {count}x{suffix}")

    return set(top_colors)


# ── 6. Write app_fonts.dart ───────────────────────────────────────
def write_dart_fonts(style_map, valid_colors):
    os.makedirs(COLORS_DIR, exist_ok=True)

    lines = []
    lines.append("import 'package:flutter_screenutil/flutter_screenutil.dart';")
    lines.append("import 'package:google_fonts/google_fonts.dart';")
    lines.append("import 'package:flutter/material.dart';")
    lines.append("import 'app_colors.dart';")
    lines.append("")
    lines.append("class TextFontStyle {")
    lines.append("  TextFontStyle._();")
    lines.append("")

    count = 0
    for (font_size, font_weight, font_family) in sorted(
        style_map.keys(), key=lambda x: (x[2], x[0], x[1])
    ):
        color_counter = style_map[(font_size, font_weight, font_family)]

        most_common_color = None
        for color_hex, _ in color_counter.most_common():
            if color_hex in valid_colors:
                most_common_color = color_hex
                break

        if not most_common_color and color_counter:
            most_common_color = color_counter.most_common(1)[0][0]

        gf_method  = font_family_to_google_fonts_method(font_family)
        fw_dart    = FONT_WEIGHT_MAP.get(font_weight, f"FontWeight.w{font_weight}")
        var_name   = f"textStyle{font_size}w{font_weight}{font_family.replace(' ', '')}"
        color_ref  = f"AppColors.c{most_common_color}" if most_common_color else "AppColors.cFF000000"

        lines.append(f"  static var {var_name} = GoogleFonts.{gf_method}(")
        lines.append(f"    color: {color_ref},")
        lines.append(f"    fontSize: {font_size}.sp,")
        lines.append(f"    fontWeight: {fw_dart},")
        lines.append(f"  );")
        lines.append("")
        count += 1

    lines.append("}")
    lines.append("")

    with open(FONTS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n✏️  {count} text styles written to {FONTS_FILE}")
    print("\n--- Preview (first 3) ---")
    preview = [l for l in lines if "static var" in l][:3]
    for p in preview:
        print(f"  {p.strip()}")
    if count > 3:
        print(f"  ... and {count - 3} more")


# ── Main ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    file_data = get_file()
    document  = file_data["document"]

    print("\n🔎 Extracting colors...")
    color_counter = extract_colors_with_count(document)
    print(f"🎨 Total unique colors found: {len(color_counter)}")
    print(f"   Keeping top {TOP_COLORS} most used...")
    valid_colors = write_dart_colors(color_counter)

    print("\n🔎 Extracting text styles...")
    style_map = extract_text_styles(document)
    print(f"✏️  Unique text styles found: {len(style_map)} (grouped by size+weight+family)")
    write_dart_fonts(style_map, valid_colors)

    print("\n✅ Done!")
    print(f"   Colors → {COLORS_FILE}")
    print(f"   Fonts  → {FONTS_FILE}")
