from __future__ import annotations

import os
from typing import Iterable

from flask import Request
from lxml import html


MAX_IMPORT_BYTES = 2 * 1024 * 1024
MAX_JSON_BODY_BYTES = 4 * 1024 * 1024
FORBIDDEN_HTML_TAGS = {"script", "iframe", "object", "embed", "form"}
SAFE_URL_ATTRS = {"href", "src"}


def _drop_dangerous_attrs(node) -> None:
    for attr_name in list(node.attrib):
        lowered = attr_name.lower()
        attr_value = str(node.attrib.get(attr_name, ""))
        if lowered.startswith("on"):
            node.attrib.pop(attr_name, None)
            continue
        if lowered in SAFE_URL_ATTRS and attr_value.strip().lower().startswith("javascript:"):
            node.attrib.pop(attr_name, None)


def sanitize_html_document(content: str) -> str:
    root = html.fromstring(content)
    for node in list(root.iter()):
        tag = getattr(node, "tag", "")
        if not isinstance(tag, str):
            continue
        if tag.lower() in FORBIDDEN_HTML_TAGS:
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
            continue
        _drop_dangerous_attrs(node)
    return html.tostring(root, encoding="unicode")


def validate_content_length(request: Request, limit_bytes: int) -> bool:
    content_length = request.content_length
    return content_length is None or content_length <= limit_bytes


def _header_value(request: Request, names: Iterable[str]) -> str:
    for name in names:
        value = request.headers.get(name, "")
        if value:
            return value
    return ""


def check_access(request: Request) -> tuple[bool, str | None]:
    token = os.environ.get("TAGGER_ACCESS_TOKEN", "").strip()
    if token:
        bearer = request.headers.get("Authorization", "")
        provided = ""
        if bearer.lower().startswith("bearer "):
            provided = bearer[7:].strip()
        if not provided:
            provided = _header_value(request, ["X-Tagger-Token", "X-Access-Token"]).strip()
        if provided != token:
            return False, "Tagger API access token is required."

    allowed_user = os.environ.get("TAGGER_ALLOWED_USER", "").strip()
    if allowed_user:
        forwarded_user = _header_value(request, ["X-Forwarded-User", "X-Remote-User"]).strip()
        if forwarded_user != allowed_user:
            return False, "Tagger API user is not authorised."

    return True, None
