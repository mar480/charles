from __future__ import annotations

import json
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lxml import html


VALIDATOR_BASE_URL = "https://test-validator.companieshouse.gov.uk/xbrl_validate"


class CompaniesHouseValidationError(Exception):
    pass


def _multipart_body(filename: str, content: str, content_type: str = "application/xhtml+xml") -> tuple[bytes, str]:
    boundary = f"----charles-tagger-{uuid.uuid4().hex}"
    lines = [
        f"--{boundary}",
        f'Content-Disposition: form-data; name="file"; filename="{filename}"',
        f"Content-Type: {content_type}",
        "",
        content,
        f"--{boundary}--",
        "",
    ]
    body = "\r\n".join(lines).encode("utf-8")
    return body, boundary


def _json_request(url: str, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None) -> dict:
    request = Request(url, data=body, headers=headers or {}, method=method)
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def submit_ixbrl(filename: str, content: str) -> str:
    body, boundary = _multipart_body(filename, content)
    try:
        payload = _json_request(
            f"{VALIDATOR_BASE_URL}/submit-accounts",
            method="POST",
            body=body,
            headers={
                "Accept": "application/json",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
    except HTTPError as exc:
        raise CompaniesHouseValidationError(f"Companies House validator upload failed: {exc.code}") from exc
    except URLError as exc:
        raise CompaniesHouseValidationError(f"Companies House validator upload failed: {exc.reason}") from exc
    file_id = payload.get("fileId")
    if not file_id:
        raise CompaniesHouseValidationError("Companies House validator did not return a fileId.")
    return str(file_id)


def wait_for_completion(file_id: str, timeout_seconds: int = 180, poll_interval_seconds: int = 2) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            payload = _json_request(f"{VALIDATOR_BASE_URL}/progress/{file_id}")
        except HTTPError as exc:
            raise CompaniesHouseValidationError(f"Companies House validator progress check failed: {exc.code}") from exc
        except URLError as exc:
            raise CompaniesHouseValidationError(f"Companies House validator progress check failed: {exc.reason}") from exc
        if payload.get("progress") == 100:
            return
        time.sleep(poll_interval_seconds)
    raise CompaniesHouseValidationError("Companies House validator did not complete before the timeout.")


def fetch_result(file_id: str) -> dict:
    url = f"{VALIDATOR_BASE_URL}/result/{file_id}"
    try:
        request = Request(url, headers={"Accept": "text/html"})
        with urlopen(request, timeout=120) as response:
            content = response.read().decode("utf-8")
    except HTTPError as exc:
        raise CompaniesHouseValidationError(f"Companies House validator result fetch failed: {exc.code}") from exc
    except URLError as exc:
        raise CompaniesHouseValidationError(f"Companies House validator result fetch failed: {exc.reason}") from exc

    root = html.fromstring(content)
    banner = root.xpath("//*[contains(concat(' ', normalize-space(@class), ' '), ' govuk-notification-banner ')]")
    banner_text = ""
    banner_heading = ""
    if banner:
        banner_heading = " ".join(banner[0].xpath(".//*[self::h2 or self::h3]/text()")).strip()
        banner_text = " ".join(part.strip() for part in banner[0].itertext() if part.strip())
    page_heading = " ".join(root.xpath("//h1/text()")).strip()
    status = "pass" if "valid" in banner_text.lower() and "not valid" not in banner_text.lower() else "fail"
    return {
        "status": status,
        "fileId": file_id,
        "resultUrl": url,
        "heading": banner_heading or page_heading,
        "message": banner_text or page_heading or "Companies House validator completed.",
    }


def validate_ixbrl(filename: str, content: str) -> dict:
    file_id = submit_ixbrl(filename, content)
    wait_for_completion(file_id)
    return fetch_result(file_id)
