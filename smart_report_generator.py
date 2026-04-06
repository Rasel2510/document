import subprocess
import os
import re
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# CONFIG — edit these
# ──────────────────────────────────────────────
YOUR_NAME    = "Md Rasel Mia"
CLIENT_NAME  = "thedoctor0101"
PROFILE_NAME = "Webgenius0"
GITHUB_URL   = "https://github.com/softvenceofficial/thedoctor0101_flutter"
GIT_USERNAME = "rasel2510"
REPORT_DIR   = "reports"

# ──────────────────────────────────────────────
# FILE PATTERN DETECTION
# ──────────────────────────────────────────────

def detect_action(status):
    """A=Added, M=Modified, D=Deleted, R=Renamed"""
    if status == 'A': return 'Created'
    if status == 'M': return 'Updated'
    if status == 'D': return 'Removed'
    if status.startswith('R'): return 'Renamed'
    return 'Modified'


def detect_section(filepath):
    """Detect section based on file path"""
    path = filepath.lower()

    # AUTH
    if any(k in path for k in ['auth', 'login', 'signup', 'register',
                                'otp', 'password', 'forgot']):
        return '🔐 Authentication'

    # API / DATA
    if any(k in path for k in ['api', 'rx', 'repository', 'datasource',
                                'endpoint', 'service', 'network']):
        return '🔌 API Integration'

    # MODELS
    if any(k in path for k in ['model', 'entity', 'response', 'request']):
        return '🗂️  Models'

    # SCREENS / PRESENTATION
    if any(k in path for k in ['screen', 'page', 'presentation', 'view']):
        return '📱 Screens'

    # WIDGETS
    if any(k in path for k in ['widget', 'component', 'card',
                                'button', 'dialog']):
        return '🧩 Widgets'

    # PROFILE
    if 'profile' in path:
        return '👤 Profile'

    # BOOKING
    if any(k in path for k in ['book', 'booking', 'reservation']):
        return '📅 Booking'

    # HOME
    if 'home' in path:
        return '🏠 Home'

    # NAVIGATION
    if any(k in path for k in ['nav', 'route', 'navigation']):
        return '🧭 Navigation'

    # CONSTANTS / CONFIG
    if any(k in path for k in ['constant', 'config', 'theme',
                                'color', 'style', 'font']):
        return '⚙️  Configuration'

    # ASSETS
    if any(k in path for k in ['asset', 'image', 'icon', 'lottie']):
        return '🎨 Assets'

    # HELPERS / UTILS
    if any(k in path for k in ['helper', 'util', 'extension',
                                'common', 'shared']):
        return '🛠️  Helpers'

    # PUBSPEC
    if 'pubspec' in path:
        return '📦 Dependencies'

    return '✅ General'


def clean_filename(filepath):
    """Convert file path to readable task description"""
    filename = os.path.basename(filepath)
    name     = os.path.splitext(filename)[0]

    # convert snake_case to Title Case
    words = name.replace('_', ' ').replace('-', ' ').split()
    name  = ' '.join(w.capitalize() for w in words)

    # fix common tech words
    replacements = {
        'Api'  : 'API',
        'Ui'   : 'UI',
        'Ux'   : 'UX',
        'Http' : 'HTTP',
        'Json' : 'JSON',
        'Id'   : 'ID',
        'Rx'   : 'Rx',
        'Otp'  : 'OTP',
        'Url'  : 'URL',
    }
    for wrong, right in replacements.items():
        name = name.replace(wrong, right)

    return name


