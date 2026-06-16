from __future__ import annotations

import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


COMPANIES_HOUSE_ENDPOINT = "https://api.company-information.service.gov.uk/company/{company_number}"
COMPANIES_HOUSE_OFFICERS_ENDPOINT = "https://api.company-information.service.gov.uk/company/{company_number}/officers"


class CompaniesHouseLookupError(Exception):
    pass


def _normalise_api_key(raw_api_key: str | None) -> str:
    api_key = (raw_api_key or "").strip()
    if len(api_key) >= 2 and api_key[0] == api_key[-1] and api_key[0] in {"'", '"'}:
        api_key = api_key[1:-1].strip()
    if not api_key:
        raise CompaniesHouseLookupError("COMPANIES_HOUSE_API_KEY is not configured")
    if api_key.lower().startswith("basic "):
        raise CompaniesHouseLookupError(
            "COMPANIES_HOUSE_API_KEY must be the raw API key only, not a full Authorization header."
        )
    return api_key


def lookup_company_profile(company_number: str) -> dict:
    api_key = _normalise_api_key(os.environ.get("COMPANIES_HOUSE_API_KEY"))

    company_number = (company_number or "").strip()
    if not company_number:
        raise CompaniesHouseLookupError("Company number is required")

    credentials = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json",
    }

    try:
        request = Request(
            COMPANIES_HOUSE_ENDPOINT.format(company_number=company_number),
            headers=headers,
        )
        with urlopen(request, timeout=15) as response:
            profile = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise CompaniesHouseLookupError(f"Companies House lookup failed: {exc.code} {body}") from exc
    except URLError as exc:
        raise CompaniesHouseLookupError(f"Companies House lookup failed: {exc.reason}") from exc

    try:
        officers_request = Request(
            COMPANIES_HOUSE_OFFICERS_ENDPOINT.format(company_number=company_number),
            headers=headers,
        )
        with urlopen(officers_request, timeout=15) as response:
            officers_payload = json.loads(response.read().decode("utf-8"))
        director_names = [
            str(item.get("name", "")).strip()
            for item in officers_payload.get("items", [])
            if str(item.get("officer_role", "")).strip().lower() == "director"
            and not item.get("resigned_on")
            and str(item.get("name", "")).strip()
        ]
        if director_names:
            profile["director_names"] = director_names
    except Exception:
        # Company profile lookup is still useful even if officers enrichment is unavailable.
        pass

    return profile
