# Productization Plan: Synthetic Consumer Research via SSR

Purpose: Build a production system that, given an intent (what to measure) and an audience (who it applies to), returns an interpretable Likert distribution and qualitative reasons, using GPT-5 via the Responses API as the core model and Semantic Similarity Rating (SSR) as the default mapping from free‑text to Likert.

This plan favors minimal, reliable steps. We keep just the steps that meaningfully reduce bias/variance or add interpretability: (1) focused context retrieval, (2) concise textual elicitation from a persona, (3) SSR mapping to a Likert distribution. Everything else is kept optional or deferred.

-------------------------------------------------------------------------------
0) Vocabulary and Decisions
-------------------------------------------------------------------------------

- Likert distribution: A probability mass function (pmf) over discrete Likert options (e.g., 1–5). We prefer a pmf (not a single score) because it captures uncertainty and supports realistic, human‑like response distributions and traditional survey metrics (mean, top‑2 box, etc.).
- Core approach: SSR (Semantic Similarity Rating). Elicit 1–2 sentence rationale, embed it, compute cosine similarity to 5 anchor statements (1–5), normalize to a pmf; average across multiple anchor sets to reduce lexical bias.
- Alternatives (planned as modules, not MVP):
  - FLR (Follow‑up Likert Rating): ask LLM to map rationale to 1–5; derive distribution via sampling.
  - Direct pmf elicitation: ask LLM to output its own pmf; then calibrate to anchors (temperature scaling/Dirichlet smoothing).
  - Pairwise/Comparative (Bradley‑Terry/Thurstone), MaxDiff, and Discrete Choice Experiments for advanced trade‑off and pricing (Phase 2+).
- Diversity: For MVP, within‑model sampling (multiple synthetic respondents via GPT‑5). Optionally estimate model‑provider variance by sampling a small canary share from other models (Anthropic, Google, xAI) and treating provider as a random effect for diagnostics.
- Minimal multi‑step rationale: Each step addresses a failure mode.
  1) Focused retrieval → reduces hallucination/overgeneralization.
  2) Textual elicitation → avoids center‑bias of direct ratings; richer explanations.
  3) SSR mapping → realistic distributions and stable alignment with human anchors.

-------------------------------------------------------------------------------
1) Acceptance Criteria (MVP)
-------------------------------------------------------------------------------

- Given {intent, audience, concept}, system returns:
  - A 5‑point Likert pmf, mean, top‑box metrics, and 95% bootstrap CIs.
  - N free‑text rationales (short, persona‑consistent) and top themes.
  - Segment cuts (if multiple personas) and an aggregate weighted result.
- Uses GPT‑5 via Responses API for elicitation; uses embeddings for SSR (e.g., text-embedding-3-small or equivalent).
- Deterministic anchors and versioned prompts; results reproducible with fixed seed and inputs.
- Parallelizable to at least 2,000 synthetic respondents in < 2 minutes on commodity infra (subject to provider rate limits).
- Logging, cost metering, and minimal guardrails (content/empty response regeneration) in place.

-------------------------------------------------------------------------------
2) Data and Retrieval (Focused Context)
-------------------------------------------------------------------------------

[2.1] Concept ingestion (MVP)
- Input: URL or text or file upload (image/PDF/text).
- Extract: title, short description, features/benefits, price if visible; capture image URL(s) for prompt.
- Persist: raw artifact, parsed summary, provenance.

[2.2] Optional context (Phase 1.5)
- Competitor snapshot: top comparable items (name, price band, key features).
- Reviews summary: top pros/cons and star rating distribution.
- Regionalization: currency, category norms.

Deliverables
- Parser util with URL/text modes; simple HTML extraction with safe defaults.
- Data schema for concept artifacts and summaries.

-------------------------------------------------------------------------------
3) Elicitation and SSR Mapping
-------------------------------------------------------------------------------

[3.1] Prompts
- Persona system prompt: “Impersonate a [age/gender/income/region/usage] consumer. Answer survey questions concisely and realistically. Avoid extremes unless justified by the stimulus.”
- Intent question template (examples):
  - Purchase intent: “How likely would you be to purchase this product?”
  - Relevance: “How relevant is this concept to you?”
- Output style: 1–2 sentences; no numeric labels; short, concrete.

