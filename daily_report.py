import subprocess
import os
import json
import re
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# CONFIG — edit these
# ──────────────────────────────────────────────
YOUR_NAME     = "Md Rasel Mia"
CLIENT_NAME   = "thedoctor0101"
PROFILE_NAME  = "Webgenius0"
GITHUB_URL    = "https://github.com/softvenceofficial/thedoctor0101_flutter"
GIT_USERNAME  = "rasel2510"
REPORT_DIR    = "reports"

# ──────────────────────────────────────────────
# SMART KEYWORD DETECTION
# ──────────────────────────────────────────────

ACTION_KEYWORDS = {
    # Fix
    "fix":        "Fixed",
    "fixed":      "Fixed",
    "bug":        "Fixed",
    "bugfix":     "Fixed",
    "resolve":    "Resolved",
    "resolved":   "Resolved",
    "patch":      "Patched",

    # Add / Implement
    "add":        "Implemented",
    "added":      "Implemented",
    "implement":  "Implemented",
    "implemented":"Implemented",
    "create":     "Created",
    "created":    "Created",
    "new":        "Implemented",
    "build":      "Built",
    "built":      "Built",
    "develop":    "Developed",

    # Update / Improve
    "update":     "Updated",
    "updated":    "Updated",
    "upgrade":    "Upgraded",
    "improve":    "Improved",
    "improved":   "Improved",
    "enhance":    "Enhanced",
    "refactor":   "Refactored",
    "refactored": "Refactored",
    "clean":      "Cleaned up",
    "cleanup":    "Cleaned up",
    "optimize":   "Optimized",
    "optimized":  "Optimized",
    "redesign":   "Redesigned",

    # Remove
    "remove":     "Removed",
    "removed":    "Removed",
    "delete":     "Removed",
    "deleted":    "Removed",

    # Complete
    "complete":   "Completed",
    "completed":  "Completed",
    "done":       "Completed",
    "finish":     "Completed",
    "finished":   "Completed",

    # Integration
    "integrate":  "Integrated",
    "integrated": "Integrated",
    "connect":    "Connected",
    "connected":  "Connected",
    "setup":      "Set up",
    "configure":  "Configured",

    # UI
    "ui":         "Improved UI for",
    "screen":     "Updated",
    "widget":     "Updated",
    "design":     "Updated design for",

    # API
    "api":        "Completed",
}

SECTION_KEYWORDS = {
    "api":    "🔌 API Integration",
    "ui":     "🎨 UI / Design",
    "fix":    "🐛 Bug Fixes",
    "bug":    "🐛 Bug Fixes",
    "screen": "📱 Screens",
    "widget": "📱 Screens",
    "auth":   "🔐 Authentication",
    "login":  "🔐 Authentication",
    "signup": "🔐 Authentication",
    "profile":"👤 Profile",
    "model":  "🗂️  Models",
    "test":   "🧪 Tests",
    "config": "⚙️  Configuration",
    "refactor":"♻️  Refactoring",
}

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def run(cmd, cwd=None):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return result.stdout.strip()
    except Exception:
        return ""

def format_date(date):
    return date.strftime("%d/%m/%Y")

def clean_commit(message):
    """Convert raw commit to professional task description"""
    msg = message.strip()

    # remove common prefixes like feat:, fix:, chore:, etc.
    msg = re.sub(r'^(feat|fix|chore|docs|style|refactor|test|build|ci|perf)(\(.+?\))?:\s*', '', msg, flags=re.IGNORECASE)

    # remove issue numbers like #123
    msg = re.sub(r'#\d+', '', msg).strip()

    # title case
    words = msg.split()
    if not words:
        return None

    first_word = words[0].lower()
    action = ACTION_KEYWORDS.get(first_word)

    if action:
        # replace first word with proper action verb
        rest = ' '.join(words[1:])
        rest = rest.strip()
        if rest:
            msg = f"{action} {rest}"
        else:
            msg = action
    else:
        # capitalize first letter
        msg = msg[0].upper() + msg[1:]

    # title case important tech words
    tech_words = {
        "api": "API", "ui": "UI", "ux": "UX", "id": "ID",
        "url": "URL", "http": "HTTP", "json": "JSON",
        "dio": "Dio", "flutter": "Flutter", "dart": "Dart",
    }
    for word, replacement in tech_words.items():
        msg = re.sub(rf'\b{word}\b', replacement, msg, flags=re.IGNORECASE)

    return msg


def detect_section(message):
    msg_lower = message.lower()
    for keyword, section in SECTION_KEYWORDS.items():
        if keyword in msg_lower:
            return section
    return "✅ General Tasks"


def deduplicate(tasks):
    """Remove very similar tasks"""
    seen = []
    result = []
    for task in tasks:
        simplified = re.sub(r'\s+', ' ', task.lower().strip())
        simplified = re.sub(r'(ed|ing|s)\b', '', simplified)
        if not any(simplified in s or s in simplified for s in seen):
            seen.append(simplified)
            result.append(task)
    return result


