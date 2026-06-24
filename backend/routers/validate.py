from fastapi import APIRouter, HTTPException
from backend.models.schemas import (
    CodeGenerationLanguage,
    CodeGenerationRequest,
    CodeGenerationTarget,
    ValidateRequest,
    ValidateResponse,
)
from backend.core.selenium_client import (
    SeleniumValidator,
    generate_cypress_code,
    generate_playwright_code,
    generate_selenium_code,
)
 
router    = APIRouter(prefix="/validate", tags=["validate"])
validator = SeleniumValidator()
 
 
@router.post("/", response_model=ValidateResponse)
def validate_locator(request: ValidateRequest):
    """
    Live-validate a locator against a real URL using Selenium
    headless Chrome.  Returns whether the locator finds exactly
    one unique element on the page.
    """
    try:
        return validator.validate(
            request.url,
            request.locator_type,
            request.locator_value,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.post("/generate-code")
def generate_code(request: CodeGenerationRequest):
    """Generate ready-to-use locator code for Selenium, Playwright, or Cypress."""
    try:
        if request.target == CodeGenerationTarget.PLAYWRIGHT:
            code = generate_playwright_code(
                request.locator_type,
                request.locator_value,
                request.language,
            )
        elif request.target == CodeGenerationTarget.CYPRESS:
            code = generate_cypress_code(
                request.locator_type,
                request.locator_value,
                request.language,
            )
        else:
            code = generate_selenium_code(
                request.locator_type,
                request.locator_value,
            )
        return {"code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code generation error: {str(e)}")