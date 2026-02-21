from __future__ import annotations

from pharma_pivot.models.schemas import ProductSchema
from pharma_pivot.scrapers.base import BaseScraper


class AUSTGAScraper(BaseScraper):
    country = "Australia"
    authority = "TGA"

    async def fetch_products(self, generic_name: str, rxcui: str | None = None) -> list[ProductSchema]:
        return []
