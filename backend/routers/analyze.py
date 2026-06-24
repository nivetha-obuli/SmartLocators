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
    Returns paginated elements with generated locators.
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

        # Get the full set of detected elements (no slicing) so server-side
        # filtering can be applied across the entire page.
        full_elements, total_detected = html_parser.extract_elements(
            soup,
            filter_tag=request.filter_tag,
            filter_attribute=request.filter_attribute,
            limit=0,
            offset=0,
        )

        # Build WebElement objects for all detected elements (may be heavy on large pages)
        all_web_elements = []
        for idx, el in enumerate(full_elements):
            try:
                attrs = html_parser.get_element_attributes(el)
                locators = locator_engine.generate_all(el, soup)
                ranked = recommender.rank(locators)
                best = recommender.pick_best(ranked)

                all_web_elements.append(WebElement(
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

        # Apply server-side search and reliability filters if provided
        filtered = all_web_elements
        if request.search_query:
            q = request.search_query.strip().lower()
            def matches_search(w):
                if q in (w.tag or "").lower():
                    return True
                if w.text and q in w.text.lower():
                    return True
                if any(q in str(v).lower() for v in w.attributes.values()):
                    return True
                if any(q in loc.value.lower() for loc in w.locators):
                    return True
                return False
            filtered = [w for w in filtered if matches_search(w)]

        if request.reliability_filter:
            rf = request.reliability_filter
            filtered = [w for w in filtered if w.best_locator.reliability == rf]

        total_available = len(filtered)

        # Pagination slice
        start = max(0, request.offset or 0)
        end = start + (request.limit or 0) if (request.limit and request.limit > 0) else None
        page_slice = filtered[start:end]

        # Adjust element_index to reflect absolute index in detected set
        for i, we in enumerate(page_slice):
            we.element_index = start + i

        return AnalyzeResponse(
            url=resolved_url,
            total_elements=len(page_slice),
            total_available=total_available,
            offset=request.offset,
            elements=page_slice,
            page_title=page_title,
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