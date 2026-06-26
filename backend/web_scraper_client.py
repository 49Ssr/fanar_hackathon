import re
import html
from html.parser import HTMLParser
from urllib.parse import urlparse
import requests

MAX_HTML_CHARS = 350_000
MAX_TEXT_CHARS = 6000
USER_AGENT = "QaaribHackathonBot/1.0 (+Qatar local assistant demo)"

URL_RE = re.compile(r"https?://[^\s<>'\")]+", re.I)


class ReadableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_skip = False
        self.skip_stack = []
        self.title_parts = []
        self.meta_description = ""
        self.current_tag = None
        self.current_heading = None
        self.headings = []
        self.paragraphs = []
        self.links = []
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = dict(attrs or [])
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_stack.append(tag)
            self.in_skip = True
            return
        if self.in_skip:
            return
        self.current_tag = tag
        if tag == "meta":
            name = (attrs.get("name") or attrs.get("property") or "").lower()
            if name in {"description", "og:description", "twitter:description"} and attrs.get("content") and not self.meta_description:
                self.meta_description = attrs.get("content", "").strip()
        if tag in {"h1", "h2", "h3"}:
            self.current_heading = []
        if tag == "p":
            self._buffer = []
        if tag == "a" and attrs.get("href"):
            text = attrs.get("title", "") or attrs.get("aria-label", "")
            href = attrs.get("href", "")
            if href.startswith("http") and len(self.links) < 8:
                self.links.append((text.strip(), href.strip()))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.skip_stack and tag == self.skip_stack[-1]:
            self.skip_stack.pop()
            self.in_skip = bool(self.skip_stack)
            return
        if self.in_skip:
            return
        if tag in {"h1", "h2", "h3"} and self.current_heading is not None:
            text = _norm(" ".join(self.current_heading))
            if text and text not in self.headings and len(self.headings) < 12:
                self.headings.append(text)
            self.current_heading = None
        if tag == "p":
            text = _norm(" ".join(self._buffer))
            if len(text) >= 45 and text not in self.paragraphs and len(self.paragraphs) < 20:
                self.paragraphs.append(text)
            self._buffer = []
        self.current_tag = None

    def handle_data(self, data):
        if self.in_skip:
            return
        text = data.strip()
        if not text:
            return
        if self.current_tag == "title":
            self.title_parts.append(text)
        if self.current_heading is not None:
            self.current_heading.append(text)
        if self.current_tag == "p":
            self._buffer.append(text)


def _norm(text):
    text = html.unescape(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_url(text):
    match = URL_RE.search(text or "")
    if not match:
        return ""
    return match.group(0).rstrip(".,);]")


def _safe_domain(url):
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _sentence_summary(parts, limit=5):
    chosen = []
    for part in parts:
        part = _norm(part)
        if not part:
            continue
        if len(part) > 360:
            part = part[:357].rsplit(" ", 1)[0] + "..."
        if part not in chosen:
            chosen.append(part)
        if len(chosen) >= limit:
            break
    return chosen


def web_scrape(query, num_results=1):
    """Fetch a page and extract a demo-safe readable summary.

    This is not a browser: heavy JS / blocked sites may not expose full text.
    """
    url = extract_url(query)
    if not url:
        return [{
            "title": "No URL found",
            "summary": "I need a full http(s) link to scrape a page.",
            "final_answer": "Send me the full link and I’ll read/summarise the page content I can access.",
        }]

    domain = _safe_domain(url)
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8"},
            timeout=12,
            allow_redirects=True,
        )
    except Exception as e:
        return [{
            "title": "Scrape failed",
            "url": url,
            "summary": f"Could not fetch the page: {e}",
            "final_answer": f"I couldn’t fetch that page cleanly. Error: {e}",
        }]

    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    text = response.text[:MAX_HTML_CHARS] if response.text else ""

    if not response.ok:
        return [{
            "title": "Page returned an error",
            "url": url,
            "status_code": response.status_code,
            "content_type": content_type,
            "summary": f"The page returned HTTP {response.status_code}.",
            "final_answer": f"I reached the page, but it returned HTTP {response.status_code}. Use web search or an official mirror if this site blocks scraping.",
        }]

    if "html" not in content_type and "text" not in content_type and text.startswith("%PDF"):
        return [{
            "title": "PDF/document detected",
            "url": url,
            "status_code": response.status_code,
            "content_type": content_type or "application/pdf",
            "summary": "The URL appears to be a PDF/document rather than a normal HTML page.",
            "final_answer": "That link looks like a document/PDF rather than a normal web page. I can still use the URL as a source hint, but the lightweight scraper is built for readable HTML pages.",
        }]

    parser = ReadableHTMLParser()
    try:
        parser.feed(text)
    except Exception:
        pass

    title = _norm(" ".join(parser.title_parts)) or domain or url
    description = _norm(parser.meta_description)
    headings = _sentence_summary(parser.headings, limit=8)
    paragraphs = _sentence_summary(parser.paragraphs, limit=6)

    key_lines = []
    if description:
        key_lines.append(description)
    key_lines.extend(headings[:4])
    key_lines.extend(paragraphs[:4])
    key_lines = _sentence_summary(key_lines, limit=7)

    extracted_text = "\n".join(key_lines)[:MAX_TEXT_CHARS]
    if not extracted_text:
        extracted_text = "The page loaded, but the lightweight scraper did not find readable article text. It may be JavaScript-rendered or blocked."

    final_lines = [f"Page check: {title}", f"Source: {url}"]
    if key_lines:
        final_lines.append("Key extract:")
        for line in key_lines[:5]:
            final_lines.append(f"- {line}")
    else:
        final_lines.append(extracted_text)
    final_lines.append("Heads up: this is a lightweight scraper, not a full browser; dynamic or blocked content may be incomplete.")

    return [{
        "title": title,
        "url": url,
        "domain": domain,
        "status_code": response.status_code,
        "content_type": content_type,
        "summary": extracted_text,
        "page_title": title,
        "headings": " | ".join(headings[:8]),
        "extracted_text": extracted_text,
        "final_answer": "\n".join(final_lines),
    }]


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "https://www.visitqatar.com/"
    for r in web_scrape(q):
        print(r.get("final_answer"))
