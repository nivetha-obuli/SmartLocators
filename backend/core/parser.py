import httpx
from bs4 import BeautifulSoup, Tag
from typing import Optional, List, Tuple
import re

INTERACTIVE_TAGS = {
    "input", "button", "a", "select", "textarea",
    "form", "label", "img", "table", "th", "td",
    "div", "span", "li", "nav", "header", "footer"
}

class HTMLParser:
    def __init__(self, parser_backend: str = "html.parser"):
        self.parser_backend = parser_backend

    async def fetch_url(self, url: str) -> Tuple[str, str]:
        """Fetch HTML content from a URL asynchronously."""
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 SmartLocatorBot/1.0"}
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text, str(response.url)

    def parse(self, html: str) -> BeautifulSoup:
        """Parse HTML string into BeautifulSoup object."""
        return BeautifulSoup(html, self.parser_backend)

    def extract_elements(
        self,
        soup: BeautifulSoup,
        filter_tag: Optional[str] = None,
        filter_attribute: Optional[str] = None,
        limit: int = 100
    ) -> List[Tag]:
        """Extract relevant interactive elements from parsed HTML."""
        tags_to_search = [filter_tag] if filter_tag else list(INTERACTIVE_TAGS)
        elements = []

        for tag_name in tags_to_search:
            found = soup.find_all(tag_name, limit=limit)
            for el in found:
                if not isinstance(el, Tag):
                    continue
                if filter_attribute and not el.has_attr(filter_attribute):
                    continue
                # Skip elements with no useful attributes or text
                if not el.attrs and not el.get_text(strip=True):
                    continue
                elements.append(el)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for el in elements:
            key = id(el)
            if key not in seen:
                seen.add(key)
                unique.append(el)

        return unique[:limit]

    def get_element_attributes(self, element: Tag) -> dict:
        """Extract all attributes from an element as a flat dict."""
        attrs = {}
        for key, val in element.attrs.items():
            if isinstance(val, list):
                attrs[key] = " ".join(val)
            else:
                attrs[key] = str(val)
        return attrs

    def get_page_title(self, soup: BeautifulSoup) -> Optional[str]:
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else None