#!/usr/bin/env python3
"""Static safety and structure checks for the offline H.U.M.A.N.S UI concept."""
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import tempfile

HTML = Path(__file__).resolve().parents[1] / "docs" / "ui-ux-prototype.html"
source = HTML.read_text(encoding="utf-8")

class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.external = []
        self.script = []
        self.in_script = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        for name in ("src", "href"):
            value = attrs.get(name, "")
            if value.startswith(("https://", "http://", "//")):
                self.external.append((tag, name, value))
        if tag == "script" and not attrs.get("src"):
            self.in_script = True
    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

parser = Structure()
parser.feed(source)
parser.close()
assert len(parser.ids) == len(set(parser.ids)), "duplicate HTML id"
assert not parser.external, f"prototype must be offline/self-contained: {parser.external}"
assert "prefers-reduced-motion:reduce" in source.replace(" ", ""), "missing system reduced-motion support"
assert "aria-live=\"polite\"" in source, "dynamic status needs a live region"
assert "4 digits" in source and "5 digits" in source, "both PIN length choices must be present"
assert "never type a real PIN" in source and "not authentication" in source, "demo warning missing"
assert "autocomplete=\"off\"" in source, "demo PIN input must opt out of autofill"
assert not re.search(r"\b(?:localStorage|sessionStorage|indexedDB|document\.cookie|fetch\s*\(|XMLHttpRequest|navigator\.credentials)\b", source), "prototype must not persist data or use network/auth APIs"
inline = re.findall(r"<script>(.*?)</script>", source, re.S)
assert len(inline) == 1, "expected one inline application script"
with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as script:
    script.write(inline[0])
    script.flush()
    subprocess.run(["node", "--check", script.name], check=True)
print("UI prototype static checks passed: unique IDs, offline, reduced motion, accessible status, 4/5 choices, no persistence/network, JavaScript syntax.")
