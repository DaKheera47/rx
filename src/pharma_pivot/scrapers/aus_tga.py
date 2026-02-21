from __future__ import annotations

from pharma_pivot.models.schemas import ProductSchema
from pharma_pivot.scrapers.base import BaseScraper


class AUSTGAScraper(BaseScraper):
    country = "Australia"
    authority = "TGA"

    async def fetch_products(self, generic_name: str, rxcui: str | None = None) -> list[ProductSchema]:
        sample = [
            {
                "generic_name": generic_name,
                "brand_name": f"{generic_name.title()} AU Starter",
                "country": self.country,
                "authority": self.authority,
                "registration_id": "AU-TGA-0001",
                "source_url": "https://www.tga.gov.au/",
                "rxcui": rxcui,
            }
        ]
        return self.validate_products(sample)
