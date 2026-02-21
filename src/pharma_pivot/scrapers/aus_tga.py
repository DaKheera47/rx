from __future__ import annotations

import logging
from datetime import date

import httpx

from pharma_pivot.models.schemas import ProductSchema
from pharma_pivot.scrapers.base import BaseScraper


class AUSTGAScraper(BaseScraper):
    country = "Australia"
    authority = "TGA"
    endpoint = "https://data.tga.gov.au/ARTGSearch/ARTGWebService.svc/JSON/ARTGValueSearch/"
    logger = logging.getLogger("pharma_pivot.scrapers.aus_tga")

    async def fetch_products(self, generic_name: str, rxcui: str | None = None) -> list[ProductSchema]:
        params = {
            "pagestart": "1",
            "pageend": "50",
            "searchterm": generic_name,
        }

        try:
            self.logger.info("Querying TGA generic='%s'", generic_name)
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(self.endpoint, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            self.logger.warning("TGA query failed generic='%s': %s", generic_name, exc)
            return []

        results = payload.get("Results", [])
        if not results:
            self.logger.info("TGA returned 0 rows for generic='%s'", generic_name)
            return []

        products: list[dict] = []
        seen_keys: set[tuple[str | None, str]] = set()
        for item in results:
            name = item.get("Name") or "Unknown"
            brand_name = name if name.strip() else "Unknown"

            registration_id = item.get("LicenceId")

            # Extract active ingredients from all nested 'Products'
            active_ingredients: set[str] = set()
            for prod in item.get("Products", []):
                for ing in prod.get("Ingredients", []):
                    if ing.get("FormulationType") == "Active":
                        ing_name = ing.get("Name", "").strip()
                        if ing_name:
                            active_ingredients.add(ing_name)

            active_ingredients_str = ", ".join(sorted(list(active_ingredients))) if active_ingredients else None

            sponsor_info = item.get("Sponsor", {})
            manufacturer_name = sponsor_info.get("Name", "Unknown")

            start_date_str = item.get("StartDate")
            registration_date = None
            if start_date_str:
                try:
                    # JSON dates from items might be 1991-04-17 or 1991-04-17T00:00:00
                    clean_date = start_date_str.split("T")[0]
                    registration_date = date.fromisoformat(clean_date)
                except (ValueError, IndexError):
                    pass

            product_info_link = (item.get("ProductInformation") or {}).get("DocumentLink")
            consumer_info_link = (item.get("ConsumerInformation") or {}).get("DocumentLink")
            source_url = product_info_link or consumer_info_link
            if not source_url:
                source_url = f"https://www.tga.gov.au/resources/artg/{registration_id}" if registration_id else None

            dedupe_key = (registration_id, brand_name.lower())
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            products.append(
                {
                    "generic_name": generic_name,
                    "brand_name": brand_name,
                    "country": self.country,
                    "authority": self.authority,
                    "registration_id": registration_id,
                    "active_ingredients": active_ingredients_str,
                    "manufacturer_name": manufacturer_name,
                    "registration_date": registration_date,
                    "source_url": source_url,
                    "rxcui": rxcui,
                }
            )

        self.logger.info("TGA normalized rows=%s generic='%s'", len(products), generic_name)
        return self.validate_products(products)
