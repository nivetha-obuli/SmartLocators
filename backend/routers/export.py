from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from backend.models.schemas import WebElement
from backend.utils.helpers  import export_page_object
 
router = APIRouter(prefix="/export", tags=["export"])
 
 
class POMRequest(BaseModel):
    elements:   List[WebElement]
    class_name: Optional[str] = "PageObjects"
    base_url:   Optional[str] = ""
 
 
@router.post("/pom")
def export_pom(request: POMRequest):
    """
    Convert a list of analyzed WebElement objects into a complete
    Python Selenium Page Object Model class.
 
    Returns the generated Python source code as a string.
    """
    code = export_page_object(
        elements   = request.elements,
        class_name = request.class_name or "PageObjects",
        base_url   = request.base_url   or "",
    )
    return {
        "class_name": request.class_name,
        "element_count": len(request.elements),
        "code": code,
    }
 