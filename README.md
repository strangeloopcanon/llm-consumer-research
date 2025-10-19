# Synthetic Consumer Research Service

Reimagining concept testing for product teams that need insight in minutes, not weeks. This repo is the reference implementation of our synthetic panel: it turns a product idea plus an audience description into survey-quality distributions, qualitative rationale, and diagnostics you can actually ship.

## Why this exists

- **Traditional consumer research is slow and expensive.** Classic panels need recruiting, incentives, and weeks of field time before you see a histogram. Marketers and PMs often compromise with ad hoc surveys or gut instinct.
- **LLMs unlock cheap respondents but need discipline.** Asking a model for a Likert score produces confident nonsense unless you constrain context, persona voice, and scoring. We pair models with deterministic anchors so teams can trust the output.
- **We’re building a new standard for rapid insight.** This project is the baseline service we operate: a monolithic Python app with type-safe interfaces, reproducible anchors, and gates for safety, cost, and observability.

## What you get out of the box

- Weighted Likert distributions (mean, top-2 box, bootstrap CIs) per persona and in aggregate.
- Concise persona-specific rationales and top recurring themes to understand *why* the score shifted.
- A FastAPI endpoint, Gradio UI, and CLI hooks that plug into existing research workflows.
- Typed Pydantic models, deterministic anchor banks, and test suites (unit + LLM golden) to keep changes safe.

## How the engine works

1. **Ingest the concept.** We accept free-text copy or fetch a URL, normalize the payload, and build a prompt block with provenance.
2. **Elicit synthetic respondents.** For each persona, GPT-5 (Responses API) roleplays realistic rationales with enforced JSON outputs, caching, and retry controls.
3. **Map rationales to Likert space.** Semantic Similarity Rating (SSR) embeds each rationale against curated anchor banks, averages across variants, and aggregates to personas and overall distributions.

The result is a transparent pipeline: every decision—persona weights, anchors, models, retry budget—is versioned and auditable.

## Run it locally

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install --upgrade pip
pip install -e .

# ensure `OPENAI_API_KEY` (and optional `RESEARCH_MODEL`) are set or defined in `.env`
uvicorn ssr_service.api:app --host 0.0.0.0 --port 8000
```

### Example request

```bash
curl -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "concept": {
      "text": "A premium whitening toothpaste with enamel-safe ingredients and a refreshing mint flavor.",
      "title": "RadiantSmile Whitening Toothpaste",
      "price": "$5.99"
    },
    "personas": [
      {
        "name": "Emily",
        "age": "34",
        "gender": "female",
        "region": "US",
        "income": "Upper middle",
        "descriptors": ["health-conscious", "busy mom"],
        "weight": 0.6
      }
    ],
    "options": {"n": 25}
  }'
