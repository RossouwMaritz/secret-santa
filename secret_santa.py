#!/usr/bin/env python3
"""Secret Santa draw that gives each person a private reveal link to send on WhatsApp.

Usage:
  python3 secret_santa.py people.csv https://you.github.io/secret-santa/
  python3 secret_santa.py people.csv https://you.github.io/secret-santa/ --only Ben

Prints one WhatsApp link per person. Click it, WhatsApp opens the chat with the message
typed, press Send. The message holds a link to the reveal page, not the name.

The draw is never printed. It is saved to <csv name>.pairs.json so a link can be
reprinted without redrawing. Don't open that file.
"""
import argparse
import base64
import csv
import json
import re
import secrets
import sys
import urllib.parse
from pathlib import Path


def load_people(path):
    """Read a name,phone CSV into {name: digits-only phone with country code}."""
    people, phones = {}, set()
    with open(path, newline="", encoding="utf-8") as f:
        for line_no, row in enumerate(csv.reader(f), 1):
            if not row or not row[0].strip() or row[0].startswith("#"):
                continue
            if line_no == 1 and row[0].strip().lower() == "name":
                continue
            if len(row) < 2:
                sys.exit(f"Line {line_no}: expected 'name,phone', got {row}")
            name, phone = row[0].strip(), re.sub(r"\D", "", row[1])
            if not 8 <= len(phone) <= 15 or phone.startswith("0"):
                sys.exit(f"Line {line_no}: '{row[1]}' for {name} needs the country code, e.g. +27821234567")
            if name in people:
                sys.exit(f"Line {line_no}: {name} is listed twice")
            if phone in phones:
                sys.exit(f"Line {line_no}: {name}'s number is already used by someone else")
            people[name] = phone
            phones.add(phone)
    if len(people) < 2:
        sys.exit("Need at least 2 people")
    return people


def draw(names):
    """Return {giver: receiver} where nobody gets themselves. Every valid draw is equally likely."""
    receivers = list(names)
    rng = secrets.SystemRandom()
    while True:
        rng.shuffle(receivers)
        if all(g != r for g, r in zip(names, receivers)):
            return dict(zip(names, receivers))


def load_or_draw(people, pairs_path):
    if pairs_path.exists():
        try:
            pairs = json.loads(pairs_path.read_text())
        except ValueError:
            sys.exit(f"The saved draw in {pairs_path} is empty or damaged. Delete it to redraw "
                     "(links already sent from the old draw will no longer match).")
        if set(pairs) != set(people):
            sys.exit(f"The people list changed since the draw. Delete {pairs_path} to redraw.")
        print(f"Using the saved draw in {pairs_path}\n")
        return pairs
    pairs = draw(list(people))
    pairs_path.write_text(json.dumps(pairs))
    pairs_path.chmod(0o600)
    print(f"Drew names and saved them (unseen) to {pairs_path}\n")
    return pairs


def reveal_url(base_url, giver, receiver):
    # shortcut: base64 hides names from a glance, not from someone who decodes it on purpose; fine among friends.
    # The part after # never leaves the phone, so the web host never sees it.
    token = json.dumps({"g": giver, "r": receiver}, ensure_ascii=False).encode()
    return base_url.rstrip("/") + "/#" + base64.urlsafe_b64encode(token).decode().rstrip("=")


def whatsapp_link(phone, giver, url):
    # No emoji: WhatsApp Desktop turns emoji in wa.me prefilled text into "�".
    text = f"Hi {giver}! Here's your Secret Santa link. Open it when nobody's looking over your shoulder:\n{url}"
    return f"https://wa.me/{phone}?text={urllib.parse.quote(text)}"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", type=Path, help="CSV with name,phone per line")
    p.add_argument("base_url", help="where the reveal page (index.html) is hosted")
    p.add_argument("--only", action="append", metavar="NAME", help="only print links for these people (repeatable)")
    args = p.parse_args()
    if not args.base_url.startswith("https://"):
        sys.exit("The page URL should start with https://")

    people = load_people(args.csv)
    unknown = set(args.only or []) - set(people)
    if unknown:
        sys.exit(f"Not in the list: {', '.join(sorted(unknown))}")

    pairs = load_or_draw(people, args.csv.with_suffix(".pairs.json"))
    for giver in args.only or people:
        print(f"{giver}:\n  {whatsapp_link(people[giver], giver, reveal_url(args.base_url, giver, pairs[giver]))}\n")


if __name__ == "__main__":
    main()
