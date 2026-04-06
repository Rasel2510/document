import subprocess
import os
from datetime import datetime, timedelta

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
YOUR_NAME = ""  # leave empty to auto detect from git config

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def run(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, cwd=cwd
        )
        return result.stdout.strip()
    except Exception:
        return ""

def get_author():
    if YOUR_NAME:
        return YOUR_NAME
    return run("git config user.name")

def is_git_repo(path):
    return os.path.exists(os.path.join(path, ".git"))

def find_git_repos(root):
    repos = []
    for item in os.listdir(root):
        full = os.path.join(root, item)
        if os.path.isdir(full) and is_git_repo(full):
            repos.append(full)
    return repos

def get_commits(repo_path, author, since, until):
    cmd = (
        f'git log '
        f'--author="{author}" '
        f'--since="{since}" '
        f'--until="{until}" '
        f'--oneline '
        f'--no-merges '
        f'--format="%s"'
    )
    output = run(cmd, cwd=repo_path)
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]

def get_branch(repo_path):
    return run("git branch --show-current", cwd=repo_path)

def get_repo_name(repo_path):
    return os.path.basename(repo_path)

def format_date(date):
    return date.strftime("%Y-%m-%d")

def print_section(title):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")

# ──────────────────────────────────────────────
# STANDUP GENERATOR
# ──────────────────────────────────────────────

def generate_standup(repos, author, since, until, label):
    all_commits = {}

    for repo in repos:
        commits = get_commits(repo, author, since, until)
        if commits:
            name = get_repo_name(repo)
            branch = get_branch(repo)
            all_commits[f"{name} ({branch})"] = commits

    print_section(f"📋 {label} — {author}")

    if not all_commits:
        print(f"\n  😴 No commits found for {label.lower()}.")
        return []

    lines = []
    for repo, commits in all_commits.items():
        print(f"\n  📁 {repo}")
        for commit in commits:
            print(f"     • {commit}")
            lines.append(f"• [{repo}] {commit}")

    return lines

def export_standup(yesterday_lines, today_lines, blockers):
    filename = f"standup_{datetime.now().strftime('%Y-%m-%d')}.txt"
    with open(filename, "w") as f:
        f.write(f"Daily Standup — {datetime.now().strftime('%A, %d %B %Y')}\n")
        f.write("=" * 50 + "\n\n")

        f.write("✅ WHAT I DID YESTERDAY:\n")
        if yesterday_lines:
            for line in yesterday_lines:
                f.write(f"  {line}\n")
        else:
            f.write("  No commits.\n")

        f.write("\n🔨 WHAT I'M DOING TODAY:\n")
        if today_lines:
            for line in today_lines:
                f.write(f"  {line}\n")
        else:
            f.write("  No commits yet.\n")

        f.write("\n🚧 BLOCKERS:\n")
        f.write(f"  {blockers if blockers else 'None'}\n")

    print(f"\n✅ Standup saved to: {filename}")
    return filename

def copy_to_clipboard(text):
    try:
        import pyperclip
        pyperclip.copy(text)
        print("📋 Copied to clipboard!")
    except ImportError:
        print("💡 Install pyperclip to auto-copy: py -m pip install pyperclip")

# ──────────────────────────────────────────────
# MAIN FLOWS
# ──────────────────────────────────────────────