[3.2] Responses API integration (core = GPT‑5)
- Use Responses API with JSON mode for reliable parsing (fields: rationale_text).
- Temperature: 0.5 (start), max_tokens small (~80), parallel requests with backoff.

[3.3] SSR mapping algorithm
- Inputs: rationale_text; anchor bank A consisting of K=5 anchors per Likert point; M anchor sets per intent (MVP M=3; target M=6).
- Steps per response:
  1) Embed rationale_text → vector r.
  2) For each anchor set m in 1..M and each Likert point k in 1..5:
     - Embed anchor a_{m,k} (precomputed) → vector a.
     - s_{m,k} = max(cosine(r, a), 0) + epsilon (epsilon ~ 1e-6).
     - p_{m,k} = s_{m,k} / sum_k s_{m,k}.
  3) pmf_k = average_m p_{m,k}.
- Outputs: pmf (length 5), mean = sum(k * pmf_k), top2box = pmf_4 + pmf_5.
- CIs via bootstrap across respondents.

[3.4] Anchor banks
- Per intent, define 5 anchors per Likert point and at least 3 phrasings per point (3–6 sets total).
- Example (purchase intent; illustrative):
  - 1: “I definitely would not buy it.”
  - 2: “I probably would not buy it.”
  - 3: “I might or might not buy it.”
  - 4: “I probably would buy it.”
  - 5: “I definitely would buy it.”
- Store anchors in versioned YAML with locale variants.

Deliverables
- `ssr/engine` with: elicit(), map_to_likert_pmf(), aggregate().
- Anchor YAML and embed cache; unit tests on mapping monotonicity.

-------------------------------------------------------------------------------
4) Sampling, Segmentation, and Weighting
-------------------------------------------------------------------------------

[4.1] Synthetic sample design
- For each persona (audience spec), draw N respondents (MVP default N=200/persona).
- Control variance with temperature and minor persona trait jitter (within bounds).

[4.2] Segments and weighting
- Aggregate across personas using provided population weights or equal weights if unspecified.
- Provide cuts by age/income/region or custom tags.

[4.3] Parallelization and idempotency
- Concurrency: configurable (e.g., 64–256 in flight), retries with jitter, dedupe on request hash.

Deliverables
- Orchestrator that runs respondents in parallel, gathers rationales, maps via SSR, and aggregates with bootstrap CIs.

-------------------------------------------------------------------------------
5) API, Storage, and Observability
-------------------------------------------------------------------------------

[5.1] API (FastAPI)
- POST `/simulate`: body { intent, intent_question?, persona(s), concept {url|text|file_ref}, n, model="gpt-5", embedding_model, anchor_bank_version }
- Returns { pmf, mean, ci, top2box, segments[], sample_n, rationales[], metadata }.
- GET `/export/:job_id`: CSV/Parquet export.

[5.2] Storage
- Postgres for metadata/results; object store for artifacts; simple cache for embeddings.

[5.3] Observability
- Request/response traces (redact PII), provider cost/tokens, latency histograms, error breakdowns.

Deliverables
- Minimal service with one route, logging, and config via env.

-------------------------------------------------------------------------------
6) Evaluation, Calibration, and Safety
-------------------------------------------------------------------------------

[6.1] Offline evaluation
- If client has historical surveys: compute correlation in means and KS similarity of distributions; report by concept and segment.
- Without ground truth: internal consistency checks (self‑agreement across paraphrased anchors), sensitivity tests (price changes, feature toggles), and sanity baselines.

[6.2] Calibration
- If human labels exist: tune epsilon or apply simple temperature scaling to align top‑box rates.
- Monitor drift across model/provider updates; lock versions in metadata.

[6.3] Safety and quality
- Content safety checks; refusal detection; re‑prompt with gentler instruction.
- Enforce max rationale length; strip numerics in rationale to avoid contaminating SSR.

Deliverables
- Eval harness with metrics, reports, and acceptance thresholds.

-------------------------------------------------------------------------------
7) Alternatives and Extensions (Planned)
-------------------------------------------------------------------------------

