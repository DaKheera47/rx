from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    generic_name: str = Field(min_length=1)
    brand_name: str = Field(min_length=1)
    country: str = Field(min_length=2)
    authority: str = Field(min_length=2)
    registration_id: Optional[str] = None
    active_ingredients: Optional[str] = None
    manufacturer_name: Optional[str] = None
    registration_date: Optional[date] = None
    source_url: Optional[str] = None
    rxcui: Optional[str] = None
