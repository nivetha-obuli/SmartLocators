import pytest
from fastapi.testclient import TestClient
from backend.main import app
 
client = TestClient(app)
 
 
# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
 
def analyze(url: str = None, html: str = None, tag: str = None):
    body = {"filter_tag": tag} if tag else {}
    if url:
        body.update({"input_type": "url", "content": url})
    else:
        body.update({"input_type": "html", "content": html})
    return client.post("/analyze/", json=body)
 
 
def assert_high_locator(resp):
    """At least one element should have a HIGH reliability locator."""
    elements = resp.json()["elements"]
    assert any(el["best_locator"]["reliability"] == "high" for el in elements), \
        "Expected at least one HIGH reliability locator"
 
 
# ══════════════════════════════════════════════════════════════
#  TEST 1 — Static HTML (offline, always runs)
# ══════════════════════════════════════════════════════════════
 
class TestStaticHTML:
    LOGIN_HTML = """
    <html><body>
      <form>
        <input data-testid="email"    type="email"    name="email"    placeholder="Email"/>
        <input data-testid="password" type="password" name="password" placeholder="Password"/>
        <button data-cy="login-btn" type="submit">Sign In</button>
        <a href="/signup" aria-label="Register link">Create account</a>
      </form>
    </body></html>
    """
 
    def test_login_form_detects_all_elements(self):
        resp = analyze(html=self.LOGIN_HTML)
        assert resp.status_code == 200
        assert resp.json()["total_elements"] >= 4
 
    def test_testid_locators_found(self):
        resp = analyze(html=self.LOGIN_HTML)
        elements = resp.json()["elements"]
        testid_locs = [
            el for el in elements
            if "data-testid" in el["best_locator"]["value"] or
               "data-cy"     in el["best_locator"]["value"]
        ]
        assert len(testid_locs) >= 2
 
    def test_all_best_locators_valid(self):
        resp = analyze(html=self.LOGIN_HTML)
        for el in resp.json()["elements"]:
            assert el["best_locator"]["value"] != ""
            assert 0.0 <= el["best_locator"]["score"] <= 1.0
 
    def test_input_filter(self):
        resp = analyze(html=self.LOGIN_HTML, tag="input")
        for el in resp.json()["elements"]:
            assert el["tag"] == "input"
 
    def test_page_title_none_for_plain_html(self):
        resp = analyze(html="<html><body><input id='x'/></body></html>")
        assert resp.json()["page_title"] is None
 
 
# ══════════════════════════════════════════════════════════════
#  TEST 2 — React SPA patterns (simulated offline)
# ══════════════════════════════════════════════════════════════
 
class TestReactSPAPatterns:
    REACT_HTML = """
    <html><body>
      <div id="root">
        <input id=":r0:" type="text" placeholder="React dynamic ID"/>
        <button id=":r1:" data-testid="submit-btn">Submit</button>
        <div class="module_abc12 active">Hashed CSS module class</div>
        <span data-reactid="item-999999">Dynamic reactid</span>
        <input aria-label="Search box" type="search"/>
        <button aria-label="Close dialog" type="button">✕</button>
      </div>
    </body></html>
    """
 
    def test_react_dynamic_ids_not_promoted(self):
        resp  = analyze(html=self.REACT_HTML)
        elems = resp.json()["elements"]
        for el in elems:
            best = el["best_locator"]["value"]
            # :r0: and :r1: should not appear in HIGH reliability locators
            if el["best_locator"]["reliability"] == "high":
                assert ":r0:" not in best
                assert ":r1:" not in best
 
    def test_testid_still_preferred(self):
        resp  = analyze(html=self.REACT_HTML)
        elems = resp.json()["elements"]
        btn   = next((e for e in elems if e["tag"] == "button"
                      and "submit" in str(e["attributes"])), None)
        if btn:
            assert "data-testid" in btn["best_locator"]["value"]
            assert btn["best_locator"]["reliability"] == "high"
 
    def test_aria_label_used_when_no_testid(self):
        resp  = analyze(html=self.REACT_HTML)
        elems = resp.json()["elements"]
        search = next((e for e in elems
                       if e["attributes"].get("aria-label") == "Search box"), None)
        if search:
            assert "aria-label" in search["best_locator"]["value"]
 
    def test_hashed_css_class_not_in_high_locator(self):
        resp  = analyze(html=self.REACT_HTML)
        for el in resp.json()["elements"]:
            if el["best_locator"]["reliability"] == "high":
                assert "_abc12" not in el["best_locator"]["value"]
 
 
# ══════════════════════════════════════════════════════════════
#  TEST 3 — Complex real-world HTML patterns
# ══════════════════════════════════════════════════════════════
 
