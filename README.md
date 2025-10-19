# Synthetic Consumer Research Service

This project implements the semantic similarity rating (SSR) workflow described in *LLMs Reproduce Human Purchase Intent via Semantic Similarity*. It exposes an API that ingests a concept, elicits short rationales from synthetic personas via the OpenAI Responses API (default: `gpt-5`), maps the text to Likert distributions using anchor embeddings, and returns familiar survey metrics plus qualitative snippets.

## Quick start

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

## Project structure

- `src/ssr_service/anchors.py` – load YAML anchor banks.
- `src/ssr_service/personas.py` – persona library, CSV ingestion, and weight normalization helpers.
- `src/ssr_service/embedding.py` – OpenAI embedding helpers for anchors and rationales.
- `src/ssr_service/elicitation.py` – Responses API client for persona rationales.
- `src/ssr_service/orchestrator.py` – orchestrates ingestion, elicitation, SSR mapping, aggregation, and bootstrapping.
- `src/ssr_service/api.py` – FastAPI app exposing `/health` and `/simulate` endpoints.
- `src/ssr_service/data/anchors/purchase_intent_en.yml` – anchor sets for purchase intent (3 variants).
- `src/ssr_service/data/personas/us_toothpaste.yml` – ACS-derived age mix for oral care shoppers.
- `src/ssr_service/data/personas/us_backpack_buyers.yml`, `us_portable_storage_buyers.yml` – additional demo persona packs.
- `src/ssr_service/data/samples/demo_samples.json` – canned concept copies from FakeStore API for quick testing.
- `scripts/generate_gov_personas.py` – regenerates persona YAMLs directly from the U.S. Census Bureau 2022 ACS 1-year API.
- `src/ssr_service/frontend.py` / `gradio_app.py` – Gradio UI for interactive runs.

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
- Provide `persona_csv` with CSV text to define custom segments. Expected columns: `name, age, gender, region, income, descriptors` (semicolon-separated) and `weight` (fractional). Example:

  ```csv
  name,age,gender,region,income,descriptors,weight
  Value Seekers,30-49,female,US,Lower,"budget;coupon",0.6
  Premium Loyalists,30-49,male,US,Upper,"premium;brand loyal",0.4
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
