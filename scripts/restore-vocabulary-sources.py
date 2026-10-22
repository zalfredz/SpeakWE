"""Restore missing source files from the pinned source lock; verify SHA-256.

Existing files are verified, never silently replaced. No dictionary scraping.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data/vocabulary/sources"


def restore(item):
    target = SOURCES / item["file"]
    if target.parent.resolve() != SOURCES.resolve():
        raise ValueError("Source path escapes source directory")
    if target.exists():
        content = target.read_bytes()
    else:
        if not item["url"].startswith(("https://raw.githubusercontent.com/", "https://svn.code.sf.net/p/wn-msa/tab/")):
            raise ValueError("Unexpected source host")
        request = urllib.request.Request(item["url"], headers={"User-Agent": "SpeakWE-vocabulary-builder/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
    if hashlib.sha256(content).hexdigest() != item["sha256"]:
        raise ValueError("Source checksum mismatch: " + item["file"])
    if not target.exists():
        target.write_bytes(content)
    return item["file"]


if __name__ == "__main__":
    lock = json.loads((SOURCES / "sources.lock.json").read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=4) as executor:
        for filename in executor.map(restore, lock["sources"]):
            print("Verified " + filename)
