# Dubious Engine

Spell check for sourcing. Give it a URL or a block of text; it pulls out the checkable claims, follows each claim's links one hop, and scores **how well the claim is sourced**, not whether it's true.

Each claim gets a 0–1 dubiousness score, reason codes explaining the score, and a level:

- **gray**: unsourced or vague attribution ("officials say"). Unverified, not wrong.
- **yellow**: weakly or circularly sourced.
- **red**: sourced to a known disinformation outlet. Reserved on purpose: a wrong red costs more trust than fifty missed yellows.

An LLM (Gemini) only *extracts* claims. Plain, inspectable rules do the judging, so every score can be traced to the line that produced it.

## Example

```bash
curl -s -X POST https://dubious-engine-bmbk6l3a7a-uw.a.run.app \
  -H 'content-type: application/json' \
  -d '{"source": "Officials say unemployment fell to 3.5% last month."}'
```

```json
TODO: {"source":"text","claims":[{"claim":"Unemployment fell to 3.5% last month.","score":0.75,"level":"gray","reasons":["HEARSAY"],"chains":[]}],"meta":{"model":"gemini-3.8-flash","tokens_in":139,"tokens_out":38,"cost_usd":0.000247,"cost_per_claim_usd":0.0002
```

## How it works

```
text or URL
   │
   ├─ fetch    page text, with each link's URL kept next to its words
   ├─ extract  Gemini returns claims as JSON (schema-constrained, temperature 0)
   ├─ resolve  follow each cited URL one hop; collect the domains it links to
   └─ score    rules over ontology/registry.json → score, reasons, level
```

## Reason codes

| Code | Fires when | Effect |
| --- | --- | --- |
| `SRC-NONE` | Claim cites no URL and names no source | Score 0.70, level gray |
| `HEARSAY` | No URL, attributed to "officials", "sources", "experts" and similar | Score 0.75, level gray |
| `SRC-TIER:<tier>` | Claim cites a URL | Base score from the best cited source's tier (primary 0.05 → disinfo 0.95) |
| `SRC-DISINFO` | A cited source is in the disinfo tier | Score ≥ 0.95, level red |
| `CHAIN-CIRC` | The page cites itself | Score ≥ 0.60 |
| `CHAIN-TERM:primary` | A non-primary citation links on to a primary source | −0.10 |
| `CHAIN-TERM:none` | A non-primary citation never reaches a primary source | +0.10 |
| `DATA-STALE` | The claim leans on data more than 5 years old | +0.10 |

Source tiers live in [`ontology/registry.json`](ontology/registry.json). The seed list is deliberately small; the structure is the point.

## Inference economics

Every response reports tokens, latency and cost, so cost per verified claim is measured, not guessed.

| Input | Tokens in / out | Latency | Cost per claim |
| --- | --- | --- | --- |
| One sentence | 139 / 38 | 2 s | $0.00025 |
| Wikipedia article | 5513 / 981 | 11 s | $0.007813 |

Model: `gemini-3.8-flash`, pinned rather than `-latest` so behavior and price only change when I change them. The obvious next cost lever is caching by content hash: a viral post would be paid for once.

## API

| Endpoint | Purpose |
| --- | --- |
| `POST /check` | Score a URL or text. Returns claims, reasons and a `check_id` |
| `POST /feedback` | Thumbs up or down on one claim: `{"check_id", "claim_index", "vote": "up"\|"down"}` |
| `GET /stats` | Total checks, cost per claim, average latency, feedback agreement rate |
| `GET /health` | Liveness check |

Interactive docs at `/docs` once it's running.

## Run it

Requires [uv](https://docs.astral.sh/uv/) and a Gemini API key.

```bash
git clone https://github.com/lindstromseth92-dotcom/dubious-engine.git
cd dubious-engine
cp .env.example .env          # then put your key in .env
uv sync
uv run uvicorn app.main:app --port 8080
```

Command line, no server: `uv run python -m dubious.cli "some text or a URL"`

Tests: `uv run ruff check . && uv run pytest -q`

## Deploy

Container: `docker build -t dubious-engine .`

Cloud Run (key stored in Secret Manager as `gemini-api-key`):

```bash
gcloud run deploy dubious-engine --source . --region us-west1 \
  --allow-unauthenticated --memory 512Mi --max-instances 2 \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest
```

## Scaling it out

The [`k8s-split`](https://github.com/lindstromseth92-dotcom/dubious-engine/tree/k8s-split) branch splits the service in two: an API that queues checks in Redis and returns immediately, and workers that run them. Manifests in `k8s/` run it on a local [kind](https://kind.sigs.k8s.io/) cluster. Workers scale independently of the API, and queued checks survive a period with zero workers.

## Limitations

- The source registry is small and hand-seeded.
- One-hop link crawl only; no multi-hop chains or cross-outlet circular-sourcing detection yet.
- Many news sites block automated fetches, especially from cloud IPs. In the planned browser extension, the page text comes from the reader's own browser, so only citations need fetching.
- Feedback is stored in SQLite on the container's disk, so it resets when Cloud Run replaces the instance.
- No benchmark yet. The scores haven't been validated against a labeled set.

## Roadmap

A labeled benchmark to validate the rules, a content-hash cache, fact-check lookups (ClaimReview), multi-hop chains, and a browser extension that draws the squiggles on Reddit.

## License

MIT