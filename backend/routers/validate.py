from fastapi import APIRouter, HTTPException
from backend.models.schemas import ValidateRequest, ValidateResponse
from backend.core.selenium_client import SeleniumValidator, generate_selenium_code
 
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
def generate_code(request: ValidateRequest):
    """Generate a ready-to-use Selenium Python code snippet."""
    try:
        code = generate_selenium_code(
            request.locator_type,
            request.locator_value,
        )
        return {"code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code generation error: {str(e)}")