```

The response includes:

- Per-persona Likert pmf, mean, top-2 box, rationales, and key themes.
- Aggregate distribution weighted by persona weights.
- Metadata describing the prompt, anchor bank, and bootstrap CIs for the average score.
- Persona summaries that highlight the segment backgrounds powering the simulation.

## Anatomy of the repo

- `src/ssr_service/api.py` – FastAPI surface exposing `/health` and `/simulate`.
- `src/ssr_service/orchestrator.py` – the heart of the pipeline (ingestion → elicitation → SSR → aggregation).
- `src/ssr_service/elicitation.py` – Responses API client with JSON-mode prompts, caching, and retry guards.
- `src/ssr_service/ssr.py` / `embedding.py` – anchor management and cosine-similarity mapping for Likert distributions.
- `src/ssr_service/personas.py` – persona library loader, CSV ingestion, and weight normalization for stratified samples.
- `src/ssr_service/data/anchors/purchase_intent_en.yml` – versioned anchor banks; extend these to add new intents.
- `src/ssr_service/data/personas/*.yml` – ACS-derived personas you can override or replace.
- `src/ssr_service/frontend.py` & `gradio_app.py` – Gradio dashboard for researchers and demo loops.
- `scripts/generate_gov_personas.py` – reproducible persona regeneration straight from the U.S. Census Bureau ACS API.
- `tests/` & `tests_llm_live/` – unit tests plus golden-schema validation for live LLM runs.

## Configuration

- `OPENAI_API_KEY` – required.
- `OPENAI_BASE_URL` – optional custom endpoint.
- `RESEARCH_MODEL` – overrides the Responses API model (default `gpt-5`).
- `OPENAI_EMBEDDING_MODEL` – embedding model (default `text-embedding-3-small`).
- `ANCHOR_BANK_PATH` – directory containing anchor YAML files.
- `PERSONA_LIBRARY_PATH` – directory containing persona library YAML files.

All settings are loaded via `pydantic-settings`; `.env` in the repo root is respected.

## Personas and sampling

- Built-in persona groups live in `src/ssr_service/data/personas`. Each YAML notes the specific ACS table used (e.g. B01001, B14004, B19037, B28002). Use a `persona_group` value (e.g. `us_toothpaste_buyers`, `us_backpack_buyers`, `us_portable_storage_buyers`) in the API body to pull the pre-weighted mix.
- Provide `persona_csv` with CSV text to define custom segments. Supported columns include:
  - Core demographics: `name, age, gender, region, income, occupation, education, household`.
  - Behavioural detail: `habits`, `motivations`, `pain_points`, `preferred_channels`, `purchase_frequency`, `background`, `notes` (semicolon-separated fields).
  - Weighting: `weight` (fractional, will be normalized if the column is missing or does not sum to 1).
  - Misc aliases: `traits` maps to `descriptors`; `purchase_freq` maps to `purchase_frequency`.

  Example:

  ```csv
  name,age,gender,region,income,occupation,habits,motivations,preferred_channels,weight
  Value Seekers,30-49,female,US,Lower,Retail associate,"coupon stacking;night stock runs","stretch paycheck","Email;SMS",0.6
  Premium Loyalists,30-49,male,US,Upper,Product lead,"reads design blogs","pay for craftsmanship","Instagram",0.4
  ```

- Sampling knobs:
- `options.n` = per-persona respondent count (default 200).
- `options.total_n` + `options.stratified` (true) allocate respondents across personas in proportion to their weights.
- `sample_id` (optional) lets you bootstrap a request from the demo scenarios in `demo_samples.json`.

### Regenerating personas from ACS data

If you need to refresh personas when new ACS releases drop:

```bash
source .venv311/bin/activate
python scripts/generate_gov_personas.py
```

This script hits the Census API to pull:

1. Age distribution (B01001) for toothpaste buyers.
2. College enrollment (B14004) + age-by-income (B19037) for backpack segments.
3. Internet subscription types (B28002) for portable storage segments.

The resulting weights are normalized and written into the YAMLs mentioned above, keeping everything traceable to official U.S. government publications.

## Notes

- The current MVP focuses on SSR for 5-point purchase intent. Additional intents can be added by defining new anchor YAML files.
- Concurrency is configurable through `MAX_CONCURRENCY` (default 64). The orchestrator retries once on transient API errors.
- Bootstrap CIs are computed over respondent-level means; increase `options.n` for more stable estimates.

## Gradio frontend

Launch the interactive UI:

```bash
source .venv311/bin/activate
python gradio_app.py
```

The UI lets you:

- Paste concept copy or a URL.
- Choose a sample scenario (`Sample Scenario` dropdown) to auto-populate concept, personas, and question.
- Choose a persona library group or upload a CSV of custom personas.
- Select per-persona or stratified total sample sizes.
- Override the intent question.
- Inspect aggregate metrics, persona breakdowns, and metadata directly in the browser.

## Quick CLI runner

Prefer a terminal workflow? Use the simplified entry point:

```bash
source .venv311/bin/activate
python -m ssr_service.simple_cli \
  --concept-text "A sparkling hydration tablet that dissolves in 30 seconds." \
  --persona-group us_toothpaste_buyers \
  --samples-per-persona 20 \
  --json
```

The command prints either a concise summary or full JSON (via `--json`), pulling enriched persona context into the prompt automatically. Point `--persona-csv` at your own panel export to override the built-in groups.

## Roadmap highlights

This repo tracks the production roadmap in `plan.md` (ignored by Git for local iteration). Upcoming milestones include richer retrieval (competitors, reviews), persistent storage, cost metering, and multi-provider diagnostics. Contributions that move us toward trustworthy, rapid consumer insight are welcome—open an issue before large architectural changes.
