"""Markdown source fetching with GitHub URL normalization."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

_GITHUB_BLOB_HOST = "github.com"
_GITHUB_RAW_HOST = "raw.githubusercontent.com"
_USER_AGENT = "tooploox-quiz-agent/0.1"
_FETCH_TIMEOUT_SECS = 30


@dataclass(frozen=True)
class MarkdownSource:
    original_url: str
    url: str
    text: str
    sha256: str


def normalize_url(url: str) -> str:
    """Convert a GitHub ``/blob/`` URL to its raw-content equivalent. Pass-through otherwise."""
    parsed = urlparse(url)
    if parsed.netloc != _GITHUB_BLOB_HOST:
        return url
    parts = parsed.path.strip("/").split("/", 3)
    if len(parts) < 4 or parts[2] != "blob":
        return url
    owner, repo, _blob, rest = parts
    return f"https://{_GITHUB_RAW_HOST}/{owner}/{repo}/{rest}"


def fetch_markdown(url: str) -> MarkdownSource:
    resolved = normalize_url(url)
    req = Request(resolved, headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(req, timeout=_FETCH_TIMEOUT_SECS) as resp:
            body = resp.read()
    except HTTPError as e:
        raise RuntimeError(f"Failed to fetch {resolved} (HTTP {e.code} {e.reason})") from e
    except URLError as e:
        raise RuntimeError(f"Failed to fetch {resolved}: {e.reason}") from e
    return MarkdownSource(
        original_url=url,
        url=resolved,
        text=body.decode("utf-8"),
        sha256=hashlib.sha256(body).hexdigest(),
    )
