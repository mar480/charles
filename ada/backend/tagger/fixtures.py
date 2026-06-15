from __future__ import annotations

import json
from pathlib import Path

from lxml import html, etree

from .security import sanitize_html_document


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "fixtures" / "microentity"
UNTAGGED_FIXTURE_PATH = FIXTURE_DIR / "microentity-untagged.html"
TAGGED_FIXTURE_PATH = FIXTURE_DIR / "microentity-tagged-valid.xhtml"
MANIFEST_PATH = FIXTURE_DIR / "microentity-fixture-manifest.json"


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_untagged_html() -> str:
    return UNTAGGED_FIXTURE_PATH.read_text(encoding="utf-8")


def load_tagged_xhtml() -> str:
    return TAGGED_FIXTURE_PATH.read_text(encoding="utf-8")


def parse_untagged_tree():
    return html.fromstring(sanitize_html_document(load_untagged_html()))


def parse_tagged_tree():
    return etree.fromstring(load_tagged_xhtml().encode("utf-8"))


def iter_inline_facts(root):
    ns = {"ix": "http://www.xbrl.org/2013/inlineXBRL"}
    for fact in root.xpath("//ix:nonFraction | //ix:nonNumeric", namespaces=ns):
        yield fact
