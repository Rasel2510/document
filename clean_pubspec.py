import os
import re
import shutil
from ruamel.yaml import YAML

PUBSPEC_FILE = "pubspec.yaml"
LIB_FOLDER = "lib"

yaml = YAML()
yaml.preserve_quotes = True


def backup_pubspec():
    backup_file = "pubspec_backup.yaml"
    shutil.copy(PUBSPEC_FILE, backup_file)
    print(f"📦 Backup created → {backup_file}")


def load_pubspec():
    with open(PUBSPEC_FILE, "r", encoding="utf-8") as f:
        return yaml.load(f)


def save_pubspec(data):
    with open(PUBSPEC_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


def get_dependencies(data):
    deps = set(data.get("dependencies", {}).keys())
    dev_deps = set(data.get("dev_dependencies", {}).keys())
    return deps, dev_deps


def get_all_dart_files():
    dart_files = []
    for root, _, files in os.walk(LIB_FOLDER):
        for file in files:
            if file.endswith(".dart"):
                dart_files.append(os.path.join(root, file))
    return dart_files


def find_used_packages(dart_files):
    used = set()
    pattern = re.compile(r"package:([\w_]+)/")

    for file in dart_files:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            matches = pattern.findall(content)
            used.update(matches)

    return used


def remove_unused(data, unused_deps, unused_dev_deps):
    if "dependencies" in data:
        for dep in unused_deps:
            data["dependencies"].pop(dep, None)

    if "dev_dependencies" in data:
        for dep in unused_dev_deps:
            data["dev_dependencies"].pop(dep, None)


def main():
    print("\n🔍 Scanning Flutter project...\n")

    if not os.path.exists(PUBSPEC_FILE):
        print("❌ pubspec.yaml not found!")
        return

    data = load_pubspec()
    deps, dev_deps = get_dependencies(data)

    dart_files = get_all_dart_files()
    used_packages = find_used_packages(dart_files)

    unused_deps = deps - used_packages
    unused_dev_deps = dev_deps - used_packages

    print("📦 Unused dependencies:")
    if unused_deps:
        for d in unused_deps:
            print(f"  ❌ {d}")
    else:
        print("  ✅ None")

    print("\n🛠️ Unused dev_dependencies:")
    if unused_dev_deps:
        for d in unused_dev_deps:
            print(f"  ❌ {d}")
    else:
        print("  ✅ None")

    if not unused_deps and not unused_dev_deps:
        print("\n🎉 Nothing to clean!")
        return

    choice = input("\n⚠️ Remove these packages? (y/n): ").lower()

    if choice == "y":
        backup_pubspec()
        remove_unused(data, unused_deps, unused_dev_deps)
        save_pubspec(data)

        print("\n✅ Unused packages removed safely!")
        print("💬 Comments and formatting preserved")
        print("👉 Run: flutter pub get\n")
    else:
        print("\n👍 No changes made.\n")


if __name__ == "__main__":
    main()