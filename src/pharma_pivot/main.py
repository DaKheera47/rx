import asyncio
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from pharma_pivot.core.normalizer import RxNormNormalizer
from pharma_pivot.scrapers.aus_tga import AUSTGAScraper
from pharma_pivot.scrapers.uk_mhra import UKMHRAScraper
from pharma_pivot.scrapers.usa_fda import USAFDAScraper

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))

app = FastAPI(title="PharmaPivot")

normalizer = RxNormNormalizer()
active_scrapers = [USAFDAScraper(), UKMHRAScraper(), AUSTGAScraper()]


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "query": "", "rxcui": None, "results": []},
    )


@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: str = Query(default="", min_length=0, description="Generic drug name"),
) -> HTMLResponse:
    query = q.strip()
    if not query:
        return templates.TemplateResponse(
            "partials/results_table.html",
            {"request": request, "query": "", "rxcui": None, "results": []},
        )

    rxcui = await asyncio.to_thread(normalizer.resolve_rxcui, query)
    if not rxcui:
        return templates.TemplateResponse(
            "partials/results_table.html",
            {
                "request": request,
                "query": query,
                "rxcui": None,
                "results": [],
                "message": "No RxNorm concept found for this generic name.",
            },
        )

    tasks = [scraper.fetch_products(query, rxcui=rxcui) for scraper in active_scrapers]
    batches = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for batch in batches:
        if isinstance(batch, Exception):
            continue
        results.extend(batch)

    results.sort(key=lambda item: (item.country, item.brand_name))

    return templates.TemplateResponse(
        "partials/results_table.html",
        {
            "request": request,
            "query": query,
            "rxcui": rxcui,
            "results": results,
        },
    )
