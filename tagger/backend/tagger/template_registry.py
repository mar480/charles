from __future__ import annotations

from copy import deepcopy

from .fixtures import load_manifest


def list_templates() -> list[dict]:
    manifest = load_manifest()
    return [
        {
            "templateId": manifest["templateId"],
            "label": manifest["label"],
            "version": manifest["version"],
            "defaultFilingProfile": manifest["defaultFilingProfile"],
            "supportedTaxonomyYears": [manifest["taxonomyYear"]],
            "recommendedEntrypoint": manifest["taxonomyEntrypoint"],
        }
    ]


def get_template(template_id: str) -> dict | None:
    manifest = load_manifest()
    if manifest["templateId"] != template_id:
        return None
    return deepcopy(manifest)

