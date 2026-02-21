import pytest

from pharma_pivot.scrapers.uk_mhra import UKMHRAScraper
from pharma_pivot.scrapers.usa_fda import USAFDAScraper


@pytest.mark.asyncio
async def test_usa_fda_returns_valid_products():
    scraper = USAFDAScraper()

    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": [
                    {
                        "brand_name": "Glucophage",
                        "product_ndc": "0000-0000",
                    }
                ]
            }

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *args, **kwargs):
            return _FakeResponse()

    import pharma_pivot.scrapers.usa_fda as usa_fda_module

    monkeypatch_target = lambda *args, **kwargs: _FakeClient()
    setattr(usa_fda_module.httpx, "AsyncClient", monkeypatch_target)

    products = await scraper.fetch_products("metformin", rxcui="860975")

    assert products
    assert all(item.country == "USA" for item in products)
    assert all(item.rxcui == "860975" for item in products)


@pytest.mark.asyncio
async def test_uk_mhra_parses_xml_into_products():
    scraper = UKMHRAScraper()

        async def _fake_download() -> str:
                return """
<dmd>
    <product>
        <name>Atorvastatin Test Brand</name>
        <code>UK-DMD-TEST-0001</code>
    </product>
</dmd>
""".strip()

        scraper._download_dmd_xml = _fake_download  # type: ignore[method-assign]

    products = await scraper.fetch_products("atorvastatin", rxcui="83367")

    assert products
    assert all(item.country == "UK" for item in products)
    assert all(item.authority == "MHRA" for item in products)
