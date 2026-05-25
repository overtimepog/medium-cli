"""Data models for Medium articles and users."""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser


class _TextStripper(HTMLParser):
    """Extract text content from HTML, stripping all tags."""

    def __init__(self):
        super().__init__()
        self.text: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def get_text(self) -> str:
        return " ".join(self.text).strip()


def _extract_first_h3(html: str) -> str:
    """Extract the first <h3> text from HTML content. Returns empty string if none."""
    match = re.search(r"<h3[^>]*>(.*?)</h3>", html, re.IGNORECASE | re.DOTALL)
    if match:
        h3_html = match.group(1)
        stripper = _TextStripper()
        stripper.feed(h3_html)
        return stripper.get_text()
    return ""


def _strip_html(html: str | None) -> str:
    """Strip HTML tags and return plain text."""
    if not html:
        return ""
    stripper = _TextStripper()
    stripper.feed(html)
    return stripper.get_text()


@dataclass
class Article:
    """A Medium article."""

    title: str
    url: str
    author: str
    published_at: datetime.datetime | None = None
    subtitle: str = ""
    tags: list[str] = field(default_factory=list)
    claps: int = 0
    read_time: int = 0

    @classmethod
    def from_rss_entry(cls, entry: dict) -> Article:
        """Create an Article from a Medium RSS feed <item> dict."""
        published_at = None
        if "published" in entry:
            try:
                published_at = parsedate_to_datetime(entry["published"])
            except (ValueError, TypeError):
                pass

        # Get subtitle: prefer content:encoded h3, fall back to summary
        subtitle = ""
        content = entry.get("content")
        if isinstance(content, list) and content:
            content_value = content[0].get("value", "")
        elif isinstance(content, dict):
            content_value = content.get("value", "")
        else:
            content_value = ""
        if content_value:
            subtitle = _extract_first_h3(content_value)
        if not subtitle:
            summary = entry.get("summary", "")
            subtitle = _strip_html(summary)

        tags = []
        if "category" in entry:
            categories = entry["category"]
            if isinstance(categories, list):
                tags = categories
            else:
                tags = [categories]

        return cls(
            title=entry.get("title", ""),
            url=entry.get("link", ""),
            author=entry.get("author", ""),
            published_at=published_at,
            subtitle=subtitle,
            tags=tags,
        )

    @classmethod
    def from_search_json(cls, hit: dict) -> Article:
        """Create an Article from a Medium search JSON result."""
        created_at = hit.get("createdAt", 0)
        published_at = None
        if created_at:
            try:
                published_at = datetime.datetime.fromtimestamp(
                    created_at / 1000, tz=datetime.timezone.utc
                )
            except (OSError, ValueError, OverflowError):
                pass

        author_name = ""
        author = hit.get("author")
        if isinstance(author, dict):
            author_name = author.get("name", "")

        tags = [t["name"] for t in hit.get("tags", []) if isinstance(t, dict)]

        return cls(
            title=hit.get("title", ""),
            url=hit.get("url", ""),
            author=author_name,
            published_at=published_at,
            subtitle=hit.get("subtitle", ""),
            tags=tags,
            claps=hit.get("clapCount", 0),
            read_time=hit.get("readingTime", 0),
        )


@dataclass
class User:
    """A Medium user profile."""

    username: str
    name: str = ""
    url: str = ""
    bio: str = ""
    avatar_url: str | None = None

    @classmethod
    def from_rss_channel(cls, channel: dict) -> User:
        """Create a User from a Medium RSS <channel> element."""
        title = channel.get("title", "")
        link = channel.get("link", "")

        # Handle case where link is a list (multiple <link> children)
        if isinstance(link, list):
            # Find the Medium user URL link
            for item in link:
                if isinstance(item, str) and "medium.com/@" in item:
                    link = item
                    break
            else:
                link = link[0] if link else ""
        if isinstance(link, dict):
            link = link.get("text", "")

        # Extract username from URL: https://medium.com/@username
        username = ""
        match = re.search(r"medium\.com/(@[\w.-]+)", link)
        if match:
            username = match.group(1)

        # Parse name from title: "Stories by Alice Coder on Medium"
        name = ""
        stories_match = re.match(r"Stories by (.+?) on Medium", title)
        if stories_match:
            name = stories_match.group(1)
        else:
            name = title

        # Bio from description
        bio = _strip_html(channel.get("description", ""))

        # Avatar from image
        avatar = None
        image = channel.get("image")
        if isinstance(image, dict):
            avatar = image.get("url")

        return cls(
            username=username,
            name=name,
            url=link,
            bio=bio,
            avatar_url=avatar,
        )