def get_commits(repo_path, author, since, until):
    cmd = (
        f'git log '
        f'--author="{author}" '
        f'--since="{since}" '
        f'--until="{until}" '
        f'--no-merges '
        f'--format="%s"'
    )
    output = run(cmd, cwd=repo_path)
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]

# ──────────────────────────────────────────────
# REPORT GENERATOR
# ──────────────────────────────────────────────

def generate_report(repo_path, author, date):
    since = f"{date.strftime('%Y-%m-%d')} 00:00"
    until = f"{date.strftime('%Y-%m-%d')} 23:59"

    raw_commits = get_commits(repo_path, author, since, until)

    if not raw_commits:
        return None, []

    # clean and categorize
    sections = {}
    for commit in raw_commits:
        cleaned = clean_commit(commit)
        if not cleaned:
            continue
        section = detect_section(commit)
        if section not in sections:
            sections[section] = []
        sections[section].append(cleaned)

    # deduplicate per section
    for section in sections:
        sections[section] = deduplicate(sections[section])

    return sections, raw_commits


def build_report_text(sections, date):
    lines = []
    lines.append(f"Date: {format_date(date)}")
    lines.append(f"Name: {YOUR_NAME}")
    lines.append(f"Client Name: {CLIENT_NAME}")
    lines.append(f"Profile Name: {PROFILE_NAME}")
    lines.append("")
    lines.append("Completed Tasks:")

    if not sections:
        lines.append("  No commits found for this date.")
    else:
        for section, tasks in sections.items():
            lines.append(f"\n  {section}")
            for task in tasks:
                lines.append(f"  - {task}")

    lines.append("")
    lines.append("GitHub:")
    lines.append(GITHUB_URL)
    lines.append("")
    lines.append(f"Git: {GIT_USERNAME}")

    return "\n".join(lines)

# ──────────────────────────────────────────────
# SAVE REPORT
# ──────────────────────────────────────────────

def save_report(text, date):
    os.makedirs(REPORT_DIR, exist_ok=True)
    filename = os.path.join(REPORT_DIR, f"report_{date.strftime('%Y-%m-%d')}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    return filename

# ──────────────────────────────────────────────
# MAIN FLOWS
# ──────────────────────────────────────────────

def report_for_date(repo_path, date, label=""):
    print(f"\n⏳ Generating report for {label or format_date(date)}...")

    sections, raw = generate_report(repo_path, GIT_USERNAME, date)

    if not sections:
        print(f"😴 No commits found for {format_date(date)}")
        return

    report_text = build_report_text(sections, date)

    print("\n" + "=" * 55)
    print(report_text)
    print("=" * 55)

    filename = save_report(report_text, date)
    print(f"\n✅ Report saved to: {filename}")

    # copy to clipboard
    try:
        import pyperclip
        pyperclip.copy(report_text)
        print("📋 Copied to clipboard!")
    except ImportError:
        print("💡 Run: py -m pip install pyperclip  (for clipboard support)")

    print(f"\n📊 Raw commits processed: {len(raw)}")


def today_report(repo_path):
    today = datetime.now().date()
    report_for_date(repo_path, today, "Today")


def yesterday_report(repo_path):
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    if today.weekday() == 0:
        yesterday = today - timedelta(days=3)
    report_for_date(repo_path, yesterday, "Yesterday")


def custom_date_report(repo_path):
    date_str = input("  Enter date (YYYY-MM-DD): ").strip()
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        report_for_date(repo_path, date)
    except ValueError:
        print("❌ Invalid date format.")


def week_report(repo_path):
    today = datetime.now().date()
    print(f"\n📆 Generating weekly report ({today - timedelta(days=6)} → {today})\n")

    all_sections = {}
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        sections, _ = generate_report(repo_path, GIT_USERNAME, date)
        if sections:
            print(f"  ✅ {format_date(date)} — found commits")
            for section, tasks in sections.items():
                if section not in all_sections:
                    all_sections[section] = []
                all_sections[section].extend(tasks)
        else:
            print(f"  ⬜ {format_date(date)} — no commits")

    # deduplicate across days
    for section in all_sections:
        all_sections[section] = deduplicate(all_sections[section])

    if not all_sections:
        print("\n😴 No commits found this week.")
        return

    report_text = build_report_text(all_sections, today)
    report_text = report_text.replace(
        f"Date: {format_date(today)}",
        f"Week: {format_date(today - timedelta(days=6))} → {format_date(today)}"
    )

    print("\n" + "=" * 55)
    print(report_text)
    print("=" * 55)

    filename = save_report(report_text, today)
    print(f"\n✅ Weekly report saved to: {filename}")

# ──────────────────────────────────────────────
# ENTRY
# ──────────────────────────────────────────────

def main():
    print("\n" + "=" * 55)
    print("       📋 Smart Daily Report Generator")
    print("=" * 55)

    path = input("\n  Repo path (leave blank for current dir): ").strip().strip('"') or "."

    if not os.path.exists(os.path.join(path, ".git")):
        print("❌ Not a git repository.")
        return

    while True:
        print(f"\n  1. 📋 Today's report")
        print(f"  2. 📋 Yesterday's report")
        print(f"  3. 📅 Custom date report")
        print(f"  4. 📆 This week report")
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
