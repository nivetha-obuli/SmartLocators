import json
import os
import pathlib
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    InvalidSelectorException,
    TimeoutException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager
from backend.models.schemas import CodeGenerationLanguage, LocatorType, ValidateResponse
 
 
# ──────────────────────────────────────────────────────────────────────────────
#  Driver factory
# ──────────────────────────────────────────────────────────────
def _build_driver() -> webdriver.Chrome:
    """Build a headless Chrome WebDriver instance."""
    opts = Options()
    headless = os.getenv("SELENIUM_HEADLESS", "True").lower() == "true"
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--user-agent=Mozilla/5.0 SmartLocatorBot/1.0")
    # Suppress Chrome logs
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
 
    driver_path = ChromeDriverManager().install()
    driver_path = pathlib.Path(driver_path)
    if not driver_path.name.lower().endswith("chromedriver.exe") and driver_path.is_file():
        parent = driver_path.parent
        exe_candidate = parent / "chromedriver.exe"
        if exe_candidate.exists():
            driver_path = exe_candidate
        else:
            # Fallback to any executable in the same directory
            exe_files = [p for p in parent.iterdir() if p.is_file() and p.suffix.lower() == ".exe"]
            if exe_files:
                driver_path = exe_files[0]

    service = Service(str(driver_path))
    return webdriver.Chrome(service=service, options=opts)
 
 
# ──────────────────────────────────────────────────────────────
#  Selenium Validator
# ──────────────────────────────────────────────────────────────
BY_MAP = {
    LocatorType.XPATH: By.XPATH,
    LocatorType.CSS:   By.CSS_SELECTOR,
}
 
 
class SeleniumValidator:
    """
    Opens a real headless Chrome session, navigates to the URL,
    and checks if the given locator resolves to exactly one element.
    """
 
    def validate(
        self,
        url: str,
        locator_type: LocatorType,
        locator_value: str,
    ) -> ValidateResponse:
        timeout = int(os.getenv("SELENIUM_TIMEOUT", "15"))
        by      = BY_MAP[locator_type]
        driver  = None
 
        try:
            driver = _build_driver()
            driver.set_page_load_timeout(timeout)
            driver.get(url)
 
            # Wait for page body to be present
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
 
            # Small extra wait for JS-heavy pages
            time.sleep(1.5)
 
            elements = driver.find_elements(by, locator_value)
            count    = len(elements)
 
            if count == 1:
                # Check visibility
                visible = elements[0].is_displayed()
                msg = (
                    "✅ Unique & visible element found — ideal for automation"
                    if visible
                    else "✅ Unique element found (not currently visible)"
                )
                return ValidateResponse(
                    locator_type   = locator_type,
                    locator_value  = locator_value,
                    is_valid       = True,
                    elements_found = 1,
                    is_unique      = True,
                    message        = msg,
                )
            elif count > 1:
                return ValidateResponse(
                    locator_type   = locator_type,
                    locator_value  = locator_value,
                    is_valid       = True,
                    elements_found = count,
                    is_unique      = False,
                    message        = (
                        f"⚠️  {count} elements matched — locator is NOT unique. "
                        "Selenium will interact with the first one only."
                    ),
                )
            else:
                # Try waiting for element (might load late)
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((by, locator_value))
                    )
                    elements = driver.find_elements(by, locator_value)
                    if elements:
                        return ValidateResponse(
                            locator_type   = locator_type,
                            locator_value  = locator_value,
                            is_valid       = True,
                            elements_found = len(elements),
                            is_unique      = len(elements) == 1,
                            message        = f"✅ Found after wait — {len(elements)} element(s)",
                        )
                except TimeoutException:
                    pass
 
                return ValidateResponse(
                    locator_type   = locator_type,
                    locator_value  = locator_value,
                    is_valid       = False,
                    elements_found = 0,
                    is_unique      = False,
                    message        = "❌ No element found — locator does not match anything on this page",
                )
 
        except InvalidSelectorException as e:
            return ValidateResponse(
                locator_type   = locator_type,
                locator_value  = locator_value,
                is_valid       = False,
                elements_found = 0,
                is_unique      = False,
                message        = f"❌ Invalid selector syntax: {str(e)[:120]}",
            )
 
        except WebDriverException as e:
            return ValidateResponse(
                locator_type   = locator_type,
                locator_value  = locator_value,
                is_valid       = False,
                elements_found = 0,
                is_unique      = False,
                message        = f"❌ Browser error: {str(e)[:120]}",
            )
 
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
 
 
# ──────────────────────────────────────────────────────────────
#  Python code snippet generator
# ──────────────────────────────────────────────────────────────
def generate_selenium_code(locator_type: LocatorType, locator_value: str) -> str:
    by_str = (
        "By.XPATH"
        if locator_type == LocatorType.XPATH
        else "By.CSS_SELECTOR"
    )
    return f'''from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
 
# ── Setup ──────────────────────────────────────
driver = webdriver.Chrome()
wait   = WebDriverWait(driver, 10)
 
# ── Navigate ───────────────────────────────────
driver.get("https://your-target-url.com")
 
# ── Locate element ─────────────────────────────
# Strategy: {locator_type.value.upper()} · Auto-generated by SmartLocator
element = wait.until(
    EC.presence_of_element_located(
        ({by_str}, "{locator_value}")
    )
)
 
# ── Interact ───────────────────────────────────
element.click()           # click the element
# element.send_keys("text")  # type into an input
# text = element.text        # read element text
 
# ── Cleanup ────────────────────────────────────
driver.quit()
'''


