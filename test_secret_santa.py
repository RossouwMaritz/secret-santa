"""Run with: python3 test_secret_santa.py"""
import collections
import tempfile
from pathlib import Path

import base64
import json
import urllib.parse

from secret_santa import draw, load_people, reveal_url, whatsapp_link

# Reveal link round-trips names (incl. accents/emoji) the way the page decodes them, and hides them.
url = reveal_url("https://x.github.io/ss/", "Zoë", "Ben 🎄")
token = url.split("#", 1)[1]
assert "Ben" not in url
assert json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))) == {"g": "Zoë", "r": "Ben 🎄"}
wa = whatsapp_link("27821234567", "Zoë", url)
assert wa.startswith("https://wa.me/27821234567?text=") and url in urllib.parse.unquote(wa)

# Nobody gets themselves, everyone gives once and receives once.
for n in range(2, 12):
    names = [f"p{i}" for i in range(n)]
    for _ in range(200):
        pairs = draw(names)
        assert all(g != r for g, r in pairs.items())
        assert sorted(pairs) == sorted(pairs.values()) == sorted(names)

# Draws vary: with 4 people there are 9 valid draws, all should show up.
seen = collections.Counter(tuple(sorted(draw(list("abcd")).items())) for _ in range(5000))
assert len(seen) == 9, len(seen)

# CSV parsing: header skipped, phone cleaned to digits.
with tempfile.TemporaryDirectory() as d:
    f = Path(d) / "p.csv"
    f.write_text("name,phone\nAnna, +27 82 123 4567\nBen,+27-83-123-4567\n")
    assert load_people(f) == {"Anna": "27821234567", "Ben": "27831234567"}

    # Local numbers without country code are rejected.
    f.write_text("Anna,0821234567\nBen,+27831234567\n")
    try:
        load_people(f)
        raise AssertionError("expected rejection")
    except SystemExit:
        pass

print("all checks passed")
