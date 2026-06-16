from __future__ import annotations

from .fixtures import load_manifest
from .ixbrl_generator import prepare_editable_template_html


def build_template_payload(project: dict) -> dict:
    manifest = load_manifest()
    return {
        **manifest,
        "editableHtml": prepare_editable_template_html(project),
    }