class TestComplexHTMLPatterns:
    COMPLEX_HTML = """
    <html><body>
      <!-- Nested form with various element types -->
      <form id="checkout-form" data-testid="checkout">
        <fieldset>
          <input type="text"     id="first-name"  name="first_name"  value=""/>
          <input type="text"     id="last-name"   name="last_name"   value=""/>
          <input type="email"    id="email"        name="email"       value=""/>
          <input type="tel"      id="phone"        name="phone"       value=""/>
          <select id="country"   name="country">
            <option value="in">India</option>
            <option value="us">United States</option>
          </select>
          <textarea id="address" name="address" rows="3"></textarea>
          <input type="checkbox" id="agree" name="agree"/>
          <label for="agree">I agree to terms</label>
        </fieldset>
        <button type="submit" id="place-order" data-testid="place-order-btn">
          Place Order
        </button>
      </form>
      <table id="order-summary">
        <thead><tr><th>Item</th><th>Price</th></tr></thead>
        <tbody>
          <tr><td id="item-name-1">Product A</td><td id="price-1">$99</td></tr>
        </tbody>
      </table>
    </body></html>
    """
 
    def test_all_form_inputs_detected(self):
        resp = analyze(html=self.COMPLEX_HTML, tag="input")
        assert resp.json()["total_elements"] >= 5
 
    def test_select_detected(self):
        resp  = analyze(html=self.COMPLEX_HTML, tag="select")
        elems = resp.json()["elements"]
        assert any(e["tag"] == "select" for e in elems)
 
    def test_textarea_detected(self):
        resp  = analyze(html=self.COMPLEX_HTML, tag="textarea")
        elems = resp.json()["elements"]
        assert any(e["tag"] == "textarea" for e in elems)
 
    def test_each_element_has_locators(self):
        resp  = analyze(html=self.COMPLEX_HTML)
        for el in resp.json()["elements"]:
            assert len(el["locators"]) >= 1
 
    def test_scores_decrease_in_list(self):
        resp  = analyze(html=self.COMPLEX_HTML)
        for el in resp.json()["elements"]:
            scores = [l["score"] for l in el["locators"]]
            assert scores == sorted(scores, reverse=True), \
                f"Locators for <{el['tag']}> are not sorted by score"
 
    def test_submit_button_has_testid(self):
        resp  = analyze(html=self.COMPLEX_HTML)
        elems = resp.json()["elements"]
        submit = next((e for e in elems
                       if e["attributes"].get("id") == "place-order"), None)
        if submit:
            assert "data-testid" in submit["best_locator"]["value"]
            assert submit["best_locator"]["score"] >= 0.95
 
 
# ══════════════════════════════════════════════════════════════
#  TEST 4 — POM generation integration
# ══════════════════════════════════════════════════════════════
 
class TestPOMIntegration:
    def test_pom_generated_from_analyze_output(self):
        resp = analyze(html="""
        <html><body>
          <input data-testid="username" type="text"/>
          <input data-testid="password" type="password"/>
          <button data-cy="submit">Login</button>
        </body></html>
        """)
        elements = resp.json()["elements"]
        pom_resp = client.post("/export/pom", json={
            "elements":   elements,
            "class_name": "LoginPage",
            "base_url":   "https://myapp.com/login",
        })
        assert pom_resp.status_code == 200
        code = pom_resp.json()["code"]
        assert "class LoginPage" in code
        assert "By.XPATH" in code
        assert "myapp.com" in code
        assert "def get_" in code
 
    def test_pom_code_is_valid_python(self):
        resp     = analyze(html="<html><body><input id='x' name='x'/></body></html>")
        elements = resp.json()["elements"]
        pom_resp = client.post("/export/pom", json={"elements": elements})
        code     = pom_resp.json()["code"]
        # Should be parseable Python
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated POM code has syntax error: {e}")
 
 
# ══════════════════════════════════════════════════════════════
#  TEST 5 — Live URL tests (marked as integration, skip if offline)
#  Run with:  pytest tests/test_integration.py -m live -v
# ══════════════════════════════════════════════════════════════
 
@pytest.mark.live
class TestLiveURLs:
    """
    These tests hit real URLs — they require an internet connection.
    They are skipped in CI unless you run with --run-live flag.
 
    Mark them:  pytest -m live
    """
 
    @pytest.fixture(autouse=True)
    def check_live(self, request):
        if not request.config.getoption("--run-live", default=False):
            pytest.skip("Live tests skipped — pass --run-live to enable")
 
    def test_saucedemo_login(self):
        resp = analyze(url="https://www.saucedemo.com", tag="input")
        assert resp.status_code == 200
        elems = resp.json()["elements"]
        assert len(elems) >= 2
        # Should have data-test attributes
        assert any("data-test" in e["best_locator"]["value"] for e in elems)
 
    def test_github_login(self):
        resp = analyze(url="https://github.com/login", tag="input")
        assert resp.status_code == 200
        assert resp.json()["total_elements"] >= 2
 
    def test_wikipedia_search(self):
        resp = analyze(url="https://www.wikipedia.org", tag="input")
        assert resp.status_code == 200
        assert resp.json()["total_elements"] >= 1
 
 
# ══════════════════════════════════════════════════════════════
#  pytest CLI option for --run-live flag
# ══════════════════════════════════════════════════════════════
 
def pytest_addoption(parser):
    try:
        parser.addoption("--run-live", action="store_true", default=False,
                         help="Run tests that hit real URLs")
    except ValueError:
        pass  # already added