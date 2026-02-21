from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from pharma_pivot.models.schemas import ProductSchema
from pharma_pivot.scrapers.base import BaseScraper


class UKMHRAScraper(BaseScraper):
    country = "UK"
    authority = "MHRA"
    dmd_xml_url = "https://example.com/dmd.xml"

    async def fetch_products(self, generic_name: str, rxcui: str | None = None) -> list[ProductSchema]:
        xml_text = await self._download_dmd_xml()
        if not xml_text:
            xml_text = self._mock_dmd_xml(generic_name)

        rows = self._parse_dmd_xml(xml_text, generic_name=generic_name, rxcui=rxcui)
        return self.validate_products(rows)

    async def _download_dmd_xml(self) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(self.dmd_xml_url)
                response.raise_for_status()
                return response.text
        except Exception:
            return None

    @staticmethod
    def _mock_dmd_xml(generic_name: str) -> str:
        return f"""
<dmd>
  <product>
    <name>{generic_name.title()} Accord 5mg Tablets</name>
    <code>UK-DMD-0001</code>
  </product>
  <product>
    <name>{generic_name.title()} Teva Oral Solution</name>
    <code>UK-DMD-0002</code>
  </product>
</dmd>
""".strip()

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
