from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import httpx

from pharma_pivot.models.schemas import ProductSchema
from pharma_pivot.scrapers.base import BaseScraper


class UKMHRAScraper(BaseScraper):
    country = "UK"
    authority = "MHRA"
    dmd_xml_url = "https://example.com/dmd.xml"
    logger = logging.getLogger("pharma_pivot.scrapers.uk_mhra")

    async def fetch_products(self, generic_name: str, rxcui: str | None = None) -> list[ProductSchema]:
        xml_text = await self._download_dmd_xml()
        if not xml_text:
            self.logger.warning("No UK dmd XML available for generic='%s'", generic_name)
            return []

        try:
            rows = self._parse_dmd_xml(xml_text, generic_name=generic_name, rxcui=rxcui)
        except ET.ParseError as exc:
            self.logger.warning("Failed to parse UK dmd XML: %s", exc)
            return []

        self.logger.info("UK MHRA normalized rows=%s generic='%s'", len(rows), generic_name)
        return self.validate_products(rows)

    async def _download_dmd_xml(self) -> str | None:
        try:
            self.logger.info("Downloading UK dmd XML source")
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(self.dmd_xml_url)
                response.raise_for_status()
                return response.text
        except Exception as exc:
            self.logger.warning("UK dmd XML download failed: %s", exc)
            return None

    def _parse_dmd_xml(self, xml_text: str, generic_name: str, rxcui: str | None) -> list[dict]:
        root = ET.fromstring(xml_text)
        rows: list[dict] = []

        for product in root.findall(".//product"):
            name = product.findtext("name")
            code = product.findtext("code")
            if not name:
                continue

            rows.append(
                {
                    "generic_name": generic_name,
                    "brand_name": name,
                    "country": self.country,
                    "authority": self.authority,
                    "registration_id": code,
                    "source_url": self.dmd_xml_url,
                    "rxcui": rxcui,
                }
            )

        return rows