def single_repo_standup():
    print_section("📁 Single Repo Standup")
    path = input("  Repo path (leave blank for current dir): ").strip().strip('"') or "."

    if not is_git_repo(path):
        print("❌ Not a git repository.")
        return

    author = get_author()
    if not author:
        author = input("  Your name (as in git): ").strip()

    today     = datetime.now().date()
    yesterday = today - timedelta(days=1)

    # skip weekend — if Monday show Friday
    if today.weekday() == 0:
        yesterday = today - timedelta(days=3)

    print(f"\n  👤 Author : {author}")
    print(f"  📅 Today  : {format_date(today)}")
    print(f"  📅 Yesterday: {format_date(yesterday)}")

    yesterday_lines = generate_standup(
        [path], author,
        f"{format_date(yesterday)} 00:00",
        f"{format_date(yesterday)} 23:59",
        "Yesterday"
    )

    today_lines = generate_standup(
        [path], author,
        f"{format_date(today)} 00:00",
        f"{format_date(today)} 23:59",
        "Today"
    )

    print_section("🚧 Blockers")
    blockers = input("  Any blockers? (leave blank for none): ").strip()

    filename = export_standup(yesterday_lines, today_lines, blockers)

    # build clipboard text
    text = f"*Daily Standup — {datetime.now().strftime('%A, %d %B %Y')}*\n\n"
    text += "*✅ Yesterday:*\n"
    text += "\n".join(yesterday_lines) if yesterday_lines else "No commits."
    text += "\n\n*🔨 Today:*\n"
    text += "\n".join(today_lines) if today_lines else "No commits yet."
    text += f"\n\n*🚧 Blockers:*\n{blockers if blockers else 'None'}"

    print("\n" + "─" * 50)
    print(text)
    print("─" * 50)

    copy = input("\n  Copy to clipboard? (y/n): ").strip().lower()
    if copy == "y":
        copy_to_clipboard(text)


def multi_repo_standup():
    print_section("📂 Multi Repo Standup")
    folder = input("  Folder containing your repos: ").strip().strip('"')

    if not os.path.exists(folder):
        print("❌ Folder not found.")
        return

    repos = find_git_repos(folder)
    if not repos:
        print("❌ No git repos found in that folder.")
        return

    print(f"\n  Found {len(repos)} repos:")
    for r in repos:
        print(f"   • {get_repo_name(r)}")

    author = get_author()
    if not author:
        author = input("\n  Your name (as in git): ").strip()

    today     = datetime.now().date()
    yesterday = today - timedelta(days=1)
    if today.weekday() == 0:
        yesterday = today - timedelta(days=3)

    yesterday_lines = generate_standup(
        repos, author,
        f"{format_date(yesterday)} 00:00",
        f"{format_date(yesterday)} 23:59",
        "Yesterday"
    )

    today_lines = generate_standup(
        repos, author,
        f"{format_date(today)} 00:00",
        f"{format_date(today)} 23:59",
        "Today"
    )

    print_section("🚧 Blockers")
    blockers = input("  Any blockers? (leave blank for none): ").strip()

    export_standup(yesterday_lines, today_lines, blockers)


def custom_date_standup():
    print_section("📅 Custom Date Standup")
    path = input("  Repo path (leave blank for current dir): ").strip().strip('"') or "."

    if not is_git_repo(path):
        print("❌ Not a git repository.")
        return

    author = get_author()
    if not author:
        author = input("  Your name (as in git): ").strip()

    date_str = input("  Date (YYYY-MM-DD): ").strip()
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print("❌ Invalid date format.")
        return

    generate_standup(
        [path], author,
        f"{format_date(date)} 00:00",
        f"{format_date(date)} 23:59",
        format_date(date)
    )


# ──────────────────────────────────────────────
# ENTRY
# ──────────────────────────────────────────────

def main():
    print("\n" + "=" * 50)
    print("       🗣️  Git Standup Generator")
    print("=" * 50)

    while True:
        print("\n  1. Single repo standup (today)")
        print("  2. Multi repo standup")
        print("  3. Custom date commits")
        print("  0. Exit")

        choice = input("\n  Choose: ").strip()

        if   choice == "1": single_repo_standup()
        elif choice == "2": multi_repo_standup()
        elif choice == "3": custom_date_standup()
        elif choice == "0":
            print("\n  👋 Bye!\n")
            break
        else:
            print("  ❌ Invalid choice.")

if __name__ == "__main__":
    main()
