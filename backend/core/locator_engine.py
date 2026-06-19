from bs4 import Tag, BeautifulSoup
from typing import List, Optional, Tuple
import re
from backend.models.schemas import Locator, LocatorType, ReliabilityScore


class LocatorEngine:
    """
    Generates XPath and CSS locators using multiple strategies.
    Strategies are tried in order of reliability preference.
    """

    # ──────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────

    def generate_all(self, element: Tag, soup: BeautifulSoup) -> List[Locator]:
        locators: List[Locator] = []

        # --- XPath strategies ---
        locators += self._xpath_by_id(element)
        locators += self._xpath_by_name(element)
        locators += self._xpath_by_test_id(element)
        locators += self._xpath_by_aria(element)
        locators += self._xpath_by_text(element)
        locators += self._xpath_by_placeholder(element)
        locators += self._xpath_by_type_value(element)
        locators += self._xpath_absolute(element, soup)

        # --- CSS strategies ---
        locators += self._css_by_id(element)
        locators += self._css_by_class(element)
        locators += self._css_by_attribute(element)
        locators += self._css_nth_child(element, soup)

        # Deduplicate and sort by score descending
        seen_values = set()
        unique: List[Locator] = []
        for loc in locators:
            if loc.value not in seen_values:
                seen_values.add(loc.value)
                unique.append(loc)

        unique.sort(key=lambda x: x.score, reverse=True)
        return unique

    # ──────────────────────────────────────────────
    # XPATH STRATEGIES
    # ──────────────────────────────────────────────

    def _xpath_by_id(self, el: Tag) -> List[Locator]:
        id_val = el.get("id", "").strip()
        if not id_val or self._is_dynamic_id(id_val):
            return []
        return [Locator(
            locator_type=LocatorType.XPATH,
            value=f'//*[@id="{id_val}"]',
            strategy="id-based",
            reliability=ReliabilityScore.HIGH,
            score=0.95,
            notes="ID locator — fastest and most reliable when ID is static"
        )]

    def _xpath_by_name(self, el: Tag) -> List[Locator]:
        name = el.get("name", "").strip()
        if not name:
            return []
        return [Locator(
            locator_type=LocatorType.XPATH,
            value=f'//{el.name}[@name="{name}"]',
            strategy="name-based",
            reliability=ReliabilityScore.HIGH,
            score=0.88,
            notes="Name attribute — reliable for form inputs"
        )]

    def _xpath_by_test_id(self, el: Tag) -> List[Locator]:
        locators = []
        for attr in ["data-testid", "data-test", "data-cy", "data-qa", "data-automation-id"]:
            val = el.get(attr, "").strip()
            if val:
                locators.append(Locator(
                    locator_type=LocatorType.XPATH,
                    value=f'//*[@{attr}="{val}"]',
                    strategy="test-id-based",
                    reliability=ReliabilityScore.HIGH,
                    score=0.97,
                    notes=f"Test automation attribute ({attr}) — best practice for stable locators"
                ))
        return locators

    def _xpath_by_aria(self, el: Tag) -> List[Locator]:
        locators = []
        for attr in ["aria-label", "aria-labelledby", "role"]:
            val = el.get(attr, "").strip()
            if val:
                locators.append(Locator(
                    locator_type=LocatorType.XPATH,
                    value=f'//*[@{attr}="{val}"]',
                    strategy="aria-based",
                    reliability=ReliabilityScore.HIGH,
                    score=0.90,
                    notes=f"ARIA attribute — accessibility-friendly and stable"
                ))
        return locators

    def _xpath_by_text(self, el: Tag) -> List[Locator]:
        text = el.get_text(strip=True)
        if not text or len(text) > 80 or len(text) < 2:
            return []
        safe_text = text.replace('"', "'")
        locators = [
            Locator(
                locator_type=LocatorType.XPATH,
                value=f'//{el.name}[text()="{safe_text}"]',
                strategy="exact-text",
                reliability=ReliabilityScore.MEDIUM,
                score=0.70,
                notes="Exact text match — breaks if copy changes"
            ),
            Locator(
                locator_type=LocatorType.XPATH,
                value=f'//{el.name}[contains(text(),"{safe_text[:30]}")]',
                strategy="partial-text",
                reliability=ReliabilityScore.MEDIUM,
                score=0.65,
                notes="Partial text match — more flexible but less precise"
            )
        ]
        return locators

    def _xpath_by_placeholder(self, el: Tag) -> List[Locator]:
        ph = el.get("placeholder", "").strip()
        if not ph:
            return []
        return [Locator(
            locator_type=LocatorType.XPATH,
            value=f'//{el.name}[@placeholder="{ph}"]',
            strategy="placeholder-based",
            reliability=ReliabilityScore.MEDIUM,
            score=0.75,
            notes="Placeholder — good for input fields"
        )]

    def _xpath_by_type_value(self, el: Tag) -> List[Locator]:
        type_val = el.get("type", "").strip()
        value_val = el.get("value", "").strip()
        if not type_val:
            return []
        if value_val:
            return [Locator(
                locator_type=LocatorType.XPATH,
                value=f'//{el.name}[@type="{type_val}" and @value="{value_val}"]',
                strategy="type-value",
                reliability=ReliabilityScore.MEDIUM,
                score=0.72,
                notes="Type + value combination"
            )]
        return [Locator(
            locator_type=LocatorType.XPATH,
            value=f'//{el.name}[@type="{type_val}"]',
            strategy="type-based",
            reliability=ReliabilityScore.LOW,
            score=0.50,
            notes="Type only — may match multiple elements"
        )]

    def _xpath_absolute(self, el: Tag, soup: BeautifulSoup) -> List[Locator]:
        """Generate absolute XPath as a last-resort locator."""
        path_parts = []
        current = el
        while current and current.name and current.name != "[document]":
            parent = current.parent
            if parent:
                siblings = [s for s in parent.children
                            if isinstance(s, Tag) and s.name == current.name]
                if len(siblings) > 1:
                    idx = siblings.index(current) + 1
                    path_parts.insert(0, f"{current.name}[{idx}]")
                else:
                    path_parts.insert(0, current.name)
            current = parent

        xpath = "/" + "/".join(path_parts) if path_parts else ""
        if not xpath:
            return []
        return [Locator(
            locator_type=LocatorType.XPATH,
            value=xpath,
            strategy="absolute-xpath",
            reliability=ReliabilityScore.LOW,
            score=0.30,
            notes="Absolute XPath — fragile, use only as last resort"
        )]

    # ──────────────────────────────────────────────
    # CSS STRATEGIES
    # ──────────────────────────────────────────────

    def _css_by_id(self, el: Tag) -> List[Locator]:
        id_val = el.get("id", "").strip()
        if not id_val or self._is_dynamic_id(id_val):
            return []
        return [Locator(
            locator_type=LocatorType.CSS,
            value=f"#{self._css_escape(id_val)}",
            strategy="id-based",
            reliability=ReliabilityScore.HIGH,
            score=0.95,
            notes="CSS ID selector — fastest CSS locator"
        )]

    def _css_by_class(self, el: Tag) -> List[Locator]:
        classes = el.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()
        stable = [c for c in classes if not self._is_dynamic_class(c)]
        if not stable:
            return []
        selector = el.name + "".join(f".{self._css_escape(c)}" for c in stable[:3])
        score = 0.75 if len(stable) >= 2 else 0.55
        return [Locator(
            locator_type=LocatorType.CSS,
            value=selector,
            strategy="class-based",
            reliability=ReliabilityScore.MEDIUM if score > 0.6 else ReliabilityScore.LOW,
            score=score,
            notes=f"CSS class selector using {len(stable)} stable class(es)"
        )]

    def _css_by_attribute(self, el: Tag) -> List[Locator]:
        locators = []
        priority_attrs = ["name", "placeholder", "type", "href", "src",
                          "data-testid", "data-test", "aria-label", "role"]
        for attr in priority_attrs:
            val = el.get(attr, "").strip()
            if val:
                locators.append(Locator(
                    locator_type=LocatorType.CSS,
                    value=f'{el.name}[{attr}="{val}"]',
                    strategy="attribute-based",
                    reliability=ReliabilityScore.HIGH if attr in ("data-testid", "aria-label") else ReliabilityScore.MEDIUM,
                    score=0.85 if attr in ("data-testid", "aria-label") else 0.70,
                    notes=f"CSS attribute selector on [{attr}]"
                ))
        return locators[:3]

    def _css_nth_child(self, el: Tag, soup: BeautifulSoup) -> List[Locator]:
        parent = el.parent
        if not parent or not parent.name:
            return []
        siblings = [s for s in parent.children if isinstance(s, Tag)]
        idx = siblings.index(el) + 1 if el in siblings else None
        if idx is None:
            return []
        parent_id = parent.get("id", "")
        if parent_id and not self._is_dynamic_id(parent_id):
            selector = f"#{parent_id} > {el.name}:nth-child({idx})"
        else:
            selector = f"{el.name}:nth-child({idx})"
        return [Locator(
            locator_type=LocatorType.CSS,
            value=selector,
            strategy="nth-child",
            reliability=ReliabilityScore.LOW,
            score=0.45,
            notes="Position-based CSS — fragile if siblings change"
        )]

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────

    def _is_dynamic_id(self, id_val: str) -> bool:
        """Detect auto-generated / dynamic IDs."""
        patterns = [
            r'\d{5,}',           # long numeric sequences
            r'[a-f0-9]{8,}',     # hex hash-like
            r':[a-z0-9]+:',      # React-style :r0:
            r'__[A-Z]',          # framework prefixes
        ]
        return any(re.search(p, id_val) for p in patterns)

    def _is_dynamic_class(self, cls: str) -> bool:
        """Detect CSS Modules / hashed class names."""
        return bool(re.search(r'[_-][a-z0-9]{5,}$', cls))

    def _css_escape(self, value: str) -> str:
        """Escape special characters for CSS selectors."""
        return re.sub(r'([!"#$%&\'()*+,.\/:;<=>?@\[\\\]^`{|}~])', r'\\\1', value)