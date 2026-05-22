import os
import re

assets_path = "assets"
output_dir  = "lib/assets_helper"
pubspec     = "pubspec.yaml"
os.makedirs(output_dir, exist_ok=True)

# ── Guard — assets folder must exist ─────────────────────────────
if not os.path.exists(assets_path):
    print(f"⚠️  '{assets_path}' folder not found. Nothing to generate.")
    exit(0)

images  = []
icons   = []
lotties = []

# ── Duplicate var name tracker ────────────────────────────────────
def make_var_name(file_path, seen_names):
    stem        = os.path.splitext(os.path.basename(file_path))[0]
    parent      = os.path.basename(os.path.dirname(file_path))
    var_name    = stem.replace("-", "_").replace(" ", "_").replace(".", "_")

    if var_name in seen_names:
        safe_parent = parent.replace("-", "_").replace(" ", "_")
        var_name    = f"{var_name}_{safe_parent}"

    seen_names.add(var_name)
    return var_name


seen_images  = set()
seen_icons   = set()
seen_lotties = set()

# ── Collect all asset folders for pubspec update ──────────────────
asset_folders = set()

for root, dirs, files in os.walk(assets_path):
    for file in sorted(files):
        full_path   = os.path.join(root, file).replace("\\", "/")
        folder_path = os.path.dirname(full_path) + "/"   # e.g. "assets/images/"

        if file.endswith(('.png', '.jpg', '.jpeg', '.webp')):
            var = make_var_name(full_path, seen_images)
            images.append((var, full_path))
            asset_folders.add(folder_path)
        elif file.endswith('.svg'):
            var = make_var_name(full_path, seen_icons)
            icons.append((var, full_path))
            asset_folders.add(folder_path)
        elif file.endswith('.json'):
            var = make_var_name(full_path, seen_lotties)
            lotties.append((var, full_path))
            asset_folders.add(folder_path)


# ── pubspec.yaml auto-update ──────────────────────────────────────
#
# Finds the `flutter:` section and updates (or creates) the `assets:` block.
# Only touches the assets list — everything else stays untouched.
#
# Before:
#   flutter:
#     uses-material-design: true
#
# After:
#   flutter:
#     uses-material-design: true
#     assets:
#       - assets/images/
#       - assets/icons/
#       - assets/lotties/

def update_pubspec(folders):
    if not os.path.exists(pubspec):
        print(f"⚠️  {pubspec} not found — skipping pubspec update.")
        return

    with open(pubspec, "r", encoding="utf-8") as f:
        content = f.read()

    sorted_folders = sorted(folders)
    assets_lines   = "\n".join(f"    - {folder}" for folder in sorted_folders)
    assets_block   = f"  assets:\n{assets_lines}"

    # Does flutter: section exist?
    if "flutter:" not in content:
        print("⚠️  No 'flutter:' section found in pubspec.yaml — skipping.")
        return

    # Does assets: block already exist inside flutter: section?
    # Replace it entirely with the new one.
    if re.search(r"(?m)^  assets:", content):
        # Remove old assets block (assets: + all its list items)
        content = re.sub(
            r"(?m)^  assets:(\n    - .+)*",
            assets_block,
            content,
        )
        print(f"♻️  Updated assets block in {pubspec}")
    else:
        # Insert after flutter: line
        content = content.replace(
            "flutter:",
            f"flutter:\n{assets_block}",
            1,
        )
        print(f"✅ Added assets block to {pubspec}")

    with open(pubspec, "w", encoding="utf-8") as f:
        f.write(content)

    print("   Folders registered:")
    for folder in sorted_folders:
        print(f"   - {folder}")


# ── Shared writer ─────────────────────────────────────────────────
def write_class(class_name, base_var, items, output_file):
    if not items:
        return

    base = os.path.dirname(items[0][1]) if items else "assets"

    lines = [
        "// AUTO GENERATED — do not edit manually",
        "// Run: python assets_script.py\n",
        f"class {class_name} {{",
        f"  {class_name}._();\n",
        f"  static const String _{base_var}Route = '{base}';\n",
    ]

    for var, path in items:
        filename = os.path.basename(path)
        lines.append(
            f"  static const String {var} = '$_{base_var}Route/{filename}';",
        )

    lines.append("}\n")

    content = "\n".join(lines)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Generated {os.path.basename(output_file)} ({len(items)} entries)")

    for var, path in items:
        stem = os.path.splitext(os.path.basename(path))[0]\
                 .replace("-", "_").replace(" ", "_").replace(".", "_")
        if var != stem:
            print(f"   ⚠️  '{stem}' conflict → renamed to '{var}' ({path})")


# ── Run ───────────────────────────────────────────────────────────
write_class("AppIcons",   "_icons",   icons,   f"{output_dir}/app_icons.dart")
write_class("AppImages",  "_images",  images,  f"{output_dir}/app_images.dart")
write_class("AppLotties", "_lotties", lotties, f"{output_dir}/app_lotties.dart")

# ── pubspec update ────────────────────────────────────────────────
if asset_folders:
    print()
    update_pubspec(asset_folders)

print("\nDone! Files saved to lib/assets_helper/")
