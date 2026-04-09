#!/usr/bin/env python3
"""
Flutter Crash Analyzer
======================
Reads Flutter/Android logcat output and pinpoints why the app crashes
after a successful login (loading dialog freeze → crash pattern).

USAGE:
    1. Capture logs BEFORE running this script:
         adb logcat -d > crash_log.txt          # dump current buffer
         adb logcat > crash_log.txt             # live capture (Ctrl+C to stop)

    2. Run:
         python analyze_flutter_crash.py                     # auto-finds crash_log.txt
         python analyze_flutter_crash.py my_log.txt          # custom file
         python analyze_flutter_crash.py --live              # read live from adb

    3. Optional: pipe directly
         adb logcat | python analyze_flutter_crash.py --stdin
"""

import sys
import re
import os
import subprocess
import argparse
from collections import defaultdict
from datetime import datetime

# ─── ANSI colours ────────────────────────────────────────────────────────────
RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def red(s):    return f"{RED}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def green(s):  return f"{GREEN}{s}{RESET}"
def cyan(s):   return f"{CYAN}{s}{RESET}"
def bold(s):   return f"{BOLD}{s}{RESET}"

# ─── PATTERNS ────────────────────────────────────────────────────────────────
# Each entry: (label, regex, severity)   severity: 'CRITICAL' | 'HIGH' | 'MEDIUM'
PATTERNS = [
    # ── Dart / Flutter fatal ──────────────────────────────────────────────
    ("DART FATAL",          r"E/flutter.*Fatal error",                       "CRITICAL"),
    ("DART UNHANDLED EXC",  r"E/flutter.*Unhandled Exception",               "CRITICAL"),
    ("DART EXCEPTION",      r"E/flutter.*Exception",                         "HIGH"),
    ("DART ERROR",          r"E/flutter.*Error",                             "HIGH"),
    ("DART ASSERTION",      r"E/flutter.*Assertion failed",                  "CRITICAL"),
    ("DART NULL",           r"E/flutter.*Null check operator",               "CRITICAL"),
    ("DART STACK",          r"#\d+\s+.*\(.*\.dart:\d+",                     "HIGH"),

    # ── Heap / Memory ─────────────────────────────────────────────────────
    ("HEAP EXHAUSTED",      r"Exhausted heap space",                         "CRITICAL"),
    ("OOM",                 r"OutOfMemoryError",                             "CRITICAL"),
    ("GC PRESSURE",         r"(Gc histogram|Reducing the number)",           "MEDIUM"),

    # ── Dart VM ───────────────────────────────────────────────────────────
    ("DARTVM ERROR",        r"E/DartVM",                                     "CRITICAL"),
    ("DARTVM CRASH",        r"(Segmentation fault|SIGSEGV|SIGABRT)",         "CRITICAL"),

    # ── Navigation / Route ────────────────────────────────────────────────
    ("NAVIGATOR ERROR",     r"(Navigator|Route|pop|push).*[Ee]rror",         "HIGH"),
    ("BUILD ERROR",         r"E/flutter.*build.*[Ee]rror",                   "HIGH"),
    ("WIDGET BUILD",        r"during.*build|setState.*called after dispose", "HIGH"),

    # ── State management ──────────────────────────────────────────────────
    ("DISPOSED WIDGET",     r"setState.*disposed",                           "HIGH"),
    ("PROVIDER ERROR",      r"(Provider|Bloc|Cubit).*[Ee]rror",             "HIGH"),
    ("GETX ERROR",          r"GetX.*[Ee]rror",                              "HIGH"),

    # ── Auth / Login specific ─────────────────────────────────────────────
    ("AUTH ERROR",          r"(auth|login|token|credential|session).*[Ee]rror", "HIGH"),
    ("TOKEN NULL",          r"(token|user|credential).*(null|empty|missing)", "HIGH"),
    ("SHARED PREFS",        r"SharedPreferences.*[Ee]rror",                  "HIGH"),
    ("SECURE STORAGE",      r"FlutterSecureStorage.*[Ee]rror",               "HIGH"),

    # ── Network ───────────────────────────────────────────────────────────
    ("NETWORK ERROR",       r"(SocketException|HttpException|DioError|http).*[Ee]rror", "HIGH"),
    ("TIMEOUT",             r"(TimeoutException|connection timed out)",      "HIGH"),
    ("CERT ERROR",          r"(HandshakeException|CertificateException)",    "HIGH"),

    # ── Dialog / Overlay ──────────────────────────────────────────────────
    ("DIALOG LEAK",         r"(showDialog|AlertDialog|OverlayEntry).*[Ee]rror", "HIGH"),
    ("LOADING DIALOG",      r"(loading|progress|indicator).*[Ee]rror",       "HIGH"),
    ("OVERLAY ERROR",       r"OverlayState.*not.*insert",                    "HIGH"),
    ("CONTEXT UNMOUNTED",   r"(context|BuildContext).*(deactivated|unmounted|disposed)", "HIGH"),

    # ── Platform / Android ────────────────────────────────────────────────
    ("ANR",                 r"ANR in",                                       "CRITICAL"),
    ("CRASH",               r"FATAL EXCEPTION",                              "CRITICAL"),
    ("JNI ERROR",           r"JNI ERROR",                                    "CRITICAL"),
    ("NATIVE CRASH",        r"(libc|signal \d+|crash_dump)",                 "CRITICAL"),

    # ── Firebase / Supabase ───────────────────────────────────────────────
    ("FIREBASE ERROR",      r"(FirebaseException|FirebaseAuth).*[Ee]rror",   "HIGH"),
    ("SUPABASE ERROR",      r"(SupabaseClient|supabase).*[Ee]rror",          "HIGH"),
]

