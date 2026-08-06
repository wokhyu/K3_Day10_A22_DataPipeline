from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


CROSSREF_API_URL = "https://api.crossref.org/works"
_REQUEST_TIMEOUT = (5.0, 30.0)
_MAX_REQUEST_ATTEMPTS = 4
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", flags=re.IGNORECASE)


class _MarkupTextExtractor(HTMLParser):
    """Collect text from the JATS/HTML fragments used in Crossref abstracts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _plain_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return normalize_whitespace(unescape(value))


def _markup_to_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    parser = _MarkupTextExtractor()
    try:
        parser.feed(unescape(value))
        parser.close()
    except Exception:
        # Crossref metadata can contain incomplete publisher-supplied markup.
        # Falling back to a conservative tag removal keeps one bad fragment
        # from invalidating the entire API response.
        return normalize_whitespace(re.sub(r"<[^>]*>", " ", unescape(value)))
    return normalize_whitespace(" ".join(parser.parts))


def _first_text(value: Any, *, allow_markup: bool = False) -> str:
    cleaner = _markup_to_text if allow_markup else _plain_text
    if isinstance(value, list):
        for item in value:
            cleaned = cleaner(item)
            if cleaned:
                return cleaned
        return ""
    return cleaner(value)


def _unique_texts(value: Any, *, allow_markup: bool = False) -> list[str]:
    if not isinstance(value, list):
        return []

    cleaner = _markup_to_text if allow_markup else _plain_text
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        cleaned = cleaner(item)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def _normalize_doi(value: Any) -> str:
    doi = _plain_text(value)
    lowered = doi.casefold()
    for prefix in ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/", "doi:"):
        if lowered.startswith(prefix):
            doi = doi[len(prefix) :].strip()
            break
    if not _DOI_PATTERN.fullmatch(doi):
        return ""
    return doi.lower()


def _extract_authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    names: list[str] = []
    seen: set[str] = set()
    for author in value:
        if isinstance(author, str):
            name = _plain_text(author)
        elif isinstance(author, dict):
            given = _plain_text(author.get("given"))
            family = _plain_text(author.get("family"))
            name = normalize_whitespace(f"{given} {family}")
            if not name:
                name = _plain_text(author.get("name")) or _plain_text(author.get("literal"))
        else:
            continue

        key = name.casefold()
        if name and key not in seen:
            names.append(name)
            seen.add(key)
    return names


def _date_from_parts(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    raw_parts = value.get("date-parts")
    if not isinstance(raw_parts, list) or not raw_parts or not isinstance(raw_parts[0], list):
        return ""

    parts = raw_parts[0]
    if not parts or len(parts) > 3:
        return ""
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) >= 2 else 1
        day = int(parts[2]) if len(parts) >= 3 else 1
        return date(year, month, day).isoformat()
    except (TypeError, ValueError, OverflowError):
        return ""


def _extract_date(item: dict[str, Any], candidates: tuple[str, ...]) -> str:
    for key in candidates:
        value = item.get(key)
        if not isinstance(value, dict):
            continue
        date_time = _plain_text(value.get("date-time"))
        if date_time:
            return date_time
        date_parts = _date_from_parts(value)
        if date_parts:
            return date_parts
    return ""


def _extract_pdf_url(value: Any) -> str:
    if not isinstance(value, list):
        return ""

    fallback = ""
    for link in value:
        if not isinstance(link, dict):
            continue
        url = _plain_text(link.get("URL"))
        if not url:
            continue
        content_type = _plain_text(link.get("content-type")).lower()
        if "pdf" in content_type:
            return url
        if not fallback and url.split("?", maxsplit=1)[0].lower().endswith(".pdf"):
            fallback = url
    return fallback


def _extract_landing_url(item: dict[str, Any], paper_id: str) -> str:
    direct_url = _plain_text(item.get("URL"))
    if direct_url:
        return direct_url

    resource = item.get("resource")
    if isinstance(resource, dict):
        primary = resource.get("primary")
        if isinstance(primary, dict):
            resource_url = _plain_text(primary.get("URL"))
            if resource_url:
                return resource_url
    return f"https://doi.org/{paper_id}"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref ``/works`` response into a consistent raw schema.

    A usable record must have a DOI, title and non-empty abstract. Optional
    publisher metadata is represented by empty strings/lists rather than by
    values invented by the ingestion layer.
    """
    if not isinstance(payload, dict):
        raise ValueError("Crossref payload must be a JSON object.")
    message = payload.get("message")
    if not isinstance(message, dict):
        raise ValueError("Crossref payload is missing the 'message' object.")
    items = message.get("items")
    if not isinstance(items, list):
        raise ValueError("Crossref payload 'message.items' must be a list.")

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        paper_id = _normalize_doi(item.get("DOI"))
        title = _first_text(item.get("title"), allow_markup=True)
        summary = _markup_to_text(item.get("abstract"))
        if not paper_id or not title or not summary:
            continue

        categories = _unique_texts(item.get("subject"), allow_markup=True)
        published = _extract_date(
            item,
            ("published", "published-online", "published-print", "issued", "created"),
        )
        updated = _extract_date(item, ("indexed", "deposited", "created", "published"))
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=_extract_authors(item.get("author")),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=_extract_landing_url(item, paper_id),
                pdf_url=_extract_pdf_url(item.get("link")),
                comment="",
            )
        )
    return records


