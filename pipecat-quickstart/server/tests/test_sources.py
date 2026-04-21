"""Tests for quiz/sources.py — Markdown fetching + GitHub URL normalization."""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from quiz.sources import MarkdownSource, fetch_markdown, normalize_url


class TestNormalizeUrl:
    def test_converts_github_blob_url_to_raw(self):
        assert (
            normalize_url("https://github.com/pipecat-ai/pipecat/blob/main/README.md")
            == "https://raw.githubusercontent.com/pipecat-ai/pipecat/main/README.md"
        )

    def test_preserves_branch_and_deep_path(self):
        assert (
            normalize_url("https://github.com/org/repo/blob/dev/docs/guide.md")
            == "https://raw.githubusercontent.com/org/repo/dev/docs/guide.md"
        )

    def test_passes_through_raw_github_url(self):
        raw = "https://raw.githubusercontent.com/org/repo/main/README.md"
        assert normalize_url(raw) == raw

    def test_passes_through_non_github_url(self):
        assert normalize_url("https://example.com/doc.md") == "https://example.com/doc.md"

    def test_passes_through_github_non_blob_url(self):
        # GitHub URLs that aren't /blob/ (e.g. /tree/, repo root) stay unchanged.
        url = "https://github.com/org/repo"
        assert normalize_url(url) == url


def _mock_urlopen_returning(body: bytes) -> MagicMock:
    """Build a MagicMock that mimics urlopen's context-manager response."""
    response = MagicMock()
    response.read.return_value = body
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


class TestFetchMarkdown:
    def test_returns_source_with_text_and_sha256(self):
        body = b"# Hello\n\nsome markdown."
        response = _mock_urlopen_returning(body)

        with patch("quiz.sources.urlopen", return_value=response):
            result = fetch_markdown("https://example.com/doc.md")

        assert isinstance(result, MarkdownSource)
        assert result.original_url == "https://example.com/doc.md"
        assert result.url == "https://example.com/doc.md"
        assert result.text == body.decode("utf-8")
        assert result.sha256 == hashlib.sha256(body).hexdigest()

    def test_normalizes_github_blob_url_before_fetching(self):
        response = _mock_urlopen_returning(b"content")

        with patch("quiz.sources.urlopen", return_value=response) as mock_urlopen:
            result = fetch_markdown("https://github.com/org/repo/blob/main/README.md")

        assert result.original_url == "https://github.com/org/repo/blob/main/README.md"
        assert result.url == "https://raw.githubusercontent.com/org/repo/main/README.md"
        req = mock_urlopen.call_args.args[0]
        hit_url = req.full_url if hasattr(req, "full_url") else req
        assert hit_url == "https://raw.githubusercontent.com/org/repo/main/README.md"

    def test_raises_runtime_error_on_http_404(self):
        err = HTTPError(url="x", code=404, msg="Not Found", hdrs=None, fp=None)  # type: ignore[arg-type]
        with patch("quiz.sources.urlopen", side_effect=err):
            with pytest.raises(RuntimeError, match="404"):
                fetch_markdown("https://example.com/missing.md")

    def test_raises_runtime_error_on_network_failure(self):
        with patch("quiz.sources.urlopen", side_effect=URLError("connection refused")):
            with pytest.raises(RuntimeError, match="connection refused"):
                fetch_markdown("https://example.com/doc.md")
