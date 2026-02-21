import pytest

from pharma_pivot.scrapers.uk_mhra import UKMHRAScraper
from pharma_pivot.scrapers.usa_fda import USAFDAScraper


@pytest.mark.asyncio
async def test_usa_fda_returns_valid_products():
    scraper = USAFDAScraper()
    products = await scraper.fetch_products("metformin", rxcui="860975")

    assert products
    assert all(item.country == "USA" for item in products)
    assert all(item.rxcui == "860975" for item in products)


@pytest.mark.asyncio
async def test_uk_mhra_parses_xml_into_products():
    scraper = UKMHRAScraper()
    products = await scraper.fetch_products("atorvastatin", rxcui="83367")

    assert products
    assert all(item.country == "UK" for item in products)
    assert all(item.authority == "MHRA" for item in products)
