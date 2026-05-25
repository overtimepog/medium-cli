"""HTTP client for Medium.com — RSS feeds and article content."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Tuple

import httpx
from medium_cli.models import Article, User

MEDIUM_BASE = "https://medium.com"


class MediumClient:
    """HTTP client for Medium.com."""

    def __init__(self, base_url: str = MEDIUM_BASE) -> None:
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=15.0,
            headers={"User-Agent": "medium-cli/0.1.0"},
            follow_redirects=True,
        )

    def search_tag(self, tag: str) -> list[Article]:
        """Search for articles by tag via RSS feed.

        Returns articles from the tag's RSS feed, most recent first.
        """
        url = f"{self._base}/feed/tag/{tag}"
        root = self._fetch_rss(url, f"tag '{tag}'")
        return self._parse_feed_items(root)

    def get_user_articles(self, username: str) -> Tuple[User, list[Article]]:
        """Get a user's profile and recent articles via RSS feed.

        Args:
            username: Medium username (with or without @ prefix).

        Returns:
            Tuple of (User profile, list of recent Articles).

        Raises:
            ValueError: If the user is not found (404).
            ConnectionError: On network errors.
        """
        username = username.lstrip("@")
        url = f"{self._base}/feed/@{username}"
        root = self._fetch_rss(url, f"@{username}")

        channel = root.find("channel")
        if channel is None:
            raise ValueError(f"User '{username}' not found")

        user = User.from_rss_channel(self._element_to_dict(channel))
        articles = self._parse_feed_items(root)
        return user, articles

    # ─── Internal Helpers ─────────────────────────────────────────

    def _fetch_rss(self, url: str, label: str) -> ET.Element:
        """Fetch and parse an RSS feed, normalizing XML namespace."""
        try:
            response = self._client.get(url)
        except Exception as e:
            raise ConnectionError(f"Failed to fetch {label} feed") from e

        if response.status_code == 404:
            raise ValueError(f"User '{label}' not found")

        response.raise_for_status()

        # Strip all namespaces for easier parsing
        xml_text = response.text
        xml_text = _strip_namespaces(xml_text)

        return ET.fromstring(xml_text)

    def _parse_feed_items(self, root: ET.Element) -> list[Article]:
        """Extract Article list from parsed RSS XML root."""
        channel = root.find("channel")
        if channel is None:
            return []
        items = channel.findall("item")
        return [self._parse_rss_item(item) for item in items]

    def _parse_rss_item(self, item: ET.Element) -> Article:
        """Parse a single RSS <item> element into an Article."""
        entry: dict[str, object] = {}
        entry["title"] = _get_text(item, "title")
        entry["link"] = _get_text(item, "link")
        entry["author"] = _get_text(item, "creator", namespace="dc") or _get_text(
            item, "creator"
        )
        entry["published"] = _get_text(item, "pubDate")

        # Collect categories as tags
        cats = item.findall("category")
        if cats:
            entry["category"] = [c.text or "" for c in cats]

        return Article.from_rss_entry(entry)

    @staticmethod
    def _element_to_dict(element: ET.Element) -> object:
        """Convert an ElementTree element into a nested structure.

        Leaf elements (text only, no children, no attrs) → plain string.
        Elements with children or attrs → dict.
        """
        # If it's a leaf — just text, no children, no attrs — return string
        text = (element.text or "").strip()
        if not element.attrib and len(element) == 0:
            return text

        result: dict[str, object] = {}
        if text:
            result["text"] = text

        # Attributes
        result.update(element.attrib)

        # Children — group by tag name
        children: dict[str, list] = {}
        for child in element:
            tag = child.tag.split("}")[-1]  # strip namespace
            children.setdefault(tag, []).append(
                MediumClient._element_to_dict(child)
            )

        for tag, items in children.items():
            result[tag] = items[0] if len(items) == 1 else items

        return result


# ─── XML Helpers ───────────────────────────────────────────────────

def _strip_namespaces(xml_str: str) -> str:
    """Remove XML namespace declarations to simplify parsing."""
    import re

    # Remove xmlns attributes
    xml_str = re.sub(r'\s+xmlns[^=]*="[^"]*"', "", xml_str)
    # Remove namespace prefixes from tags: <dc:creator> → <creator>
    xml_str = re.sub(r"(</?)(\w+):(\w+)", r"\1\3", xml_str)
    return xml_str


def _get_text(element: ET.Element, tag: str, namespace: str = "") -> str:
    """Get text content of a child element by tag name."""
    child = element.find(tag)
    if child is not None:
        return child.text or ""
    return ""
