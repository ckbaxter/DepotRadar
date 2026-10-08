#!/usr/bin/env python3
"""Überträgt die Versionen aus frontend/changelog.json nach app.py und README.md.

frontend/changelog.json ist die einzige Stelle, an der Versionen von Hand geändert werden
(Schlüssel frontend_version und backend_version plus ein Eintrag in "entries").

  python3 scripts/sync-version.py
      schreibt VERSION in backend/app.py und die Versions-Badges in README.md

  python3 scripts/sync-version.py --check
      ändert nichts, Exit-Code 1 bei Abweichung (so läuft es in GitHub Actions)

  python3 scripts/sync-version.py --check --tag backend-v2.8.50
      prüft zusätzlich, ob der Release-Tag zu backend_version passt

Geprüft wird außerdem, dass der jüngste Changelog-Eintrag, der "Backend v…" bzw. "Frontend v…"
nennt, zur jeweiligen Version oben in der Datei passt. Das lässt sich nicht automatisch
korrigieren: dann Eintrag ergänzen oder Version anpassen.

Exit-Codes: 0 = alles synchron, 1 = Abweichung, 2 = Datei oder Muster unbrauchbar.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "frontend" / "changelog.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

# (Datei, Muster mit drei Gruppen: davor / Version / danach, Schlüssel in changelog.json)
TARGETS = [
    (ROOT / "backend" / "app.py", r'^(VERSION\s*=\s*")([^"]+)(")', "backend_version"),
    (ROOT / "README.md", r"(badge/Backend-v)([^-]+)(-)", "backend_version"),
    (ROOT / "README.md", r"(badge/Frontend-v)([^-]+)(-)", "frontend_version"),
]

# So steht die Version im Freitext "versions" der Changelog-Einträge,
# z. B. "Frontend v2.13.83 · Backend v2.8.49"
ENTRY_PATTERNS = {
    "backend_version": ("Backend", re.compile(r"Backend v(\d+\.\d+\.\d+)")),
    "frontend_version": ("Frontend", re.compile(r"Frontend v(\d+\.\d+\.\d+)")),
}


def fail(msg):
    print(f"Fehler: {msg}", file=sys.stderr)
    sys.exit(2)


def read(path):
    return path.read_bytes().decode("utf-8")


def newest_entry_version(entries, pattern):
    """Version aus dem jüngsten Eintrag (Einträge stehen neueste zuerst), der sie nennt."""
    for entry in entries:
        m = pattern.search(str(entry.get("versions", "")))
        if m:
            return m.group(1)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="nur prüfen, nichts schreiben")
    ap.add_argument("--tag", help="Release-Tag, der zu backend_version passen muss (z. B. backend-v2.8.50)")
    args = ap.parse_args()

    try:
        data = json.loads(read(CHANGELOG))
    except (OSError, ValueError) as e:
        fail(f"{CHANGELOG.relative_to(ROOT)} nicht lesbar: {e}")

    versions = {}
    for key in ENTRY_PATTERNS:
        v = data.get(key)
        if not isinstance(v, str) or not SEMVER.match(v):
            fail(f"{key} fehlt oder ist keine Version (x.y.z) in {CHANGELOG.name}")
        versions[key] = v

    entries = data.get("entries")
    if not isinstance(entries, list):
        fail(f"\"entries\" fehlt oder ist keine Liste in {CHANGELOG.name}")

    fixes, errors, texts = [], [], {}

    # 1) VERSION in app.py und README-Badges: automatisch korrigierbar
    for path, pattern, key in TARGETS:
        text = texts.get(path) or read(path)
        found = re.findall(pattern, text, flags=re.M)
        if len(found) != 1:
            fail(f"Muster für {key} in {path.name} {len(found)}x gefunden (erwartet: genau 1x)")
        if found[0][1] != versions[key]:
            fixes.append(f"{path.name}: v{found[0][1]} statt v{versions[key]} ({key})")
        texts[path] = re.sub(pattern, lambda m: m.group(1) + versions[key] + m.group(3), text, flags=re.M)

    # 2) Jüngster Changelog-Eintrag je Teil: nur von Hand korrigierbar
    for key, (name, pattern) in ENTRY_PATTERNS.items():
        newest = newest_entry_version(entries, pattern)
        if newest is None:
            errors.append(f"{CHANGELOG.name}: kein Eintrag nennt \"{name} v…\"")
        elif newest != versions[key]:
            errors.append(
                f"{CHANGELOG.name}: jüngster {name}-Eintrag nennt v{newest}, oben steht v{versions[key]} "
                f"(Eintrag ergänzen oder {key} korrigieren)"
            )

    # 3) Release-Tag: nur von Hand korrigierbar
    if args.tag and args.tag != f"backend-v{versions['backend_version']}":
        errors.append(f"Tag {args.tag} passt nicht zu backend_version v{versions['backend_version']}")

    if args.check:
        if fixes or errors:
            print("Versionen sind nicht synchron mit changelog.json:", file=sys.stderr)
            for line in fixes + errors:
                print(f"  - {line}", file=sys.stderr)
            if fixes:
                print("Lösung: python3 scripts/sync-version.py ausführen und die Änderung committen.", file=sys.stderr)
            sys.exit(1)
        print(f"OK: Backend v{versions['backend_version']} · Frontend v{versions['frontend_version']}")
        return

    for path, text in texts.items():
        path.write_bytes(text.encode("utf-8"))
    if fixes:
        print("Aktualisiert:")
        for line in fixes:
            print(f"  - {line}")
    else:
        print("Nichts zu tun, alles synchron.")
    if errors:
        print("Achtung, von Hand zu korrigieren:", file=sys.stderr)
        for line in errors:
            print(f"  - {line}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
