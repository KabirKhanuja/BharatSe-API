"""The shape a generated listing must have.

Validated with Pydantic rather than trusted. Two constraints the providers do
not honour, so they are enforced here in validators instead of in the schema:
length limits, and item counts.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Category = Literal[
    "textiles",
    "pottery",
    "jewellery",
    "woodwork",
    "metalwork",
    "painting",
    "bamboo_cane",
    "leather",
    "other",
]


class GeneratedListing(BaseModel):
    """What one call returns from an artisan's voice note.

    Both languages come out of the same pass, so the Hindi is not a machine
    translation of the English and the two stay consistent.
    """

    title_en: str
    title_hi: str
    description_en: str
    description_hi: str
    tags: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    technique: str = ""
    category: Category = "other"
    estimated_hours: float | None = None
    transcript: str = ""
    detected_language: str = ""

    @field_validator("title_en", "title_hi")
    @classmethod
    def _trim_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty")
        # Marketplaces truncate past roughly 60 characters, so trim on a word
        # boundary rather than letting the channel cut mid word.
        return v if len(v) <= 60 else v[:60].rsplit(" ", 1)[0]

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, v: list[str]) -> list[str]:
        cleaned = [t.strip().lower() for t in v if t.strip()]
        deduped = list(dict.fromkeys(cleaned))
        if len(deduped) < 3:
            raise ValueError("at least 3 tags are required for search to work")
        return deduped[:8]

    @field_validator("materials")
    @classmethod
    def _clean_materials(cls, v: list[str]) -> list[str]:
        return [m.strip().lower() for m in v if m.strip()][:6]
