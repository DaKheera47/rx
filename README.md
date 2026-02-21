# PharmaPivot

PharmaPivot is a FastAPI + HTMX application that normalizes a user-entered generic drug name to RxNorm (RXCUI), then aggregates registered product names from country-specific scraper strategies.

## Run

```bash
uv sync
uv run uvicorn pharma_pivot.main:app --reload --app-dir src
```

Visit: http://127.0.0.1:8000

## Development

```bash
uv sync --group dev
uv run pytest
```
