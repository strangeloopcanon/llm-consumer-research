"""Pydantic models for API inputs and outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

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
    occupation: Optional[str] = None
    education: Optional[str] = None
    household: Optional[str] = None
    purchase_frequency: Optional[str] = Field(default=None, alias="purchase_freq")
    usage_context: Optional[str] = Field(default=None, alias="usage")
    background: Optional[str] = None
    habits: List[str] = Field(default_factory=list)
    motivations: List[str] = Field(default_factory=list)
    pain_points: List[str] = Field(default_factory=list)
    preferred_channels: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    source: Optional[str] = None
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
        if self.occupation:
            parts.append(f"occupation: {self.occupation}")
        if self.education:
            parts.append(f"education: {self.education}")
        if self.household:
            parts.append(f"household: {self.household}")
        if self.purchase_frequency:
            parts.append(f"purchase cadence: {self.purchase_frequency}")
        if self.background:
            parts.append(self.background)

        def _format_list(label: str, values: List[str]) -> None:
            if not values:
                return
            trimmed = ", ".join(values[:3])
            parts.append(f"{label}: {trimmed}")

        _format_list("habits", self.habits)
        _format_list("motivations", self.motivations)
        _format_list("pain points", self.pain_points)
        _format_list("preferred channels", self.preferred_channels)
        _format_list("additional traits", self.descriptors)

        if self.notes:
            parts.append(self.notes)
        return ", ".join(parts) if parts else "a representative consumer"


class ConceptInput(BaseModel):
    url: Optional[HttpUrl] = None
    text: Optional[str] = None
    title: Optional[str] = None
    price: Optional[str] = None


class PersonaFilter(BaseModel):
    """Filtering rules for selecting personas from the library."""

    group: Optional[str] = Field(
        default=None,
        description="Restrict search to a specific persona group; falls back to entire library when omitted.",
    )
    include: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Field -> allowed values (case-insensitive). Matches any of the listed values.",
    )
    exclude: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Field -> disallowed values (case-insensitive). Reject personas containing these values.",
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Free-text keywords that must appear in at least one descriptive field.",
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description="Cap the number of personas returned after filtering.",
    )
    weight_share: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional portion of total weight to allocate to this slice.",
    )


class PersonaTemplate(BaseModel):
    """Template that can be converted into a PersonaSpec."""

    name: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    income: Optional[str] = None
    region: Optional[str] = None
    occupation: Optional[str] = None
    education: Optional[str] = None
    household: Optional[str] = None
    purchase_frequency: Optional[str] = Field(default=None, alias="purchase_freq")
    usage_context: Optional[str] = Field(default=None, alias="usage")
    background: Optional[str] = None
    habits: List[str] = Field(default_factory=list)
    motivations: List[str] = Field(default_factory=list)
    pain_points: List[str] = Field(default_factory=list)
    preferred_channels: List[str] = Field(default_factory=list)
    descriptors: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    source: Optional[str] = None
    weight: Optional[float] = Field(default=None, ge=0.0)

    def to_persona_spec(self, fallback_name: str) -> PersonaSpec:
        """Convert the template into a PersonaSpec, applying defaults as needed."""

        persona_data: Dict[str, Union[str, List[str], float, None]] = {
            "name": self.name or fallback_name,
            "age": self.age,
            "gender": self.gender,
            "income": self.income,
            "region": self.region,
            "occupation": self.occupation,
            "education": self.education,
            "household": self.household,
            "purchase_frequency": self.purchase_frequency,
            "usage_context": self.usage_context,
            "background": self.background,
            "habits": self.habits,
            "motivations": self.motivations,
            "pain_points": self.pain_points,
            "preferred_channels": self.preferred_channels,
            "descriptors": self.descriptors,
            "notes": self.notes,
            "source": self.source,
            "weight": self.weight or 1.0,
        }
        return PersonaSpec.model_validate(persona_data)


class PersonaGenerationTask(BaseModel):
    """Instruction for synthesising personas programmatically."""

    prompt: str = Field(
        description="Free-form description of the audience slice to generate."
    )
    count: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Number of personas to synthesise from the prompt.",
    )
    strategy: Literal["heuristic", "openai"] = Field(
        default="heuristic",
        description="Generation backend to use; heuristic is offline and deterministic.",
    )
    weight_share: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional share of total weight reserved for generated personas.",
    )
    attributes: Dict[str, str] = Field(
        default_factory=dict,
        description="Attribute overrides applied to every generated persona (e.g. region=US).",
    )
    templates: List[PersonaTemplate] = Field(
        default_factory=list,
        description="Optional explicit templates to seed the generator; missing values are filled heuristically.",
    )


class PersonaInjection(BaseModel):
    """Directly inject a persona specification into the simulation."""

    persona: PersonaSpec
    weight_share: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional share of total weight reserved for this injection.",
    )


class RakingConfig(BaseModel):
    """Configuration for demographic raking."""

    enabled: bool = False
    mode: Literal["lenient", "strict"] = "lenient"
    iterations: int = Field(default=20, ge=1, le=200)


class PopulationSpec(BaseModel):
    """High-level specification for composing a target population."""

    base_group: Optional[str] = Field(
        default=None,
        description="Optional persona library group to seed the population.",
    )
    persona_csv_path: Optional[Path] = Field(
        default=None,
        description="Optional path to a persona CSV to include as a bucket.",
    )
    filters: List[PersonaFilter] = Field(default_factory=list)
    generations: List[PersonaGenerationTask] = Field(default_factory=list)
    injections: List[PersonaInjection] = Field(default_factory=list)
    marginals: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Optional marginal distributions for raking (field -> category -> share).",
    )
    raking: RakingConfig = Field(default_factory=RakingConfig)


class SimulationOptions(BaseModel):
    n: int = Field(default=200, ge=1)
    model: Optional[str] = None
    embedding_model: Optional[str] = None
    anchor_bank: Optional[str] = Field(default="purchase_intent_en.yml")
    intent: str = Field(default="purchase_intent")
    intent_question: Optional[str] = Field(default=None)
    total_n: Optional[int] = Field(default=None, ge=1)
    stratified: bool = Field(default=False)
    providers: List[str] = Field(default_factory=lambda: ["openai"])
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    additional_instructions: Optional[str] = None


class SimulationRequest(BaseModel):
    concept: ConceptInput
    personas: List[PersonaSpec] = Field(default_factory=list)
    persona_group: Optional[str] = Field(default=None)
    persona_csv: Optional[str] = Field(
        default=None, description="Raw CSV string defining personas"
    )
    questions: List[str] = Field(
        default_factory=list,
        description="Optional list of survey questions to ask each persona in addition to the default intent question.",
    )
    persona_filters: List[PersonaFilter] = Field(
        default_factory=list,
        description="Filters applied to the persona library to compose dynamic segments.",
    )
    persona_injections: List[PersonaInjection] = Field(
        default_factory=list,
        description="Explicit personas added to the request before normalization.",
    )
    persona_generations: List[PersonaGenerationTask] = Field(
        default_factory=list,
        description="Prompt-driven persona generation tasks evaluated before simulation.",
    )
    sample_id: Optional[str] = Field(
        default=None, description="Name of built-in sample scenario"
    )
    intent: str = Field(default="purchase_intent")
    intent_question: Optional[str] = None
    options: SimulationOptions = Field(default_factory=SimulationOptions)
    population_spec: Optional[PopulationSpec] = Field(
        default=None,
        description="High-level population definition evaluated after other persona inputs.",
    )


class LikertDistribution(BaseModel):
    ratings: List[int]
    pmf: List[float]
    mean: float
    top2box: float
    sample_n: int


class PersonaQuestionResult(BaseModel):
    question_id: str
    question: str
    distribution: LikertDistribution
    rationales: List[str]
    themes: List[str]


class PersonaResult(BaseModel):
    persona: PersonaSpec
    distribution: LikertDistribution
    rationales: List[str]
    themes: List[str]
    question_results: List[PersonaQuestionResult] = Field(default_factory=list)


class QuestionAggregate(BaseModel):
    question_id: str
    question: str
    aggregate: LikertDistribution


class SimulationResponse(BaseModel):
    aggregate: LikertDistribution
    personas: List[PersonaResult]
    metadata: Dict[str, str] = Field(default_factory=dict)
    questions: List[QuestionAggregate] = Field(default_factory=list)


__all__ = [
    "ConceptInput",
    "LikertDistribution",
    "QuestionAggregate",
    "PersonaResult",
    "PersonaSpec",
    "PersonaFilter",
    "PersonaTemplate",
    "PersonaGenerationTask",
    "PersonaInjection",
    "PersonaQuestionResult",
    "PopulationSpec",
    "RakingConfig",
    "SimulationOptions",
    "SimulationRequest",
    "SimulationResponse",
    "coerce_http_url",
]
