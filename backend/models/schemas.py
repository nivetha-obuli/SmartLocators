from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from enum import Enum

class InputType(str, Enum):
    URL = "url"
    HTML = "html"

class LocatorType(str, Enum):
    XPATH = "xpath"
    CSS = "css"

class ReliabilityScore(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class AnalyzeRequest(BaseModel):
    input_type: InputType
    content: str                        # URL string or raw HTML
    filter_tag: Optional[str] = None    # e.g., "input", "button"
    filter_attribute: Optional[str] = None
    limit: int = 100                    # Max elements per request
    offset: int = 0                     # Skip first N elements
    search_query: Optional[str] = None  # Text search over tag/text/attributes/locators
    reliability_filter: Optional[ReliabilityScore] = None

class Locator(BaseModel):
    locator_type: LocatorType
    value: str
    strategy: str                       # e.g., "id-based", "text-based"
    reliability: ReliabilityScore
    score: float                        # 0.0 - 1.0
    notes: Optional[str] = None

class WebElement(BaseModel):
    tag: str
    text: Optional[str]
    attributes: dict
    locators: List[Locator]
    best_locator: Locator
    element_index: int

class AnalyzeResponse(BaseModel):
    url: Optional[str]
    total_elements: int                 # Elements in this batch
    total_available: int                # Total elements on page
    offset: int                         # Current offset
    elements: List[WebElement]
    page_title: Optional[str]

class CodeGenerationTarget(str, Enum):
    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"
    CYPRESS = "cypress"

class CodeGenerationLanguage(str, Enum):
    PYTHON = "python"
    JS = "js"
    TS = "ts"

class ValidateRequest(BaseModel):
    url: str
    locator_type: LocatorType
    locator_value: str

class CodeGenerationRequest(BaseModel):
    url: str
    locator_type: LocatorType
    locator_value: str
    target: CodeGenerationTarget = CodeGenerationTarget.SELENIUM
    language: CodeGenerationLanguage = CodeGenerationLanguage.PYTHON

class ValidateResponse(BaseModel):
    locator_type: LocatorType
    locator_value: str
    is_valid: bool
    elements_found: int
    is_unique: bool
    message: str