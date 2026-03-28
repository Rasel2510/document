import os

assets_path = "assets"
output_dir  = "lib/assets_helper"
os.makedirs(output_dir, exist_ok=True)

images  = []
icons   = []
lotties = []

for root, dirs, files in os.walk(assets_path):
    for file in files:
        full_path = os.path.join(root, file).replace("\\", "/")
        var_name  = os.path.splitext(file)[0]\
                      .replace("-", "_")\
                      .replace(" ", "_")\
                      .replace(".", "_")

        if file.endswith(('.png', '.jpg', '.jpeg', '.webp')):
            images.append((var_name, full_path))
        elif file.endswith('.svg'):
            icons.append((var_name, full_path))
        elif file.endswith('.json'):
            lotties.append((var_name, full_path))

# ── AppIcons ──────────────────────────────────────────────
def write_icons(items):
    if not items:
        return

    # find base route from first item
    # "assets/icons/home_icon.svg" → "assets/icons"
    base = os.path.dirname(items[0][1]) if items else "assets/icons"

    lines = [
        "// AUTO GENERATED — do not edit manually",
        "// Run: python generate_assets.py\n",
        "class AppIcons {",
        "  AppIcons._();\n",
        f"  static const String _iconsRoute = '{base}';\n",
    ]
    for var, path in items:
        filename = os.path.basename(path)  # "home_icon.svg"
        lines.append(
            f"  static const String {var} = '${{_iconsRoute}}/{filename}';",
        )
    lines.append("}\n")

    # fix the dart string interpolation
    content = "\n".join(lines).replace(
        "${_iconsRoute}",
        r"$_iconsRoute"
    )

    with open(f"{output_dir}/app_icons.dart", "w") as f:
        f.write(content)
    print(f"✅ Generated app_icons.dart ({len(items)} icons)")

# ── AppImages ─────────────────────────────────────────────
def write_images(items):
    if not items:
        return

    base = os.path.dirname(items[0][1]) if items else "assets/images"

    lines = [
        "// AUTO GENERATED — do not edit manually",
        "// Run: python generate_assets.py\n",
        "class AppImages {",
        "  AppImages._();\n",
        f"  static const String _imagesRoute = '{base}';\n",
    ]
    for var, path in items:
        filename = os.path.basename(path)
        lines.append(
            f"  static const String {var} = '${{_imagesRoute}}/{filename}';",
        )
    lines.append("}\n")

    content = "\n".join(lines).replace(
        "${_imagesRoute}",
        r"$_imagesRoute"
    )

    with open(f"{output_dir}/app_images.dart", "w") as f:
        f.write(content)
    print(f"✅ Generated app_images.dart ({len(items)} images)")

# ── AppLotties ────────────────────────────────────────────
def write_lotties(items):
    if not items:
        return

    base = os.path.dirname(items[0][1]) if items else "assets/lotties"

    lines = [
        "// AUTO GENERATED — do not edit manually",
        "// Run: python generate_assets.py\n",
        "class AppLotties {",
        "  AppLotties._();\n",
        f"  static const String _lottiesRoute = '{base}';\n",
    ]
    for var, path in items:
        filename = os.path.basename(path)
        lines.append(
            f"  static const String {var} = '${{_lottiesRoute}}/{filename}';",
        )
    lines.append("}\n")

    content = "\n".join(lines).replace(
        "${_lottiesRoute}",
        r"$_lottiesRoute"
    )

    with open(f"{output_dir}/app_lotties.dart", "w") as f:
        f.write(content)
    print(f"✅ Generated app_lotties.dart ({len(items)} lotties)")

# ── Run ───────────────────────────────────────────────────
write_icons(icons)
write_images(images)
write_lotties(lotties)

print("\nDone! Files saved to lib/assets_helper/")