def _playwright_selector(locator_type: LocatorType, locator_value: str) -> str:
    return f"xpath={locator_value}" if locator_type == LocatorType.XPATH else locator_value


def _playwright_getby_helper(attr: str, value: str):
    if attr in ("data-testid", "data-test", "data-cy", "data-qa", "data-automation-id"):
        return "test_id", value
    if attr == "role":
        return "role", value
    if attr == "placeholder":
        return "placeholder", value
    if attr in ("aria-label", "aria-labelledby", "label"):
        return "label", value
    if attr == "alt":
        return "alt", value
    if attr == "title":
        return "title", value
    return None


def _playwright_getby_details(locator_type: LocatorType, locator_value: str):
    if locator_type == LocatorType.CSS:
        match = re.search(r'\[([A-Za-z0-9\-_]+)=["\']([^"\']+)["\']\]', locator_value)
        if match:
            return _playwright_getby_helper(match.group(1), match.group(2))
        return None

    # XPath: try attribute-based getBy mappings first
    attr_match = re.search(r'@([A-Za-z0-9\-_]+)=["\']([^"\']+)["\']', locator_value)
    if attr_match:
        helper = _playwright_getby_helper(attr_match.group(1), attr_match.group(2))
        if helper:
            return helper

    # XPath by text patterns
    exact_text = re.search(r'text\(\)\s*=\s*["\'](.+?)["\']', locator_value)
    if exact_text:
        return "text", exact_text.group(1)

    contains_text = re.search(r'contains\(\s*text\(\)\s*,\s*["\'](.+?)["\']\s*\)', locator_value)
    if contains_text:
        return "text", contains_text.group(1)

    return None


def _playwright_locator_expression(
    locator_type: LocatorType,
    locator_value: str,
    language: CodeGenerationLanguage,
) -> str:
    getby = _playwright_getby_details(locator_type, locator_value)
    if getby:
        method_key, value = getby
        if language == CodeGenerationLanguage.PYTHON:
            method_names = {
                "test_id": "get_by_test_id",
                "role": "get_by_role",
                "placeholder": "get_by_placeholder",
                "text": "get_by_text",
                "label": "get_by_label",
                "alt": "get_by_alt_text",
                "title": "get_by_title",
            }
        else:
            method_names = {
                "test_id": "getByTestId",
                "role": "getByRole",
                "placeholder": "getByPlaceholder",
                "text": "getByText",
                "label": "getByLabel",
                "alt": "getByAltText",
                "title": "getByTitle",
            }
        method = method_names.get(method_key)
        if method:
            return f'page.{method}({json.dumps(value)})'

    selector = _playwright_selector(locator_type, locator_value)
    return f'page.locator({json.dumps(selector)})'


def _playwright_needs_first(locator_expr: str) -> bool:
    return locator_expr.startswith("page.locator(")