def build_task_description(action, filepath):
    """Build professional task description from file change"""
    name   = clean_filename(filepath)
    folder = os.path.dirname(filepath).lower()
    ext    = os.path.splitext(filepath)[1]

    # determine file type
    if 'model' in folder or 'model' in filepath.lower():
        file_type = 'model'
    elif 'screen' in folder or 'page' in folder:
        file_type = 'screen'
    elif 'widget' in folder:
        file_type = 'widget'
    elif 'api' in folder:
        file_type = 'API class'
    elif 'rx' in filepath.lower():
        file_type = 'Rx class'
    elif ext == '.dart':
        file_type = 'class'
    elif ext in ['.png', '.jpg', '.svg', '.json']:
        file_type = 'asset'
    elif 'pubspec' in filepath.lower():
        file_type = 'dependencies'
    else:
        file_type = 'file'

    if file_type == 'dependencies':
        return f"{action} package dependencies"
    elif file_type == 'asset':
        return f"{action} {name} asset"
    else:
        return f"{action} {name} {file_type}"


# ──────────────────────────────────────────────
# GIT HELPERS
# ──────────────────────────────────────────────

def run(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd, shell=True,
            capture_output=True, text=True, cwd=cwd
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_commits_with_files(repo_path, author, since, until):
    """Get each commit with its changed files"""
    hash_cmd = (
        f'git log '
        f'--author="{author}" '
        f'--since="{since}" '
        f'--until="{until}" '
        f'--no-merges '
        f'--format="%H"'
    )
    hashes = run(hash_cmd, cwd=repo_path)
    if not hashes:
        return []

    commits = []
    for commit_hash in hashes.splitlines():
        commit_hash = commit_hash.strip()
        if not commit_hash:
            continue

        diff_cmd = f'git diff-tree --no-commit-id -r --name-status {commit_hash}'
        diff_output = run(diff_cmd, cwd=repo_path)

        files = []
        for line in diff_output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                status   = parts[0]
                filepath = parts[-1]
                files.append((status, filepath))

        commits.append({'hash': commit_hash, 'files': files})

    return commits


def format_date(date):
    return date.strftime("%d/%m/%Y")


# ──────────────────────────────────────────────
# REPORT GENERATOR
# ──────────────────────────────────────────────

def generate_report(repo_path, author, date):
    since = f"{date.strftime('%Y-%m-%d')} 00:00"
    until = f"{date.strftime('%Y-%m-%d')} 23:59"

    commits = get_commits_with_files(repo_path, author, since, until)
    if not commits:
        return None

    sections = {}
    seen     = set()

    # files to skip
    skip_patterns = [
        '.g.dart', '.freezed.dart',
        'pubspec.lock', '.gitignore',
        '.metadata', 'analysis_options',
        '.iml', '.gradle', 'gradlew',
    ]

    for commit in commits:
        for status, filepath in commit['files']:
            if any(p in filepath for p in skip_patterns):
                continue

            action      = detect_action(status)
            section     = detect_section(filepath)
            description = build_task_description(action, filepath)

            key = f"{action}_{filepath}"
            if key in seen:
                continue
            seen.add(key)

            if section not in sections:
                sections[section] = []
            sections[section].append({
                'description': description,
                'filepath'   : filepath,
                'action'     : action,
            })

    return sections if sections else None


def build_report_text(sections, date, is_week=False, week_range=None):
    lines = []
    lines.append("=" * 55)
    lines.append("       📋 Daily Work Report")
    lines.append("=" * 55)
    lines.append("")

    if is_week and week_range:
        lines.append(f"Week    : {week_range}")
    else:
        lines.append(f"Date    : {format_date(date)}")

    lines.append(f"Name    : {YOUR_NAME}")
    lines.append(f"Client  : {CLIENT_NAME}")
    lines.append(f"Profile : {PROFILE_NAME}")
    lines.append("")
    lines.append("─" * 55)
    lines.append("Completed Tasks:")
    lines.append("─" * 55)
    lines.append("")

    if not sections:
        lines.append("  No changes found.")
    else:
        total = 0
        for section, tasks in sorted(sections.items()):
            lines.append(f"  {section}")
            for task in tasks:
                lines.append(f"  - {task['description']}")
                total += 1
            lines.append("")

        lines.append("─" * 55)
        lines.append(f"  Total: {total} files changed")

    lines.append("")
    lines.append("─" * 55)
    lines.append(f"GitHub  : {GITHUB_URL}")
    lines.append(f"Git     : {GIT_USERNAME}")
    lines.append("=" * 55)

    return "\n".join(lines)


# ──────────────────────────────────────────────
# SAVE & DISPLAY
# ──────────────────────────────────────────────

def save_report(text, date, prefix="report"):
    os.makedirs(REPORT_DIR, exist_ok=True)
    filename = os.path.join(
        REPORT_DIR,
        f"{prefix}_{date.strftime('%Y-%m-%d')}.txt"
    )
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    return filename


def display_and_save(sections, date, label="", is_week=False, week_range=None):
    if not sections:
        print(f"\n😴 No file changes found for {label or format_date(date)}")
        return

    report_text = build_report_text(
        sections, date,
        is_week=is_week,
        week_range=week_range,
    )

    print("\n" + report_text)

    filename = save_report(report_text, date)
    print(f"\n✅ Report saved: {filename}")

    try:
        import pyperclip
        pyperclip.copy(report_text)
        print("📋 Copied to clipboard!")
    except ImportError:
        print("💡 Run: pip install pyperclip  ← for clipboard support")


# ──────────────────────────────────────────────
# REPORT FLOWS
# ──────────────────────────────────────────────

def today_report(repo_path):
    date     = datetime.now().date()
    sections = generate_report(repo_path, GIT_USERNAME, date)
    display_and_save(sections, date, "Today")


def yesterday_report(repo_path):
    today = datetime.now().date()
    date  = today - timedelta(days=3 if today.weekday() == 0 else 1)
    sections = generate_report(repo_path, GIT_USERNAME, date)
    display_and_save(sections, date, "Yesterday")


def custom_date_report(repo_path):
    date_str = input("  Enter date (YYYY-MM-DD): ").strip()
    try:
        date     = datetime.strptime(date_str, "%Y-%m-%d").date()
        sections = generate_report(repo_path, GIT_USERNAME, date)
        display_and_save(sections, date)
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")


def week_report(repo_path):
    today        = datetime.now().date()
    all_sections = {}

    print(f"\n📆 Scanning last 7 days...\n")

    for i in range(6, -1, -1):
        date     = today - timedelta(days=i)
        sections = generate_report(repo_path, GIT_USERNAME, date)

        if sections:
            print(f"  ✅ {format_date(date)} — changes found")
            for section, tasks in sections.items():
                if section not in all_sections:
                    all_sections[section] = []
                existing = {t['filepath'] for t in all_sections[section]}
                for task in tasks:
                    if task['filepath'] not in existing:
                        all_sections[section].append(task)
                        existing.add(task['filepath'])
        else:
            print(f"  ⬜ {format_date(date)} — no changes")

    week_range = (
        f"{format_date(today - timedelta(days=6))} → {format_date(today)}"
    )
    display_and_save(
        all_sections, today,
        label="This Week",
        is_week=True,
        week_range=week_range,
    )


# ──────────────────────────────────────────────
# ENTRY
# ──────────────────────────────────────────────

def main():
    print("\n" + "=" * 55)
    print("  📋 Smart File-Based Report Generator")
    print("  Reads actual file changes — not commit messages")
    print("=" * 55)

    path = input(
        "\n  Repo path (leave blank for current dir): "
    ).strip().strip('"') or "."

    if not os.path.exists(os.path.join(path, ".git")):
        print("❌ Not a git repository.")
        return

    while True:
        print(f"\n  1. 📋 Today's report")
        print(f"  2. 📋 Yesterday's report")
        print(f"  3. 📅 Custom date")
        print(f"  4. 📆 This week")
        print(f"  0. 👋 Exit")

        choice = input("\n  Choose: ").strip()

        if   choice == "1": today_report(path)
        elif choice == "2": yesterday_report(path)
        elif choice == "3": custom_date_report(path)
        elif choice == "4": week_report(path)
        elif choice == "0":
            print("\n  👋 Bye!\n")
            break
        else:
            print("  ❌ Invalid choice.")


if __name__ == "__main__":
    main()
