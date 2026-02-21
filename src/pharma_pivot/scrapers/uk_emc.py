from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from pharma_pivot.models.schemas import ProductSchema
from pharma_pivot.scrapers.base import BaseScraper


class UKEMCScraper(BaseScraper):
    country = "UK"
    authority = "EMC"
    search_url = "https://www.medicines.org.uk/emc/search-js"
    base_url = "https://www.medicines.org.uk"
    default_limit = 50
    logger = logging.getLogger("pharma_pivot.scrapers.uk_eMC")
    request_headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "text/html",
        "priority": "u=1, i",
        "sec-ch-ua": '"Chromium";v="145", "Not:A-Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/145.0.0.0 Safari/537.36"
        ),
    }

    async def fetch_products(self, generic_name: str, rxcui: str | None = None) -> list[ProductSchema]:
        seen_ids: set[str] = set()
        rows: list[dict] = []
        offset = 1

        while True:
            html = await self._fetch_search_page(generic_name=generic_name, offset=offset, limit=self.default_limit)
            if not html:
                break

            page_rows, next_offset = self._parse_search_html(
                html,
                generic_name=generic_name,
                rxcui=rxcui,
                seen_ids=seen_ids,
            )
            rows.extend(page_rows)

            if not next_offset or next_offset == offset:
                break
            offset = next_offset

        self.logger.info("UK EMC normalized rows=%s generic='%s'", len(rows), generic_name)
        return self.validate_products(rows)

    async def _fetch_search_page(self, generic_name: str, offset: int, limit: int) -> str | None:
        params = {
            "q": generic_name,
            "offset": str(offset),
            "limit": str(limit),
            "orderBy": "product",
        }
        headers = {
            **self.request_headers,
            "referer": f"{self.base_url}/emc/search?q={generic_name}",
        }

        try:
            self.logger.info("Querying EMC EMC generic='%s' offset=%s", generic_name, offset)
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(self.search_url, params=params, headers=headers)
                response.raise_for_status()
                return response.text
        except Exception as exc:
            self.logger.warning("EMC EMC query failed generic='%s' offset=%s: %s", generic_name, offset, exc)
            return None

    def _parse_search_html(
        self,
        html_text: str,
        generic_name: str,
        rxcui: str | None,
        seen_ids: set[str],
    ) -> tuple[list[dict], int | None]:
        soup = BeautifulSoup(html_text, "html.parser")
        rows: list[dict] = []

        for product in soup.select("div.search-results-product"):
            title_link = product.select_one("a.search-results-product-info-title-link")
            if not title_link:
                continue

            name = title_link.get_text(strip=True)
            if not name:
                continue

            href = title_link.get("href") or ""
            registration_id = self._extract_registration_id(href)
            ingredients_text = product.select_one("div.search-results-product-info-type")
            company_link = product.select_one("div.search-results-product-info-company a")
            manufacturer_name = company_link.get_text(strip=True) if company_link else None
            active_ingredients = ingredients_text.get_text(strip=True) if ingredients_text else None

            dedupe_key = registration_id or name.lower()
            if dedupe_key in seen_ids:
                continue
            seen_ids.add(dedupe_key)

            rows.append(
                {
                    "generic_name": generic_name,
                    "brand_name": name,
                    "country": self.country,
                    "authority": self.authority,
                    "registration_id": registration_id,
                    "active_ingredients": active_ingredients,
                    "manufacturer_name": manufacturer_name,
                    "source_url": urljoin(self.base_url, href) if href else self.search_url,
                    "rxcui": rxcui,
                }
            )

        next_link = soup.select_one("a.search-paging-next")
        next_offset: int | None = None
        if next_link:
            raw_offset = next_link.get("data-next-offset")
            if raw_offset and raw_offset.isdigit():
                next_offset = int(raw_offset)

        return rows, next_offset

    @staticmethod
    def _extract_registration_id(href: str) -> str | None:
        if not href:
            return None
        match = re.search(r"/emc/product/(\d+)", href)
        if not match:
            return None
        return match.group(1)
