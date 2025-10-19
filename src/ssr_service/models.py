"""Pydantic models for API inputs and outputs."""

from __future__ import annotations

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, TypeAdapter, ValidationError

_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


def coerce_http_url(value: Union[str, HttpUrl, None]) -> Optional[HttpUrl]:
    if value is None:
        return None
    if isinstance(value, HttpUrl):
        return value
    try:
        return _HTTP_URL_ADAPTER.validate_python(value)
    except ValidationError:
        return None


class PersonaSpec(BaseModel):
    name: str = Field(default_factory=lambda: "persona")
    age: Optional[str] = None
    gender: Optional[str] = None
    income: Optional[str] = None
    region: Optional[str] = None
    usage_context: Optional[str] = Field(default=None, alias="usage")
    descriptors: List[str] = Field(default_factory=list)
    weight: float = Field(default=1.0, ge=0)

    def describe(self) -> str:
        parts: List[str] = []
        if self.age:
            parts.append(f"age {self.age}")
        if self.gender:
            parts.append(self.gender)
        if self.region:
            parts.append(f"based in {self.region}")
        if self.income:
            parts.append(f"income: {self.income}")
        if self.usage_context:
            parts.append(f"usage context: {self.usage_context}")
        if self.descriptors:
            parts.append(
                "additional traits: " + ", ".join(self.descriptors)
            )
        return ", ".join(parts) if parts else "a representative consumer"


class ConceptInput(BaseModel):
    url: Optional[HttpUrl] = None
    text: Optional[str] = None
    title: Optional[str] = None
    price: Optional[str] = None


class SimulationOptions(BaseModel):
    n: int = Field(default=200, ge=1)
    model: Optional[str] = None
    embedding_model: Optional[str] = None
    anchor_bank: Optional[str] = Field(default="purchase_intent_en.yml")
    intent: str = Field(default="purchase_intent")
    intent_question: Optional[str] = Field(default=None)
    total_n: Optional[int] = Field(default=None, ge=1)
    stratified: bool = Field(default=False)


class SimulationRequest(BaseModel):
    concept: ConceptInput
    personas: List[PersonaSpec] = Field(default_factory=list)
    persona_group: Optional[str] = Field(default=None)
    persona_csv: Optional[str] = Field(
        default=None, description="Raw CSV string defining personas"
    )
    sample_id: Optional[str] = Field(
        default=None, description="Name of built-in sample scenario"
    )
    intent: str = Field(default="purchase_intent")
    intent_question: Optional[str] = None
    options: SimulationOptions = Field(default_factory=SimulationOptions)


class LikertDistribution(BaseModel):
    ratings: List[int]
    pmf: List[float]
    mean: float
    top2box: float
    sample_n: int


class PersonaResult(BaseModel):
    persona: PersonaSpec
    distribution: LikertDistribution
    rationales: List[str]
    themes: List[str]


class SimulationResponse(BaseModel):
    aggregate: LikertDistribution
    personas: List[PersonaResult]
    metadata: Dict[str, str] = Field(default_factory=dict)


__all__ = [
    "ConceptInput",
    "LikertDistribution",
    "PersonaResult",
    "PersonaSpec",
    "SimulationOptions",
    "SimulationRequest",
    "SimulationResponse",
    "coerce_http_url",
]
