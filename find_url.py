import os
import sys

SEARCH_TERMS = [
    "admin.yukancv.ai",
    "const String url",
    "baseUrl",
]

def search_in_project(root_dir):
    print(f"\n🔍 Searching in: {root_dir}\n")
    found_any = False

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip build and cache folders
        dirnames[:] = [d for d in dirnames if d not in {
            '.dart_tool', '.gradle', 'build', '.idea', 
            'android', 'ios', '.git', 'node_modules'
        }]

        for filename in filenames:
            if not filename.endswith('.dart'):
                continue

            filepath = os.path.join(dirpath, filename)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception:
                continue

            for i, line in enumerate(lines, start=1):
                for term in SEARCH_TERMS:
                    if term.lower() in line.lower():
                        print(f"📄 File : {filepath}")
                        print(f"   Line {i}: {line.strip()}")
                        print()
                        found_any = True
                        break

    if not found_any:
        print("❌ Nothing found. Make sure the path is correct.")
    else:
        print("✅ Search complete!")

if __name__ == "__main__":
    # Pass your Flutter project path as argument
    # Example: python find_url.py /path/to/your/flutter/project
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = input("Enter your Flutter project path: ").strip()

    if not os.path.exists(project_path):
        print(f"❌ Path not found: {project_path}")
    else:
        search_in_project(project_path)
