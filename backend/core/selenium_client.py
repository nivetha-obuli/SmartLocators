import json
import os
import pathlib
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


def generate_playwright_code(
    locator_type: LocatorType,
    locator_value: str,
    language: CodeGenerationLanguage,
) -> str:
    selector = _playwright_selector(locator_type, locator_value)

    if language == CodeGenerationLanguage.TS:
        return f'''import {{ chromium }} from "playwright";

(async () => {{
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto("https://your-target-url.com");

  const element = page.locator("{selector}").first();
  await element.click();

  await browser.close();
}})();
'''

    if language == CodeGenerationLanguage.JS:
        return f'''const {{ chromium }} = require("playwright");

(async () => {{
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto("https://your-target-url.com");

  const element = page.locator("{selector}").first();
  await element.click();

  await browser.close();
}})();
'''

    return f'''from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page()
    page.goto("https://your-target-url.com")

    element = page.locator("{selector}").first
    element.click()

    browser.close()
'''


def generate_cypress_code(
    locator_type: LocatorType,
    locator_value: str,
    language: CodeGenerationLanguage,
) -> str:
    if locator_type == LocatorType.XPATH:
        locator_call = f'cy.xpath("{locator_value}")'
    else:
        locator_call = f'cy.get("{locator_value}")'

    if language == CodeGenerationLanguage.TS:
        return f'''describe("SmartLocator example", () => {{
  it("locates and clicks the element", () => {{
    cy.visit("https://your-target-url.com");
    {locator_call}.first().click();
  }});
}});
'''

    return f'''describe("SmartLocator example", () => {{
  it("locates and clicks the element", () => {{
    cy.visit("https://your-target-url.com");
    {locator_call}.first().click();
  }});
}});
'''
