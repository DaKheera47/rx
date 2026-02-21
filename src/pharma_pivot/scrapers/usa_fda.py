from __future__ import annotations

import os

import httpx

from pharma_pivot.models.schemas import ProductSchema
from pharma_pivot.scrapers.base import BaseScraper


class USAFDAScraper(BaseScraper):
    country = "USA"
    authority = "FDA"
    endpoint = "https://api.fda.gov/drug/ndc.json"

    async def fetch_products(self, generic_name: str, rxcui: str | None = None) -> list[ProductSchema]:
        api_key = os.getenv("OPENFDA_API_KEY", "").strip()
        params = {
            "search": f"generic_name:\"{generic_name}\"",
            "limit": "10",
        }
        if api_key:
            params["api_key"] = api_key

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(self.endpoint, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return self.validate_products(
                [
                    {
                        "generic_name": generic_name,
                        "brand_name": f"{generic_name.title()} Mock US",
                        "country": self.country,
                        "authority": self.authority,
                        "registration_id": "US-MOCK-0001",
                        "source_url": self.endpoint,
                        "rxcui": rxcui,
                    }
                ]
            )

        products = []
        for item in payload.get("results", []):
            products.append(
                {
                    "generic_name": generic_name,
                    "brand_name": item.get("brand_name") or "Unknown Brand",
                    "country": self.country,
                    "authority": self.authority,
                    "registration_id": item.get("product_ndc"),
                    "source_url": self.endpoint,
                    "rxcui": rxcui,
                }
            )

        return self.validate_products(products)
