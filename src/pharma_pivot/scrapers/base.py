from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from pharma_pivot.models.schemas import ProductSchema


class BaseScraper(ABC):
    country: str
    authority: str

    @abstractmethod
    async def fetch_products(self, generic_name: str, rxcui: str | None = None) -> list[ProductSchema]:
        raise NotImplementedError

    def validate_products(self, items: Iterable[dict]) -> list[ProductSchema]:
        validated = []
        for item in items:
            validated.append(ProductSchema.model_validate(item))
        return validated
