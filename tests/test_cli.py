"""Tests for Click CLI commands."""

from click.testing import CliRunner
from medium_cli.cli import main


class TestSearchCommand:
    """`medium search` command."""

    def test_search_by_tag(self, httpx_mock):
        """medium search <tag> shows article table."""
        httpx_mock.add_response(
            url="https://medium.com/feed/tag/python",
            method="GET",
            text=_tag_rss(["Python Tips", "Async Python"]),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["search", "python"])

        assert result.exit_code == 0
        assert "Python Tips" in result.output
        assert "Async Python" in result.output

    def test_search_empty_tag(self, httpx_mock):
        """medium search with empty results shows message."""
        httpx_mock.add_response(
            url="https://medium.com/feed/tag/xyzzy",
            method="GET",
            text=_tag_rss([]),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["search", "xyzzy"])

        assert result.exit_code == 0
        assert "No articles found" in result.output

    def test_search_network_error(self, httpx_mock):
        """medium search shows error on network failure."""
        httpx_mock.add_exception(
            url="https://medium.com/feed/tag/python",
            exception=Exception("Down"),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["search", "python"])

        assert result.exit_code == 1
        assert "Error" in result.output


class TestUserCommand:
    """`medium user` command."""

    def test_user_shows_profile_and_articles(self, httpx_mock):
        """medium user @karpathy shows profile and article list."""
        httpx_mock.add_response(
            url="https://medium.com/feed/@karpathy",
            method="GET",
            text=_user_rss("karpathy", "Andrej Karpathy", ["State of GPT", "Biohacking"]),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["user", "karpathy"])

        assert result.exit_code == 0
        assert "Andrej Karpathy" in result.output
        assert "State of GPT" in result.output
        assert "Biohacking" in result.output

    def test_user_not_found(self, httpx_mock):
        """medium user shows error for unknown user."""
        httpx_mock.add_response(
            url="https://medium.com/feed/@nobody123xyz",
            status_code=404,
        )

        runner = CliRunner()
        result = runner.invoke(main, ["user", "nobody123xyz"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_user_with_at_prefix(self, httpx_mock):
        """medium user handles @ prefix gracefully."""
        httpx_mock.add_response(
            url="https://medium.com/feed/@alice",
            method="GET",
            text=_user_rss("alice", "Alice", ["Post One"]),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["user", "@alice"])

        assert result.exit_code == 0
        assert "Alice" in result.output


class TestReadCommand:
    """`medium read` command."""

    ARTICLE_URL = "https://karpathy.medium.com/software-2-0-abc123"

    def test_read_shows_article_content(self, httpx_mock):
        """medium read <url> shows article title, author, and cleaned content."""
        httpx_mock.add_response(
            url="https://medium.com/feed/@karpathy",
            method="GET",
            text=_user_rss_with_body(
                "@karpathy", "Andrej Karpathy",
                [("Software 2.0", self.ARTICLE_URL,
                  "Andrej Karpathy", "Sat, 11 Nov 2017 12:00:00 GMT",
                  ["Programming"],
                  "<p>The classical stack of Software 1.0.</p>"
                  "<h3>A New Kind of Software</h3>"
                  "<p>Software 2.0 is written in neural network weights.</p>")],
            ),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["read", self.ARTICLE_URL])

        assert result.exit_code == 0
        assert "Software 2.0" in result.output
        assert "Andrej Karpathy" in result.output
        assert "classical stack" in result.output
        assert "neural network weights" in result.output

    def test_read_article_not_found(self, httpx_mock):
        """medium read shows error when article not in feed."""
        httpx_mock.add_response(
            url="https://medium.com/feed/@karpathy",
            method="GET",
            text=_user_rss_with_body(
                "@karpathy", "Andrej Karpathy",
                [("Other Post", "https://karpathy.medium.com/other-789",
                  "Andrej Karpathy", "Mon, 20 Mar 2024 10:00:00 GMT",
                  [], "<p>something else</p>")],
            ),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["read", self.ARTICLE_URL])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_read_bad_url(self):
        """medium read shows error for non-Medium URLs."""
        runner = CliRunner()
        result = runner.invoke(main, ["read", "https://twitter.com/x"])

        assert result.exit_code == 1
        assert "Could not parse" in result.output


class TestTrendingCommand:
    """`medium trending` command."""

    def test_trending_shows_articles(self, httpx_mock):
        """medium trending shows popular articles table."""
        httpx_mock.add_response(
            url="https://medium.com/feed/tag/popular",
            method="GET",
            text=_tag_rss(["Hot Post 1", "Hot Post 2"]),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["trending"])

        assert result.exit_code == 0
        assert "Hot Post 1" in result.output
        assert "Hot Post 2" in result.output

    def test_trending_network_error(self, httpx_mock):
        """medium trending shows error on failure."""
        httpx_mock.add_exception(
            url="https://medium.com/feed/tag/popular",
            exception=Exception("Down"),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["trending"])

        assert result.exit_code == 1
        assert "Error" in result.output


class TestNoArgs:
    """Default help output."""

    def test_no_args_shows_help(self):
        """medium with no args shows help."""
        runner = CliRunner()
        result = runner.invoke(main, [])

        assert result.exit_code == 0
        assert "Usage:" in result.output or "Commands:" in result.output


# ─── XML Fixtures ───────────────────────────────────────────────────

def _tag_rss(titles: list[str]) -> str:
    items = ""
    for i, t in enumerate(titles):
        items += f"""
    <item>
        <title><![CDATA[{t}]]></title>
        <link>https://medium.com/article-{i}</link>
        <dc:creator><![CDATA[Author {i}]]></dc:creator>
        <pubDate>Mon, {15+i} Jan 2024 10:00:00 GMT</pubDate>
        <category>tag</category>
    </item>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
<channel>
    <title><![CDATA[tag on Medium]]></title>
    <link>https://medium.com/tag/tag</link>
{items}
</channel>
</rss>"""


def _user_rss(username: str, name: str, titles: list[str]) -> str:
    items = ""
    for i, t in enumerate(titles):
        items += f"""
    <item>
        <title><![CDATA[{t}]]></title>
        <link>https://medium.com/@{username}/article-{i}</link>
        <dc:creator><![CDATA[{name}]]></dc:creator>
        <pubDate>Mon, {15+i} Jan 2024 10:00:00 GMT</pubDate>
    </item>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
<channel>
    <title><![CDATA[Stories by {name} on Medium]]></title>
    <link>https://medium.com/@{username}</link>
    <image>
        <url>https://cdn-images-1.medium.com/fit/c/400/400/1*abc.jpeg</url>
    </image>
{items}
</channel>
</rss>"""


def _user_rss_with_body(
    username: str, name: str,
    items: list[tuple[str, str, str, str, list[str], str]],
) -> str:
    """Build a user RSS feed XML with content:encoded in each item."""
    items_xml = ""
    for title, link, author, pub_date, categories, body in items:
        cats = "".join(f"<category>{c}</category>" for c in categories)
        items_xml += f"""
    <item>
        <title><![CDATA[{title}]]></title>
        <link>{link}</link>
        <dc:creator><![CDATA[{author}]]></dc:creator>
        <pubDate>{pub_date}</pubDate>
        {cats}
        <encoded><![CDATA[{body}]]></encoded>
    </item>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     version="2.0">
<channel>
    <title><![CDATA[Stories by {name} on Medium]]></title>
    <link>https://medium.com/{username}</link>
    <image>
        <url>https://cdn-images-1.medium.com/fit/c/400/400/1*abc.jpeg</url>
    </image>
{items_xml}
</channel>
</rss>"""
