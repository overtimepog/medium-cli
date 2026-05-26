"""Tests for MediumClient HTTP interactions."""

import pytest
from medium_cli.client import MediumClient


class TestSearch:
    """Search by tag via RSS feed."""

    TAG_FEED_URL = "https://medium.com/feed/tag/python"

    def test_search_returns_articles(self, httpx_mock):
        """search() parses RSS tag feed and returns Article list."""
        httpx_mock.add_response(
            url=self.TAG_FEED_URL,
            method="GET",
            text=_rss_feed_xml(tag="python", items=[
                ("Python Tips and Tricks", "https://medium.com/@alice/python-tips-123",
                 "Alice", "Mon, 15 Jan 2024 10:00:00 GMT",
                 ["Python", "Programming"]),
                ("Async Python Deep Dive", "https://medium.com/@bob/async-python-456",
                 "Bob", "Tue, 16 Jan 2024 14:00:00 GMT",
                 ["Python", "Async"]),
            ]),
        )

        client = MediumClient()
        articles = client.search_tag("python")

        assert len(articles) == 2
        assert articles[0].title == "Python Tips and Tricks"
        assert articles[0].author == "Alice"
        assert articles[1].title == "Async Python Deep Dive"
        assert articles[1].tags == ["Python", "Async"]

    def test_search_empty_results(self, httpx_mock):
        """search() returns empty list when tag feed has no items."""
        httpx_mock.add_response(
            url="https://medium.com/feed/tag/nonexistent-tag-xyz",
            method="GET",
            text=_rss_feed_xml(tag="nonexistent-tag-xyz", items=[]),
        )

        client = MediumClient()
        articles = client.search_tag("nonexistent-tag-xyz")
        assert articles == []

    def test_search_network_error(self, httpx_mock):
        """search() raises ConnectionError on network failure."""
        httpx_mock.add_exception(
            url="https://medium.com/feed/tag/python",
            exception=Exception("Connection refused"),
        )

        client = MediumClient()
        with pytest.raises(ConnectionError, match="Failed to fetch.*tag.*python"):
            client.search_tag("python")


class TestUserArticles:
    """Get a user's articles via RSS feed."""

    USER_FEED_URL = "https://medium.com/feed/@karpathy"

    def test_get_user_articles_returns_articles_and_profile(self, httpx_mock):
        """get_user_articles() returns (User, [Article]) from RSS feed."""
        httpx_mock.add_response(
            url=self.USER_FEED_URL,
            method="GET",
            text=_user_rss_feed_xml(
                username="@karpathy",
                name="Andrej Karpathy",
                avatar="https://cdn-images-1.medium.com/fit/c/400/400/1*abc123.jpeg",
                items=[
                    ("State of GPT", "https://karpathy.medium.com/state-of-gpt-123",
                     "Andrej Karpathy", "Mon, 20 Mar 2024 10:00:00 GMT", ["AI", "GPT"]),
                    ("Biohacking", "https://karpathy.medium.com/biohacking-456",
                     "Andrej Karpathy", "Tue, 21 Mar 2024 14:00:00 GMT", ["Health"]),
                ],
            ),
        )

        client = MediumClient()
        user, articles = client.get_user_articles("karpathy")

        assert user.username == "@karpathy"
        assert user.name == "Andrej Karpathy"
        assert "abc123" in (user.avatar_url or "")
        assert len(articles) == 2
        assert articles[0].title == "State of GPT"
        assert articles[1].title == "Biohacking"

    def test_get_user_articles_not_found(self, httpx_mock):
        """get_user_articles() raises ValueError on 404."""
        httpx_mock.add_response(
            url=self.USER_FEED_URL,
            status_code=404,
            text="Not Found",
        )

        client = MediumClient()
        with pytest.raises(ValueError, match="User.*karpathy.*not found"):
            client.get_user_articles("karpathy")

    def test_get_user_articles_network_error(self, httpx_mock):
        """get_user_articles() raises ConnectionError on network failure."""
        httpx_mock.add_exception(
            url=self.USER_FEED_URL,
            exception=Exception("Timeout"),
        )

        client = MediumClient()
        with pytest.raises(ConnectionError, match="Failed to fetch.*@karpathy"):
            client.get_user_articles("karpathy")


