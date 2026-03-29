import os
import re
import yaml

PUBSPEC_FILE = "pubspec.yaml"
LIB_FOLDER = "lib"

def get_dependencies():
    with open(PUBSPEC_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    deps = data.get("dependencies", {})
    dev_deps = data.get("dev_dependencies", {})

    return set(deps.keys()), set(dev_deps.keys()), data


def get_all_dart_files():
    dart_files = []
    for root, _, files in os.walk(LIB_FOLDER):
        for file in files:
            if file.endswith(".dart"):
                dart_files.append(os.path.join(root, file))
    return dart_files


def find_used_packages(dart_files):
    used = set()
    import_pattern = re.compile(r"package:([\w_]+)/")

    for file in dart_files:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            matches = import_pattern.findall(content)
            used.update(matches)

    return used


def main():
    print("🔍 Scanning project...\n")

    deps, dev_deps, yaml_data = get_dependencies()
    dart_files = get_all_dart_files()
    used = find_used_packages(dart_files)

    unused_deps = deps - used
    unused_dev_deps = dev_deps - used

    print("📦 Unused dependencies:")
    for d in unused_deps:
        print(f"  ❌ {d}")

    print("\n🛠️ Unused dev_dependencies:")
    for d in unused_dev_deps:
        print(f"  ❌ {d}")

    # Optional removal
    choice = input("\nRemove unused packages? (y/n): ").lower()

    if choice == "y":
        for d in unused_deps:
            yaml_data["dependencies"].pop(d, None)

        for d in unused_dev_deps:
            yaml_data["dev_dependencies"].pop(d, None)

        with open(PUBSPEC_FILE, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f, sort_keys=False)

        print("\n✅ Removed unused packages!")
        print("👉 Run: flutter pub get")

    else:
        print("\n👍 No changes made.")


if __name__ == "__main__":
    main()