- FLR: ask model to map rationale to 1–5; derive pmf via sample histogram; compare to SSR.
- Direct pmf elicitation: model outputs pmf + rationale; then calibrate to anchors.
- Pairwise preferences (Bradley‑Terry/Thurstone) and MaxDiff for attribute trade‑offs.
- Discrete Choice Experiments for price/feature utilities and simple demand curves.

-------------------------------------------------------------------------------
8) Model Strategy (Diversity and Providers)
-------------------------------------------------------------------------------

- Core: GPT‑5 via Responses API (configurable model name).
- Within‑model diversity: multiple respondents with controlled temperature and slight persona jitter.
- Cross‑model diversity (optional): sample 10–20% from other providers to estimate provider variance; use as diagnostic, not ensemble, in MVP.
- Fallback: configurable model list with health checks.

Deliverables
- Provider abstraction with pluggable backends and per‑provider rate‑limit configs.

-------------------------------------------------------------------------------
9) Milestones and Step‑by‑Step Tasks
-------------------------------------------------------------------------------

M1 — Core SSR Engine (Week 1)
- [ ] Create anchor YAML for purchase intent (3 sets, en‑US).
- [ ] Implement embeddings cache and cosine sim.
- [ ] Implement SSR mapping with multi‑set averaging and epsilon smoothing.
- [ ] Unit tests: monotonicity wrt known texts; pmf sums to 1; stability across sets.

M2 — Elicitation via GPT‑5 (Week 1)
- [ ] Implement Responses API client with JSON output schema { rationale_text }.
- [ ] Persona system prompt + intent templates; fixtures for 3 example personas.
- [ ] Retry/backoff and max concurrency settings; redact logs.

M3 — Orchestration and Aggregation (Week 1–2)
- [ ] Orchestrator to run N respondents/persona in parallel; seed control.
- [ ] Bootstrap CIs for mean and top‑box; segment aggregation and weights.
- [ ] Simple theme extraction (top n‑grams or small LLM summarizer).

M4 — API Surface (Week 2)
- [ ] FastAPI endpoint POST `/simulate` with request validation.
- [ ] Persist inputs, outputs, and provenance to Postgres.
- [ ] CSV/Parquet export endpoint; basic auth.

M5 — Retrieval (Week 2–3)
- [ ] URL/text ingestion; HTML parser; artifact store.
- [ ] Optional competitor and reviews stub; configuration flags.

M6 — Evaluation and Calibration (Week 3)
- [ ] Eval harness to compute mean correlation and KS similarity (if ground truth available).
- [ ] Sensitivity tests (price/feature toggles) and drift reports.
- [ ] Optional top‑box calibration if human labels exist.

M7 — Reliability, Cost, and Ops (Week 3–4)
- [ ] Token/cost metering; request tracing; error budgets.
- [ ] Health checks and fallback models; rate‑limit adaptation.
- [ ] Documentation and runbooks.

-------------------------------------------------------------------------------
10) Implementation Notes and Snippets (for later execution)
-------------------------------------------------------------------------------

- Responses API (pseudo‑code)
  - Input: persona, concept_context, intent_question
  - Output: rationale_text (1–2 sentences)
  - Model: configurable (default "gpt-5")

- SSR math
  - Cosine similarity with ReLU + epsilon to avoid zeroing pmf.
  - Average across anchor sets; store per‑set pmfs for diagnostics.

- Anchors governance
  - Versioned YAML; locale‑specific; human review; unit tests to catch inverted anchors.

- Guardrails
  - If rationale is too short/empty/off‑topic, regenerate with a single retry at lower temperature.

-------------------------------------------------------------------------------
11) Risks and Mitigations
-------------------------------------------------------------------------------

- Overconfidence from a single provider → Mitigation: provider diagnostics and fallback.
- Lexical bias to anchors → Mitigation: multiple anchor sets; future supervised calibration.
- Cost spikes → Mitigation: cap N per persona, cache embeddings, summarize long inputs.
- Distribution collapse → Mitigation: SSR over FLR/direct; monitor KS similarity and entropy.

-------------------------------------------------------------------------------
12) What’s Next After MVP
-------------------------------------------------------------------------------

- Add DCE/MaxDiff modules for pricing/attribute utilities.
- Add human‑in‑the‑loop miniature panels for anchor calibration.
- Add lightweight UI dashboard and multi‑tenant auth.

