from __future__ import annotations

import logging

import httpx

from pharma_pivot.models.schemas import ProductSchema
from pharma_pivot.scrapers.base import BaseScraper


class USAFDAScraper(BaseScraper):
    country = "USA"
    authority = "FDA"
    endpoint = "https://api.fda.gov/drug/drugsfda.json"
    rxnorm_names_endpoint = "https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/allProperties.json"
    logger = logging.getLogger("pharma_pivot.scrapers.usa_fda")

    async def fetch_products(self, generic_name: str, rxcui: str | None = None) -> list[ProductSchema]:
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                search_terms = await self._resolve_search_terms(client, generic_name, rxcui)
                self.logger.info("Querying openFDA generic='%s' aliases=%s", generic_name, search_terms)

                merged_results: list[dict] = []
                for term in search_terms:
                    payload = await self._fetch_fda_payload(client, term)
                    if not payload:
                        continue
                    merged_results.extend(payload.get("results", []))
        except Exception as exc:
            self.logger.warning("openFDA query failed generic='%s': %s", generic_name, exc)
            return []

        products: list[dict] = []
        seen_keys: set[tuple[str, str, str]] = set()
        for item in merged_results:
            fda_info = item.get("openfda", {})
            if not fda_info:
                continue

            generic_names = fda_info.get("generic_name", [generic_name])
            manufacturer_names = fda_info.get("manufacturer_name", ["Unknown"])
            application_number = item.get("application_number")
            registration_id = application_number if isinstance(application_number, str) else "N/A"

            source_url = (
                "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process"
                f"&ApplNo={registration_id}"
            )

            brand_name = fda_info.get("brand_name", ["Unknown"])[0]
            manufacturer_name = manufacturer_names[0]
            dedupe_key = (registration_id, brand_name.lower(), manufacturer_name.lower())
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
                    "active_ingredients": ", ".join(generic_names) if generic_names else generic_name,
                    "manufacturer_name": manufacturer_name,
                    "source_url": source_url,
                    "rxcui": rxcui,
                }
            )

        if not products:
            self.logger.info("openFDA returned 0 rows for generic='%s'", generic_name)

        self.logger.info("openFDA normalized rows=%s generic='%s'", len(products), generic_name)

        return self.validate_products(products)

    async def _resolve_search_terms(
        self,
        client: httpx.AsyncClient,
        generic_name: str,
        rxcui: str | None,
    ) -> list[str]:
        base_name = generic_name.strip()
        if not base_name:
            return []

        if not rxcui:
            return [base_name]

        try:
            response = await client.get(
                self.rxnorm_names_endpoint.format(rxcui=rxcui),
                params={"prop": "names"},
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            self.logger.warning("RxNorm names lookup failed rxcui='%s': %s", rxcui, exc)
            return [base_name]

        terms: list[str] = [base_name]
        seen: set[str] = {base_name.lower()}

        concepts = payload.get("propConceptGroup", {}).get("propConcept") or []
        for concept in concepts:
            value = (concept.get("propValue") or "").strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            terms.append(value)

        return terms

    async def _fetch_fda_payload(self, client: httpx.AsyncClient, term: str) -> dict | None:
        params = {
            "search": f"openfda.generic_name:\"{term}\"",
            "limit": "50",
        }

        response = await client.get(self.endpoint, params=params)
        if response.status_code != 200:
            self.logger.warning("openFDA returned status=%s term='%s'", response.status_code, term)
            return None

        return response.json()