# Lines that contain these substrings are likely the START of a crash block
CRASH_ANCHOR_PATTERNS = [
    r"FATAL EXCEPTION",
    r"E/flutter.*Unhandled Exception",
    r"E/flutter.*Fatal",
    r"E/DartVM.*Exhausted",
    r"Assertion failed",
    r"Null check operator used on a null value",
]

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def read_log_file(path: str) -> list[str]:
    encodings = ["utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, errors="replace") as f:
                return f.readlines()
        except Exception:
            continue
    print(red(f"[!] Could not read {path}"))
    sys.exit(1)


def read_adb_live() -> list[str]:
    print(cyan("[*] Reading live adb logcat ... press Ctrl+C to stop\n"))
    lines = []
    try:
        proc = subprocess.Popen(
            ["adb", "logcat", "-v", "time"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        for line in proc.stdout:
            print(line, end="")   # mirror to terminal
            lines.append(line)
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        print(red("[!] adb not found. Make sure Android SDK platform-tools is in PATH."))
        sys.exit(1)
    return lines


def read_stdin() -> list[str]:
    print(cyan("[*] Reading from stdin ...\n"))
    return sys.stdin.readlines()


def extract_crash_blocks(lines: list[str]) -> list[tuple[int, list[str]]]:
    """Return list of (start_line_no, block_lines) for each crash block found."""
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        for pat in CRASH_ANCHOR_PATTERNS:
            if re.search(pat, line, re.IGNORECASE):
                # Grab up to 60 lines as the crash block
                block = lines[i : i + 60]
                blocks.append((i + 1, block))
                break
        i += 1
    return blocks


def match_patterns(lines: list[str]) -> dict:
    """Scan all lines and collect hits per pattern."""
    hits = defaultdict(list)   # label -> [(lineno, line)]
    for lineno, line in enumerate(lines, 1):
        for label, pat, severity in PATTERNS:
            if re.search(pat, line, re.IGNORECASE):
                hits[label].append((lineno, severity, line.rstrip()))
    return hits


def guess_root_cause(hits: dict, crash_blocks: list) -> list[str]:
    """Heuristic: produce a prioritised list of likely root-cause messages."""
    causes = []

    # 1. Heap exhaustion → already diagnosed from previous session
    if "HEAP EXHAUSTED" in hits or "OOM" in hits:
        causes.append("🔴 HEAP EXHAUSTION — Dart VM ran out of memory. "
                       "Check for unbounded lists, missing RepaintBoundary, "
                       "or SingleChildScrollView inside render loops.")

    # 2. Null safety crash after login → very common pattern
    if "DART NULL" in hits:
        causes.append("🔴 NULL CHECK CRASH — A non-nullable field was null after login. "
                       "Likely: user model field, token, or navigation argument is null. "
                       "Check: Navigator.pushReplacement argument, user?.uid, token!.")

    # 3. Navigator/context after async gap
    if "CONTEXT UNMOUNTED" in hits or "DISPOSED WIDGET" in hits:
        causes.append("🔴 USE-AFTER-DISPOSE — BuildContext used after widget was unmounted. "
                       "Classic pattern: await loginApi(); if (!mounted) return; "
                       "Navigator.pushReplacement(context, ...);  ← missing mounted check.")

    # 4. Dialog not closed before navigation
    if "DIALOG LEAK" in hits or "LOADING DIALOG" in hits or "OVERLAY ERROR" in hits:
        causes.append("🟡 LOADING DIALOG LEAK — showDialog() overlay was not dismissed "
                       "before Navigator.push/pushReplacement. "
                       "Fix: Navigator.pop(context); BEFORE navigating away.")

    # 5. Auth token null
    if "TOKEN NULL" in hits or "AUTH ERROR" in hits:
        causes.append("🟡 AUTH DATA NULL — token/user object is null after login success. "
                       "Check your auth state listener and ensure you await it fully.")

    # 6. Provider / state crash
    if "PROVIDER ERROR" in hits or "GETX ERROR" in hits:
        causes.append("🟡 STATE MANAGEMENT ERROR — BLoC/Provider/GetX threw after login. "
                       "Ensure you are not reading a disposed controller.")

    # 7. General Dart exception
    if "DART UNHANDLED EXC" in hits or "DART FATAL" in hits:
        causes.append("🔴 UNHANDLED DART EXCEPTION — see crash blocks below for full trace.")

    if not causes:
        causes.append("⚪ No known pattern matched — check the raw crash blocks below.")

    return causes


def print_section(title: str):
    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'═'*60}{RESET}")


def severity_color(sev: str) -> str:
    if sev == "CRITICAL": return red(sev)
    if sev == "HIGH":     return yellow(sev)
    return cyan(sev)


# ─── REPORT ──────────────────────────────────────────────────────────────────

def print_report(hits: dict, crash_blocks: list, lines: list[str]):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{BOLD}Flutter Crash Analyzer — {timestamp}{RESET}")
    print(f"Total log lines scanned: {len(lines)}")

    # ── Summary of matched patterns ──────────────────────────────────────
    print_section("PATTERN MATCHES")
    if not hits:
        print(green("  ✓ No known error patterns found."))
    else:
        for label, entries in sorted(hits.items(),
                key=lambda kv: 0 if kv[1][0][1]=="CRITICAL"
                               else 1 if kv[1][0][1]=="HIGH" else 2):
            sev = entries[0][1]
            count = len(entries)
            print(f"  [{severity_color(sev)}] {bold(label):30s}  {count} hit(s)")
            # Show first 3 matching lines
            for lineno, _, line in entries[:3]:
                snippet = line[line.find("]")+1:].strip() if "]" in line else line.strip()
                snippet = snippet[:120]
                print(f"       L{lineno:>5}: {snippet}")
            if count > 3:
                print(f"       ... and {count-3} more")

    # ── Root cause guesses ───────────────────────────────────────────────
    print_section("LIKELY ROOT CAUSES  (most probable first)")
    causes = guess_root_cause(hits, crash_blocks)
    for i, cause in enumerate(causes, 1):
        print(f"\n  {i}. {cause}")

    # ── Crash blocks ─────────────────────────────────────────────────────
    print_section(f"CRASH BLOCKS  ({len(crash_blocks)} found)")
    if not crash_blocks:
        print(yellow("  No explicit crash anchor found. "
                     "The crash may be silent (heap OOM) — check PATTERN MATCHES above."))
    for idx, (start, block) in enumerate(crash_blocks, 1):
        print(f"\n  {red(f'── Crash #{idx} (starts at line {start})')} ──")
        for line in block:
            stripped = line.rstrip()
            if not stripped:
                continue
            # highlight dart stack frames
            if re.search(r"#\d+\s+.*\.dart:\d+", stripped):
                print(f"    {yellow(stripped)}")
            elif re.search(r"(Error|Exception|Fatal|FATAL)", stripped, re.I):
                print(f"    {red(stripped)}")
            else:
                print(f"    {stripped}")

    # ── Login-specific checklist ──────────────────────────────────────────
    print_section("LOGIN-CRASH CHECKLIST  (manual review)")
    checklist = [
        ("Mounted check after await",
         "if (!mounted) return;  ← add this after every await in login logic"),
        ("Loading dialog dismissed before navigate",
         "Navigator.pop(context);  ← call BEFORE Navigator.pushReplacement"),
        ("Null-safe user model",
         "final user = result.user!;  ← use ?. or add null guard"),
        ("Navigator context valid",
         "Do not store context across async gaps in StatelessWidget"),
        ("Token stored before navigation",
         "await storage.write(key:'token', value: token);  ← await storage FIRST"),
        ("No double-pop of dialog",
         "Ensure dialog is shown/hidden exactly once per login attempt"),
        ("Exception caught in login bloc/service",
         "Wrap login call in try/catch and emit error state instead of crashing"),
    ]
    for item, fix in checklist:
        print(f"\n  ☐  {bold(item)}")
        print(f"       {fix}")

    # ── Suggested adb commands ────────────────────────────────────────────
    print_section("NEXT STEPS")
    print("""
  1. Capture a fresh log right after the crash:
       adb logcat -d -v threadtime > fresh_crash.txt
       python analyze_flutter_crash.py fresh_crash.txt

  2. Filter only your app's errors:
       adb logcat --pid=$(adb shell pidof -s com.your.package) > app_only.txt

  3. Enable Flutter verbose logging in your login code:
       debugPrint('[LOGIN] step: calling API');
       debugPrint('[LOGIN] result: \${result}');

  4. Add a global Flutter error handler in main.dart:
       FlutterError.onError = (details) {
         debugPrint('FLUTTER ERROR: \${details.exceptionAsString()}');
         debugPrint(details.stack.toString());
       };

  5. Wrap login navigation in runZonedGuarded:
       runZonedGuarded(() => runApp(MyApp()), (e, st) {
         debugPrint('ZONE ERROR: \$e\\n\$st');
       });
""")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Analyze Flutter logcat output for post-login crash causes.")
    parser.add_argument("logfile", nargs="?", default=None,
                        help="Path to logcat file (default: crash_log.txt)")
    parser.add_argument("--live",  action="store_true",
                        help="Read live from adb logcat")
    parser.add_argument("--stdin", action="store_true",
                        help="Read from stdin (pipe mode)")
    args = parser.parse_args()

    # ── Decide input source ──────────────────────────────────────────────
    if args.live:
        lines = read_adb_live()
    elif args.stdin:
        lines = read_stdin()
    else:
        path = args.logfile or "crash_log.txt"
        if not os.path.exists(path):
            print(red(f"\n[!] Log file '{path}' not found.\n"))
            print("To capture a log run:\n"
                  "  adb logcat -d > crash_log.txt\n"
                  "Then re-run this script.")
            sys.exit(1)
        lines = read_log_file(path)

    # ── Analyse ──────────────────────────────────────────────────────────
    hits         = match_patterns(lines)
    crash_blocks = extract_crash_blocks(lines)
    print_report(hits, crash_blocks, lines)


if __name__ == "__main__":
    main()
