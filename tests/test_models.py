"""Tests for Medium data models."""

import datetime

import pytest
from medium_cli.models import Article, User


class TestArticle:
    """Article model tests."""

    def test_from_rss_entry_parses_all_fields(self):
        """Article.from_rss_entry() extracts title, author, url, date, content."""
        entry = {
            "title": "How to Write Good Code",
            "link": "https://medium.com/@alice/how-to-write-good-code-abc123",
            "author": "Alice Coder",
            "published": "Mon, 15 Jan 2024 10:30:00 GMT",
            "summary": "<p>Writing good code is an art form.</p>",
            "category": ["Programming", "Software Engineering"],
        }
        article = Article.from_rss_entry(entry)

        assert article.title == "How to Write Good Code"
        assert article.url == "https://medium.com/@alice/how-to-write-good-code-abc123"
        assert article.author == "Alice Coder"
        assert isinstance(article.published_at, datetime.datetime)
        assert article.published_at.year == 2024
        assert article.published_at.month == 1
        assert article.published_at.day == 15
        assert "art form" in article.subtitle
        assert "Programming" in article.tags
        assert "Software Engineering" in article.tags

    def test_from_rss_entry_handles_minimal_fields(self):
        """from_rss_entry() works with minimal RSS entry (no categories)."""
        entry = {
            "title": "Minimal Post",
            "link": "https://medium.com/@bob/minimal-xyz",
            "author": "Bob",
            "published": "Sun, 01 Dec 2024 00:00:00 GMT",
        }
        article = Article.from_rss_entry(entry)

        assert article.title == "Minimal Post"
        assert article.url == "https://medium.com/@bob/minimal-xyz"
        assert article.author == "Bob"
        assert article.tags == []
        assert article.subtitle == ""

    def test_from_rss_entry_parses_medium_subtitle(self):
        """from_rss_entry() extracts subtitle from Medium content:encoded field."""
        entry = {
            "title": "A Deep Dive into Rust",
            "link": "https://medium.com/@carlos/rust-deep-dive",
            "author": "Carlos",
            "published": "Tue, 20 Feb 2024 14:00:00 GMT",
            "content": [
                {
                    "value": (
                        "<h3>Rust's ownership model is revolutionary</h3>"
                        "<p>Let me explain why...</p>"
                    )
                }
            ],
        }
        article = Article.from_rss_entry(entry)
        assert article.subtitle == "Rust's ownership model is revolutionary"

    def test_from_search_json_parses_hit(self):
        """Article.from_search_json() extracts from Medium search JSON."""
        hit = {
            "title": "Machine Learning in Production",
            "url": "https://medium.com/@dana/ml-in-prod-456",
            "author": {"name": "Dana Dev"},
            "createdAt": 1705334400000,  # Jan 15, 2024 12:00:00 UTC
            "subtitle": "Lessons from deploying ML at scale",
            "clapCount": 2500,
            "readingTime": 8,
            "tags": [{"name": "Machine Learning"}, {"name": "DevOps"}],
        }
        article = Article.from_search_json(hit)

        assert article.title == "Machine Learning in Production"
        assert article.url == "https://medium.com/@dana/ml-in-prod-456"
        assert article.author == "Dana Dev"
        assert article.subtitle == "Lessons from deploying ML at scale"
        assert article.claps == 2500
        assert article.read_time == 8
        assert article.tags == ["Machine Learning", "DevOps"]
        assert isinstance(article.published_at, datetime.datetime)

    def test_from_search_json_minimal(self):
        """from_search_json() handles minimal search hit."""
        hit = {
            "title": "Quick Tip",
            "url": "https://medium.com/@eva/quick-tip",
            "author": {"name": "Eva"},
            "createdAt": 0,
        }
        article = Article.from_search_json(hit)
        assert article.title == "Quick Tip"
        assert article.author == "Eva"
        assert article.claps == 0
        assert article.read_time == 0
        assert article.tags == []
        assert article.subtitle == ""


class TestUser:
    """User model tests."""

    def test_from_rss_channel_parses_user_info(self):
        """User.from_rss_channel() extracts user info from RSS channel."""
        channel = {
            "title": "Stories by Alice Coder on Medium",
            "link": "https://medium.com/@alice",
            "description": "I write about Python, Rust, and developer tools.",
            "image": {
                "url": "https://cdn-images-1.medium.com/fit/c/400/400/1*abc123.jpeg"
            },
        }
        user = User.from_rss_channel(channel)

        assert user.username == "@alice"
        assert user.name == "Alice Coder"
        assert user.url == "https://medium.com/@alice"
        assert "Python" in user.bio
        assert "abc123" in user.avatar_url

    def test_from_rss_channel_no_image(self):
        """from_rss_channel() handles missing avatar image."""
        channel = {
            "title": "Stories by Bob on Medium",
            "link": "https://medium.com/@bob",
        }
        user = User.from_rss_channel(channel)
        assert user.username == "@bob"
        assert user.avatar_url is None

    def test_from_rss_channel_invalid_title(self):
        """from_rss_channel() falls back to URL when title doesn't match pattern."""
        channel = {
            "title": "Some Other Feed",
            "link": "https://medium.com/@charlie",
        }
        user = User.from_rss_channel(channel)
        assert user.username == "@charlie"
        assert user.name == "Some Other Feed"
