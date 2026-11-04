"""Extract fixed rendered exercise statements without solutions; stdlib only."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Extractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.rows = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        skip = bool(self.stack and self.stack[-1][1]) or bool(classes & {
            "solutions", "solution", "hint", "answer", "autopermalink", "problem-buttons", "heading"
        })
        if tag == "article" and "exercise" in classes:
            self.current = {"source_id": attrs["id"], "text_parts": []}
        if self.current and tag in {"div", "p", "li"} and not skip:
            self.current["text_parts"].append("\n")
        if self.current and tag == "input" and not skip:
            self.current["text_parts"].append("[blank]")
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, skip))

    def handle_endtag(self, tag):
        if tag == "article" and self.current:
            text = "\n".join(" ".join(line.split()) for line in "".join(self.current.pop("text_parts")).splitlines() if line.strip())
            self.rows.append({**self.current, "original_wording": text})
            self.current = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.current and not (self.stack and self.stack[-1][1]):
            self.current["text_parts"].append(data)


def extract():
    parser = Extractor()
    parser.feed((ROOT / "sources/binom_excerpt.html").read_text())
    assert len(parser.rows) == 13
    assert len({row["source_id"] for row in parser.rows}) == 13
    assert all("Solution" not in row["original_wording"] for row in parser.rows)
    return parser.rows


if __name__ == "__main__":
    print(json.dumps(extract(), indent=2, ensure_ascii=False))