def _retry_delay(response: requests.Response | None, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 30.0)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                seconds = (retry_at - datetime.now(UTC)).total_seconds()
                return min(max(seconds, 0.0), 30.0)
            except (TypeError, ValueError, OverflowError):
                pass
    return min(2.0**attempt, 8.0)


def _request_crossref(params: dict[str, Any]) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "day10-data-observability-lab/0.1 (educational Crossref ingestion)",
    }
    last_error: requests.RequestException | None = None

    for attempt in range(_MAX_REQUEST_ATTEMPTS):
        response: requests.Response | None = None
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers=headers,
                timeout=_REQUEST_TIMEOUT,
            )
            if response.status_code not in _RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise RuntimeError("Crossref returned an invalid JSON response.") from exc
                if not isinstance(payload, dict):
                    raise RuntimeError("Crossref returned JSON with an unexpected top-level type.")
                return payload

            if attempt == _MAX_REQUEST_ATTEMPTS - 1:
                response.raise_for_status()
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
            if attempt == _MAX_REQUEST_ATTEMPTS - 1:
                break

        delay = _retry_delay(response, attempt)
        if response is not None:
            response.close()
        time.sleep(delay)

    raise RuntimeError(
        f"Crossref request failed after {_MAX_REQUEST_ATTEMPTS} attempts."
    ) from last_error


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref works and persist both source and parsed raw artifacts."""
    if not 1 <= settings.max_results <= 1000:
        raise ValueError("settings.max_results must be between 1 and 1000.")

    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    payload = _request_crossref(params)

    # Preserve source lineage even if a publisher-supplied item later fails
    # parsing. This snapshot must therefore be written before parsing.
    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load and validate a parsed Crossref raw-record snapshot."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError("Raw records snapshot must contain a JSON list.")

    field_names = tuple(field.name for field in fields(PaperRecord))
    list_fields = {"authors", "categories"}
    records: list[PaperRecord] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Raw record at index {index} must be a JSON object.")

        missing = [name for name in field_names if name not in item]
        if missing:
            raise ValueError(
                f"Raw record at index {index} is missing fields: {', '.join(missing)}."
            )

        for name in field_names:
            value = item[name]
            if name in list_fields:
                if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
                    raise ValueError(
                        f"Raw record at index {index} field '{name}' must be a list of strings."
                    )
            elif not isinstance(value, str):
                raise ValueError(
                    f"Raw record at index {index} field '{name}' must be a string."
                )

        record_data = {name: item[name] for name in field_names}
        records.append(PaperRecord(**record_data))
    return records
