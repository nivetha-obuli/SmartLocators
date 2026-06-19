from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.models.schemas import (
    AnalyzeRequest, AnalyzeResponse, InputType, WebElement
)
from backend.core.parser import HTMLParser
from backend.core.locator_engine import LocatorEngine
from backend.core.recommender import LocatorRecommender

router = APIRouter(prefix="/analyze", tags=["analyze"])

html_parser = HTMLParser()
locator_engine = LocatorEngine()
recommender = LocatorRecommender()


@router.post("/", response_model=AnalyzeResponse)
async def analyze_page(request: AnalyzeRequest):
    """
    Analyze a web page from URL or raw HTML.
    Returns all detected elements with generated locators.
    """
    html_content = ""
    resolved_url = None

    if request.input_type == InputType.URL:
        try:
            html_content, resolved_url = await html_parser.fetch_url(request.content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    else:
        html_content = request.content

    try:
        soup = html_parser.parse(html_content)
        page_title = html_parser.get_page_title(soup)

        raw_elements = html_parser.extract_elements(
            soup,
            filter_tag=request.filter_tag,
            filter_attribute=request.filter_attribute
        )

        web_elements = []
        for idx, el in enumerate(raw_elements):
            try:
                attrs = html_parser.get_element_attributes(el)
                locators = locator_engine.generate_all(el, soup)
                ranked = recommender.rank(locators)
                best = recommender.pick_best(ranked)

                web_elements.append(WebElement(
                    tag=el.name,
                    text=el.get_text(strip=True)[:100] or None,
                    attributes=attrs,
                    locators=ranked[:5],           # Top 5 locators per element
                    best_locator=best,
                    element_index=idx
                ))
            except Exception as e:
                # Skip elements that fail to process
                print(f"Error processing element {idx}: {str(e)}")
                continue

        return AnalyzeResponse(
            url=resolved_url,
            total_elements=len(web_elements),
            elements=web_elements,
            page_title=page_title
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@router.get("/url", response_model=AnalyzeResponse)
async def analyze_url(
    url: str = Query(..., description="Full URL to analyze"),
    tag: Optional[str] = Query(None, description="Filter by HTML tag"),
):
    """Convenience GET endpoint — analyze a URL directly."""
    req = AnalyzeRequest(input_type=InputType.URL, content=url, filter_tag=tag)
    return await analyze_page(req)