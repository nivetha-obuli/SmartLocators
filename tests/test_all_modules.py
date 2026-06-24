import pytest  # type: ignore
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from bs4 import BeautifulSoup  # type: ignore
 
 
# ══════════════════════════════════════════════════════════════
#  FIXTURES
# ══════════════════════════════════════════════════════════════
 
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
  <form id="login-form">
    <input id="username" name="username" type="text"
           placeholder="Enter username" data-testid="user-input"/>
    <input id="password" name="password" type="password"
           placeholder="Enter password" aria-label="Password field"/>
    <button id="login-btn" type="submit" data-cy="submit-btn">Login</button>
    <a href="/forgot" class="link-secondary">Forgot password?</a>
    <select name="role" id="role-select">
      <option value="user">User</option>
      <option value="admin">Admin</option>
    </select>
  </form>
  <div class="dynamic" id="item-123456">Dynamic ID</div>
  <div id="react-id" data-id=":r0:">React ID</div>
</body>
</html>
"""
 
 
@pytest.fixture
def soup():
    return BeautifulSoup(SAMPLE_HTML, "lxml")
 
 
@pytest.fixture
def parser():
    from backend.core.parser import HTMLParser
    return HTMLParser()
 
 
@pytest.fixture
def engine():
    from backend.core.locator_engine import LocatorEngine
    return LocatorEngine()
 
 
@pytest.fixture
def recommender():
    from backend.core.recommender import LocatorRecommender
    return LocatorRecommender()
 
 
@pytest.fixture
def username_tag(soup):
    return soup.find("input", {"id": "username"})
 
 
@pytest.fixture
def button_tag(soup):
    return soup.find("button", {"id": "login-btn"})
 
 
@pytest.fixture
def dynamic_tag(soup):
    return soup.find("div", {"id": "item-123456"})
 
 
@pytest.fixture
def react_tag(soup):
    return soup.find("div", {"id": "react-id"})
 
 
# ══════════════════════════════════════════════════════════════
#  TASK 4.1 — schemas.py tests
# ══════════════════════════════════════════════════════════════
 
class TestSchemas:
    def test_analyze_request_url(self):
        from backend.models.schemas import AnalyzeRequest, InputType
        req = AnalyzeRequest(input_type=InputType.URL, content="https://example.com")
        assert req.input_type == InputType.URL
        assert req.content == "https://example.com"
        assert req.filter_tag is None
 
    def test_analyze_request_html(self):
        from backend.models.schemas import AnalyzeRequest, InputType
        req = AnalyzeRequest(input_type=InputType.HTML, content="<html></html>")
        assert req.input_type == InputType.HTML
 
    def test_locator_model(self):
        from backend.models.schemas import Locator, LocatorType, ReliabilityScore
        loc = Locator(
            locator_type=LocatorType.XPATH,
            value='//*[@id="test"]',
            strategy="id-based",
            reliability=ReliabilityScore.HIGH,
            score=0.95,
        )
        assert loc.score == 0.95
        assert loc.reliability == ReliabilityScore.HIGH
 
    def test_web_element_model(self):
        from backend.models.schemas import WebElement, Locator, LocatorType, ReliabilityScore
        loc = Locator(
            locator_type=LocatorType.CSS, value="#btn",
            strategy="id-based", reliability=ReliabilityScore.HIGH,
            score=0.95,
        )
        el = WebElement(
            tag="button", text="Login",
            attributes={"id": "btn"},
            locators=[loc], best_locator=loc,
            element_index=0,
        )
        assert el.tag == "button"
        assert el.best_locator.value == "#btn"
 
    def test_validate_response_model(self):
        from backend.models.schemas import ValidateResponse, LocatorType
        resp = ValidateResponse(
            locator_type=LocatorType.XPATH,
            locator_value='//*[@id="x"]',
            is_valid=True, elements_found=1,
            is_unique=True, message="✅ Found",
        )
        assert resp.is_unique is True
 
    def test_reliability_enum_values(self):
        from backend.models.schemas import ReliabilityScore
        assert ReliabilityScore.HIGH   == "high"
        assert ReliabilityScore.MEDIUM == "medium"
        assert ReliabilityScore.LOW    == "low"
 
    def test_locator_type_enum(self):
        from backend.models.schemas import LocatorType
        assert LocatorType.XPATH == "xpath"
        assert LocatorType.CSS   == "css"
 
 
# ══════════════════════════════════════════════════════════════
#  TASK 4.2 — parser.py tests
# ══════════════════════════════════════════════════════════════
 
class TestParser:
    def test_parse_returns_soup(self, parser):
        s = parser.parse(SAMPLE_HTML)
        assert s is not None
        assert s.find("title").text == "Test Page"
 
    def test_get_page_title(self, parser):
        s = parser.parse(SAMPLE_HTML)
        assert parser.get_page_title(s) == "Test Page"
 
    def test_get_page_title_missing(self, parser):
        s = parser.parse("<html><body></body></html>")
        assert parser.get_page_title(s) is None
 
    def test_extract_elements_default(self, parser, soup):
        elements = parser.extract_elements(soup)
        tags = [e.name for e in elements]
        assert "input" in tags
        assert "button" in tags
        assert "a" in tags
 
    def test_extract_elements_filter_tag(self, parser, soup):
        elements = parser.extract_elements(soup, filter_tag="input")
        assert all(e.name == "input" for e in elements)
        assert len(elements) == 2
 
    def test_extract_elements_filter_attribute(self, parser, soup):
        elements = parser.extract_elements(soup, filter_attribute="data-testid")
        assert len(elements) == 1
        assert elements[0].get("data-testid") == "user-input"
 
    def test_extract_elements_deduplication(self, parser, soup):
        # Calling twice should not duplicate
        e1 = parser.extract_elements(soup)
        e2 = parser.extract_elements(soup)
        assert len(e1) == len(e2)
 
    def test_get_element_attributes(self, parser, username_tag):
        attrs = parser.get_element_attributes(username_tag)
        assert attrs["id"] == "username"
        assert attrs["name"] == "username"
        assert attrs["type"] == "text"
        assert attrs["data-testid"] == "user-input"
 
    def test_get_element_attributes_class_list(self, parser):
        from bs4 import BeautifulSoup  # type: ignore
        html  = '<div class="btn primary active">Click</div>'
        s     = BeautifulSoup(html, "lxml")
        div   = s.find("div")
        attrs = parser.get_element_attributes(div)
        assert "btn" in attrs["class"]
 
    @pytest.mark.asyncio
    async def test_fetch_url_success(self, parser):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_HTML
        mock_resp.url  = "https://example.com"
        mock_resp.raise_for_status = MagicMock()
 
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)
        mock_client.get        = AsyncMock(return_value=mock_resp)
 
        with patch("httpx.AsyncClient", return_value=mock_client):
            html, url = await parser.fetch_url("https://example.com")
        assert "Test Page" in html
        assert "example.com" in url
 
    @pytest.mark.asyncio
    async def test_fetch_url_error(self, parser):
        import httpx
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)
        mock_client.get        = AsyncMock(side_effect=httpx.RequestError("timeout"))
 
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.RequestError):
                await parser.fetch_url("https://bad-url.com")
 
 
# ══════════════════════════════════════════════════════════════
#  TASK 4.3 — locator_engine.py tests
# ══════════════════════════════════════════════════════════════
 
class TestLocatorEngine:
 
    def test_generate_all_returns_list(self, engine, username_tag, soup):
        locs = engine.generate_all(username_tag, soup)
        assert isinstance(locs, list)
        assert len(locs) > 0
 
    def test_testid_strategy(self, engine, username_tag, soup):
        locs = engine.generate_all(username_tag, soup)
        vals = [l.value for l in locs]
        assert any("data-testid" in v for v in vals)
 
    def test_testid_highest_score(self, engine, username_tag, soup):
        locs = engine.generate_all(username_tag, soup)
        testid_locs = [l for l in locs if "data-testid" in l.value]
        assert testid_locs
        assert testid_locs[0].score >= 0.95
 
    def test_id_strategy(self, engine, username_tag, soup):
        locs = engine.generate_all(username_tag, soup)
        id_locs = [l for l in locs if 'id="username"' in l.value or '[@id="username"]' in l.value]
        assert id_locs
 
    def test_aria_strategy(self, engine, soup):
        password_tag = soup.find("input", {"id": "password"})
        locs = engine.generate_all(password_tag, soup)
        vals = [l.value for l in locs]
        assert any("aria-label" in v for v in vals)
 
    def test_cy_strategy(self, engine, button_tag, soup):
        locs = engine.generate_all(button_tag, soup)
        vals = [l.value for l in locs]
        assert any("data-cy" in v for v in vals)
 
    def test_text_strategy(self, engine, button_tag, soup):
        locs = engine.generate_all(button_tag, soup)
        vals = [l.value for l in locs]
        assert any("Login" in v for v in vals)
 
    def test_css_id_strategy(self, engine, username_tag, soup):
        locs = engine.generate_all(username_tag, soup)
        css_locs = [l for l in locs
                    if l.locator_type.value == "css" and l.value.startswith("#")]
        assert css_locs
 
    def test_dynamic_id_excluded(self, engine, dynamic_tag, soup):
        """item-123456 is dynamic — should NOT produce id-based locator."""
        locs = engine.generate_all(dynamic_tag, soup)
        id_vals = [l.value for l in locs if "id-based" in l.strategy]
        # Either no id-based locator, or none with the dynamic value
        for v in id_vals:
            assert "123456" not in v
 
    def test_react_id_excluded(self, engine, react_tag, soup):
        """:r0: is a React dynamic ID — should not be used."""
        locs = engine.generate_all(react_tag, soup)
        for loc in locs:
            if "id-based" in loc.strategy:
                assert ":r0:" not in loc.value
 
    def test_absolute_xpath_generated(self, engine, username_tag, soup):
        locs = engine.generate_all(username_tag, soup)
        absolute = [l for l in locs if l.strategy == "absolute-xpath"]
        assert absolute
        assert absolute[0].score <= 0.35
 
    def test_deduplicated_results(self, engine, username_tag, soup):
        locs = engine.generate_all(username_tag, soup)
        values = [l.value for l in locs]
        assert len(values) == len(set(values))
 
    def test_sorted_by_score(self, engine, username_tag, soup):
        locs = engine.generate_all(username_tag, soup)
        scores = [l.score for l in locs]
        assert scores == sorted(scores, reverse=True)
 
    def test_is_dynamic_id_long_number(self, engine):
        assert engine._is_dynamic_id("item-123456") is True
 
    def test_is_dynamic_id_hex(self, engine):
        assert engine._is_dynamic_id("a3f9bc12ef") is True
 
    def test_is_dynamic_id_react(self, engine):
        assert engine._is_dynamic_id(":r0:") is True
 
    def test_is_dynamic_id_static(self, engine):
        assert engine._is_dynamic_id("login-button") is False
        assert engine._is_dynamic_id("username") is False
 
    def test_is_dynamic_class_hashed(self, engine):
        assert engine._is_dynamic_class("button_abc12") is True
 
    def test_is_dynamic_class_stable(self, engine):
        assert engine._is_dynamic_class("btn-primary") is False
 
    def test_css_escape(self, engine):
        escaped = engine._css_escape("id.with.dots")
        assert "\\." in escaped
 
 
# ══════════════════════════════════════════════════════════════
#  TASK 4.4 — recommender.py tests
# ══════════════════════════════════════════════════════════════
 
class TestRecommender:
    from backend.models.schemas import Locator, LocatorType, ReliabilityScore
 
    def _make_locator(self, locator_type, value, strategy, score):
        from backend.models.schemas import Locator, LocatorType, ReliabilityScore
        return Locator(
            locator_type  = LocatorType(locator_type),
            value         = value,
            strategy      = strategy,
            reliability   = ReliabilityScore.MEDIUM,
            score         = score,
        )
 
    def test_rank_returns_sorted(self, recommender):
        locs = [
            self._make_locator("xpath", '//*[@id="x"]',             "id-based",      0.5),
            self._make_locator("xpath", '//*[@data-testid="x"]',    "test-id-based", 0.9),
            self._make_locator("xpath", '/html/body/div/input',      "absolute-xpath",0.2),
        ]
        ranked = recommender.rank(locs)
        scores = [l.score for l in ranked]
        assert scores == sorted(scores, reverse=True)
 
    def test_testid_gets_bonus(self, recommender):
        loc = self._make_locator(
            "xpath", '//*[@data-testid="user"]', "test-id-based", 0.9
        )
        ranked = recommender.rank([loc])
        assert ranked[0].score > 0.9
 
    def test_deep_xpath_gets_penalty(self, recommender):
        loc = self._make_locator(
            "xpath",
            "/html/body/div[1]/main/section/div[2]/form/input",
            "absolute-xpath", 0.5,
        )
        ranked = recommender.rank([loc])
        assert ranked[0].score < 0.5
 
    def test_dynamic_number_penalty(self, recommender):
        loc = self._make_locator(
            "css", '#item-12345', "id-based", 0.9
        )
        ranked = recommender.rank([loc])
        assert ranked[0].score < 0.9
 
    def test_pick_best_returns_highest(self, recommender):
        locs = [
            self._make_locator("css",   "#id",              "id-based",      0.8),
            self._make_locator("xpath", '//*[@id="id"]',    "id-based",      0.85),
            self._make_locator("xpath", '/html/body/input', "absolute-xpath",0.25),
        ]
        best = recommender.pick_best(locs)
        scores = [l.score for l in locs]
        assert best.score == recommender.rank(locs)[0].score
 
    def test_score_clamped_0_1(self, recommender):
        loc = self._make_locator("xpath", '//*[@data-testid="x"]', "test-id-based", 1.0)
        ranked = recommender.rank([loc])
        assert 0.0 <= ranked[0].score <= 1.0
 
    def test_high_reliability_classification(self, recommender):
        loc = self._make_locator("xpath", '//*[@data-testid="x"]', "test-id-based", 0.9)
        ranked = recommender.rank([loc])
        assert ranked[0].reliability.value == "high"
 
    def test_low_reliability_classification(self, recommender):
        loc = self._make_locator("xpath", "/html/body/div/input", "absolute-xpath", 0.3)
        ranked = recommender.rank([loc])
        assert ranked[0].reliability.value in ("low", "medium")
 
 
# ══════════════════════════════════════════════════════════════
#  TASK 4.5 — FastAPI API endpoint tests
# ══════════════════════════════════════════════════════════════
 
class TestAPI:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)
 
    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
 
    def test_analyze_html_input(self, client):
        resp = client.post("/analyze/", json={
            "input_type": "html",
            "content": SAMPLE_HTML,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_elements"] > 0
        assert "elements" in data
 
    def test_analyze_html_filter_tag(self, client):
        resp = client.post("/analyze/", json={
            "input_type": "html",
            "content":    SAMPLE_HTML,
            "filter_tag": "input",
        })
        assert resp.status_code == 200
        data = resp.json()
        for el in data["elements"]:
            assert el["tag"] == "input"
 
    def test_analyze_element_has_best_locator(self, client):
        resp = client.post("/analyze/", json={
            "input_type": "html",
            "content":    SAMPLE_HTML,
        })
        data = resp.json()
        el   = data["elements"][0]
        assert "best_locator" in el
        assert "value"        in el["best_locator"]
        assert "score"        in el["best_locator"]
        assert "reliability"  in el["best_locator"]
 
    def test_analyze_locator_score_in_range(self, client):
        resp = client.post("/analyze/", json={
            "input_type": "html",
            "content":    SAMPLE_HTML,
        })
        for el in resp.json()["elements"]:
            assert 0.0 <= el["best_locator"]["score"] <= 1.0
 
    def test_analyze_invalid_input_type(self, client):
        resp = client.post("/analyze/", json={
            "input_type": "invalid",
            "content":    "test",
        })
        assert resp.status_code == 422
 
    def test_analyze_empty_content(self, client):
        resp = client.post("/analyze/", json={
            "input_type": "html",
            "content":    "",
        })
        # Should succeed but with 0 elements
        assert resp.status_code == 200
 
    def test_generate_code_endpoint(self, client):
        resp = client.post("/validate/generate-code", json={
            "url":           "https://example.com",
            "locator_type":  "xpath",
            "locator_value": '//*[@id="username"]',
        })
        assert resp.status_code == 200
        code = resp.json()["code"]
        assert "By.XPATH" in code
        assert "username" in code
        assert "WebDriverWait" in code
 
    def test_generate_playwright_js_code(self, client):
        resp = client.post("/validate/generate-code", json={
            "url":           "https://example.com",
            "locator_type":  "xpath",
            "locator_value": '//*[@id="username"]',
            "target":        "playwright",
            "language":      "js",
        })
        assert resp.status_code == 200
        code = resp.json()["code"]
        assert "require(\"playwright\")" in code
        assert "page.locator(\"xpath=//*[@id=\"username\"]\")" in code
 
    def test_generate_cypress_code(self, client):
        resp = client.post("/validate/generate-code", json={
            "url":           "https://example.com",
            "locator_type":  "css",
            "locator_value": ".btn-primary",
            "target":        "cypress",
            "language":      "js",
        })
        assert resp.status_code == 200
        code = resp.json()["code"]
        assert "cy.get(\".btn-primary\")" in code
        assert "cy.visit(\"https://your-target-url.com\")" in code
 
    def test_export_pom_endpoint(self, client):
        # First analyze to get elements
        analyze = client.post("/analyze/", json={
            "input_type": "html",
            "content":    SAMPLE_HTML,
        })
        elements = analyze.json()["elements"]
        resp = client.post("/export/pom", json={"elements": elements})
        assert resp.status_code == 200
        code = resp.json()["code"]
        assert "class PageObjects" in code
        assert "WebDriverWait" in code
 
    def test_get_url_convenience_endpoint(self, client):
        with patch("backend.core.parser.HTMLParser.fetch_url",
                   new_callable=AsyncMock,
                   return_value=(SAMPLE_HTML, "https://example.com")):
            resp = client.get("/analyze/url?url=https://example.com")
        assert resp.status_code == 200
 
 
# ══════════════════════════════════════════════════════════════
#  TASK 4.6 — helpers.py (POM generator) tests
# ══════════════════════════════════════════════════════════════
 
class TestPOMGenerator:
    @pytest.fixture
    def sample_elements(self):
        from backend.models.schemas import WebElement, Locator, LocatorType, ReliabilityScore
        def make_el(idx, tag, attrs, loc_val, strategy="test-id-based"):
            loc = Locator(
                locator_type=LocatorType.XPATH,
                value=loc_val,
                strategy=strategy,
                reliability=ReliabilityScore.HIGH,
                score=0.95,
            )
            return WebElement(
                tag=tag, text="", attributes=attrs,
                locators=[loc], best_locator=loc, element_index=idx,
            )
        return [
            make_el(0, "input",  {"data-testid": "username", "type": "text"},   '//*[@data-testid="username"]'),
            make_el(1, "input",  {"data-testid": "password", "type": "password"},'//*[@data-testid="password"]'),
            make_el(2, "button", {"data-cy": "submit"},                          '//*[@data-cy="submit"]'),
        ]
 
    def test_pom_generates_class(self, sample_elements):
        from backend.utils.helpers import export_page_object
        code = export_page_object(sample_elements)
        assert "class PageObjects" in code
 
    def test_pom_has_get_methods(self, sample_elements):
        from backend.utils.helpers import export_page_object
        code = export_page_object(sample_elements)
        assert "def get_username" in code
        assert "def get_password" in code
 
    def test_pom_has_type_methods_for_inputs(self, sample_elements):
        from backend.utils.helpers import export_page_object
        code = export_page_object(sample_elements)
        assert "def type_username" in code
        assert "def type_password" in code
 
    def test_pom_has_click_methods(self, sample_elements):
        from backend.utils.helpers import export_page_object
        code = export_page_object(sample_elements)
        assert "def click_" in code
 
    def test_pom_has_locator_constants(self, sample_elements):
        from backend.utils.helpers import export_page_object
        code = export_page_object(sample_elements)
        assert "By.XPATH" in code
        assert "_LOCATOR" in code
 
    def test_pom_custom_class_name(self, sample_elements):
        from backend.utils.helpers import export_page_object
        code = export_page_object(sample_elements, class_name="LoginPage")
        assert "class LoginPage" in code
 
    def test_pom_custom_base_url(self, sample_elements):
        from backend.utils.helpers import export_page_object
        code = export_page_object(sample_elements, base_url="https://saucedemo.com")
        assert "def open" in code
        assert "saucedemo.com" in code
 
    def test_pom_no_duplicate_methods(self, sample_elements):
        from backend.utils.helpers import export_page_object
        code  = export_page_object(sample_elements)
        lines = [l.strip() for l in code.split("\n") if l.strip().startswith("def get_")]
        assert len(lines) == len(set(lines))