class TestGetArticle:
    """Fetch full article content by URL."""

    def test_get_article_returns_cleaned_content(self, httpx_mock):
        """get_article() fetches user RSS, matches URL, returns cleaned text."""
        article_url = "https://karpathy.medium.com/software-2-0-abc123"
        content_html = (
            "<h3>A New Kind of Software</h3>"
            "<p>The 'classical stack' of Software 1.0 is what we're all familiar with.</p>"
            "<p>It's written in languages like Python, C++, etc.</p>"
            "<pre><code>def forward(x): return x * 2</code></pre>"
        )
        httpx_mock.add_response(
            url="https://medium.com/feed/@karpathy",
            method="GET",
            text=_user_rss_with_content(
                username="@karpathy",
                name="Andrej Karpathy",
                avatar="https://cdn-images-1.medium.com/1*abc.jpeg",
                items=[
                    ("State of GPT", "https://karpathy.medium.com/state-of-gpt-456",
                     "Andrej Karpathy", "Mon, 20 Mar 2024 10:00:00 GMT",
                     ["AI"], "<p>GPTs are amazing.</p>"),
                    ("Software 2.0", article_url,
                     "Andrej Karpathy", "Sat, 11 Nov 2017 12:00:00 GMT",
                     ["Programming"], content_html),
                ],
            ),
        )

        client = MediumClient()
        article, content = client.get_article(article_url)

        assert article.title == "Software 2.0"
        assert article.author == "Andrej Karpathy"
        assert "classical stack" in content
        assert "forward(x)" in content
        assert "<h3>" not in content  # HTML stripped
        assert "<p>" not in content

    def test_get_article_not_in_feed(self, httpx_mock):
        """get_article() raises ValueError when article not found in user's feed."""
        httpx_mock.add_response(
            url="https://medium.com/feed/@karpathy",
            method="GET",
            text=_user_rss_with_content(
                username="@karpathy", name="Andrej Karpathy",
                avatar="", items=[
                    ("Other Post", "https://karpathy.medium.com/other-789",
                     "Andrej Karpathy", "Mon, 20 Mar 2024 10:00:00 GMT",
                     [], "<p>something</p>"),
                ],
            ),
        )

        client = MediumClient()
        with pytest.raises(ValueError, match="not found"):
            client.get_article("https://karpathy.medium.com/software-2-0-abc123")

    def test_get_article_unrecognized_url(self):
        """get_article() raises ValueError for non-Medium or unparseable URLs."""
        client = MediumClient()
        with pytest.raises(ValueError, match="Could not parse"):
            client.get_article("https://twitter.com/user/status/123")

    def test_get_article_feed_error(self, httpx_mock):
        """get_article() propagates feed fetch errors."""
        httpx_mock.add_exception(
            url="https://medium.com/feed/@karpathy",
            exception=Exception("Down"),
        )

        client = MediumClient()
        with pytest.raises(ConnectionError):
            client.get_article("https://karpathy.medium.com/some-article-123")


class TestTrending:
    """Browse trending/popular articles."""

    def test_get_trending_returns_articles(self, httpx_mock):
        """get_trending() fetches popular tag RSS and returns articles."""
        httpx_mock.add_response(
            url="https://medium.com/feed/tag/popular",
            method="GET",
            text=_rss_feed_xml(tag="popular", items=[
                ("Trending Post 1", "https://medium.com/@alice/trending-1",
                 "Alice", "Mon, 25 May 2026 10:00:00 GMT", ["Tech"]),
                ("Trending Post 2", "https://medium.com/@bob/trending-2",
                 "Bob", "Mon, 25 May 2026 09:00:00 GMT", ["AI"]),
                ("Trending Post 3", "https://medium.com/@carol/trending-3",
                 "Carol", "Mon, 25 May 2026 08:00:00 GMT", ["Design"]),
            ]),
        )

        client = MediumClient()
        articles = client.get_trending()

        assert len(articles) == 3
        assert articles[0].title == "Trending Post 1"
        assert articles[1].title == "Trending Post 2"

    def test_get_trending_network_error(self, httpx_mock):
        """get_trending() raises ConnectionError on failure."""
        httpx_mock.add_exception(
            url="https://medium.com/feed/tag/popular",
            exception=Exception("Timeout"),
        )

        client = MediumClient()
        with pytest.raises(ConnectionError):
            client.get_trending()


# ─── XML Fixture Builders ───────────────────────────────────────────

def _rss_feed_xml(tag: str, items: list[tuple]) -> str:
    """Build a minimal Medium tag RSS feed XML string."""
    items_xml = ""
    for title, link, author, pub_date, categories in items:
        cats = "".join(f"<category>{c}</category>" for c in categories)
        items_xml += f"""
    <item>
        <title><![CDATA[{title}]]></title>
        <link>{link}</link>
        <dc:creator><![CDATA[{author}]]></dc:creator>
        <pubDate>{pub_date}</pubDate>
        {cats}
    </item>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
<channel>
    <title><![CDATA[{tag} on Medium]]></title>
    <link>https://medium.com/tag/{tag}/latest</link>
{items_xml}
</channel>
</rss>"""


def _user_rss_feed_xml(
    username: str, name: str, avatar: str, items: list[tuple]
) -> str:
    """Build a minimal Medium user RSS feed XML string."""
    items_xml = ""
    for title, link, author, pub_date, categories in items:
        cats = "".join(f"<category>{c}</category>" for c in categories)
        items_xml += f"""
    <item>
        <title><![CDATA[{title}]]></title>
        <link>{link}</link>
        <dc:creator><![CDATA[{author}]]></dc:creator>
        <pubDate>{pub_date}</pubDate>
        {cats}
    </item>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
<channel>
    <title><![CDATA[Stories by {name} on Medium]]></title>
    <link>https://medium.com/{username}</link>
    <image>
        <url>{avatar}</url>
    </image>
{items_xml}
</channel>
</rss>"""


def _user_rss_with_content(
    username: str, name: str, avatar: str,
    items: list[tuple[str, str, str, str, list[str], str]],
) -> str:
    """Build a Medium user RSS feed with article content (content:encoded)."""
    items_xml = ""
    for title, link, author, pub_date, categories, content_html in items:
        cats = "".join(f"<category>{c}</category>" for c in categories)
        encoded = f"<![CDATA[{content_html}]]>"
        items_xml += f"""
    <item>
        <title><![CDATA[{title}]]></title>
        <link>{link}</link>
        <dc:creator><![CDATA[{author}]]></dc:creator>
        <pubDate>{pub_date}</pubDate>
        {cats}
        <encoded>{encoded}</encoded>
    </item>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     version="2.0">
<channel>
    <title><![CDATA[Stories by {name} on Medium]]></title>
    <link>https://medium.com/{username}</link>
    <image>
        <url>{avatar}</url>
    </image>
{items_xml}
</channel>
</rss>"""