def generate_playwright_code(
    locator_type: LocatorType,
    locator_value: str,
    language: CodeGenerationLanguage,
) -> str:
    locator_expr = _playwright_locator_expression(locator_type, locator_value, language)

    if language == CodeGenerationLanguage.TS:
        first_call = ".first()" if _playwright_needs_first(locator_expr) else ""
        return f'''import {{ chromium }} from "playwright";

(async () => {{
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto("https://your-target-url.com");

  const element = {locator_expr}{first_call};
  await element.click();

  await browser.close();
}})();
'''

    if language == CodeGenerationLanguage.JS:
        first_call = ".first()" if _playwright_needs_first(locator_expr) else ""
        return f'''const {{ chromium }} = require("playwright");

(async () => {{
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto("https://your-target-url.com");

  const element = {locator_expr}{first_call};
  await element.click();

  await browser.close();
}})();
'''

    first_call = ".first" if _playwright_needs_first(locator_expr) else ""
    return f'''from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page()
    page.goto("https://your-target-url.com")

    element = {locator_expr}{first_call}
    element.click()

    browser.close()
'''



def _cypress_getby_helper(attr: str, value: str) -> str | None:
    supported_attrs = {
        "data-testid",
        "data-test",
        "data-cy",
        "data-qa",
        "data-automation-id",
        "placeholder",
        "role",
        "alt",
        "title",
        "aria-label",
        "aria-labelledby",
        "label",
        "id",
        "name",
    }
    if attr in supported_attrs:
        return f"cy.get([{attr}={json.dumps(value)}])"
    return None


def _cypress_locator_expression(locator_type: LocatorType, locator_value: str) -> str:
    if locator_type == LocatorType.CSS:
        match = re.search(r'\[([A-Za-z0-9\-_]+)=\s*["\']([^"\']+)["\']\]', locator_value)
        if match:
            helper = _cypress_getby_helper(match.group(1), match.group(2))
            if helper:
                return helper
        return f'cy.get("{locator_value}")'

    if locator_type == LocatorType.XPATH:
        attr_match = re.search(r'@([A-Za-z0-9\-_]+)=\s*["\']([^"\']+)["\']', locator_value)
        if attr_match:
            helper = _cypress_getby_helper(attr_match.group(1), attr_match.group(2))
            if helper:
                return helper

        attr_contains = re.search(
            r'contains\(\s*@([A-Za-z0-9\-_]+)\s*,\s*["\']([^"\']+)["\']\s*\)',
            locator_value,
        )
        if attr_contains:
            helper = _cypress_getby_helper(attr_contains.group(1), attr_contains.group(2))
            if helper:
                return helper

        exact_text = re.search(r'text\(\)\s*=\s*["\'](.+?)["\']', locator_value)
        if exact_text:
            return f'cy.contains({json.dumps(exact_text.group(1))})'

        contains_text = re.search(r'contains\(\s*text\(\)\s*,\s*["\'](.+?)["\']\s*\)', locator_value)
        if contains_text:
            return f'cy.contains({json.dumps(contains_text.group(1))})'

        return f'cy.xpath("{locator_value}")'

    return f'cy.get("{locator_value}")'


def _cypress_needs_first(locator_call: str) -> bool:
    if locator_call.startswith("cy.get(["):
        return False
    if locator_call.startswith("cy.contains("):
        return False
    return locator_call.startswith("cy.get(") or locator_call.startswith("cy.xpath(")


def generate_cypress_code(
    locator_type: LocatorType,
    locator_value: str,
    language: CodeGenerationLanguage,
) -> str:
    locator_call = _cypress_locator_expression(locator_type, locator_value)
    first_suffix = ".first()" if _cypress_needs_first(locator_call) else ""

    if language == CodeGenerationLanguage.TS:
        return f'''describe("SmartLocator example", () => {{
  it("locates and clicks the element", () => {{
    cy.visit("https://your-target-url.com");
    {locator_call}{first_suffix}.click();
  }});
}});
'''

    return f'''describe("SmartLocator example", () => {{
  it("locates and clicks the element", () => {{
    cy.visit("https://your-target-url.com");
    {locator_call}{first_suffix}.click();
  }});
}});
'''
