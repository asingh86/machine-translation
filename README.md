# Translation API

A RESTful API serving machine translation using FastAPI and HuggingFace Transformers (Helsinki-NLP Opus-MT models).

## Quick Start

```bash
# Install dependencies
uv sync

# Run the API
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest -v

# Lint
uv run ruff check .
```

The API will be available at `http://127.0.0.1:8000`. Interactive docs at `http://127.0.0.1:8000/docs`.


## Project Structure

```
app/
├── main.py                         # FastAPI app, lifespan, middleware wiring
├── config.py                       # Pydantic settings from environment variables
├── logging_config.py               # Structured JSON logging setup
├── api/routes.py                   # Endpoint handlers
├── models/registry.py              # Model loading, registry, and inference
├── schemas/translation.py          # Request/response Pydantic models
└── middleware/
    ├── safeguard.py                # Content filtering (input + output)
    └── request_logging.py          # Request logging with correlation IDs
tests/
├── conftest.py                     # Shared fixtures
├── test_api.py                     # Integration tests
├── test_registry.py                # Model registry unit tests
└── test_safeguard.py               # Safeguard unit tests
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/translate` | Translate text between supported language pairs |
| GET | `/languages` | List available language pairs |
| GET | `/health/live` | Liveness probe (process alive) |
| GET | `/health/ready` | Readiness probe (models loaded, inference working) |

### Example Request

```bash
curl -X POST http://127.0.0.1:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, how are you?", "source_lang": "en", "target_lang": "es"}'
```

### Example Response

```json
{
  "translated_text": "Hola, ¿cómo estás?",
  "source_lang": "en",
  "target_lang": "es",
  "model_name": "Helsinki-NLP/opus-mt-en-es",
  "inference_time_ms": 42.15
}
```

## Design Decisions

**Model choice:** Helsinki-NLP Opus-MT models are small (~100MB each), fast, and well-supported. They offer a good tradeoff between quality and resource usage for a self-contained service.

**Registry pattern:** Models are loaded once at startup via a `ModelRegistry` class and stored on `app.state`. This avoids per-request loading and makes adding new language pairs a config change rather than a code change.

**Separation of health probes:** Liveness (`/health/live`) has no dependencies and always returns 200 if the process is running. Readiness (`/health/ready`) verifies models are loaded and runs a test translation. This distinction matters in orchestration environments like Kubernetes where liveness failures trigger restarts and readiness failures stop traffic routing.

## Further Questions

### 1. Can you serve multiple language options?

**Implemented.** The `ModelRegistry` is designed around a dictionary keyed by `(source_lang, target_lang)` tuples. Adding new language pairs is a configuration change in `config.py` — no code changes required. The `/languages` endpoint dynamically reflects all loaded pairs.

Currently configured: EN↔ES. Additional pairs (EN↔FR, EN↔DE) can be added by extending `default_language_pairs` in settings or via the `TRANSLATE_DEFAULT_LANGUAGE_PAIRS` environment variable.

**Tradeoff considered:** Loading all models at startup uses more memory but gives predictable latency. An alternative would be lazy loading (load on first request per pair), which saves memory at the cost of cold-start latency for the first user of each pair.

### 2. How could you continuously evaluate the performance of the model?

**Proposed approach (not yet implemented):**

Three complementary evaluation mechanisms, each catching different quality issues:

**Automated reference-based metrics** — A scheduled pipeline (cron/Airflow) runs translations from a versioned test dataset (e.g., Tatoeba EN-ES, 200-500 pairs per language) against the live API and computes: BLEU (n-gram overlap), chrF++ (character-level F-score, more robust for morphologically rich languages like Spanish), and COMET (learned metric trained on human judgments, correlates better with human quality assessment than BLEU). Scores are tracked over time — a sustained drop signals model regression or infrastructure issues.

**LLM-as-a-judge** — For a sampled subset of production translations, a separate LLM (e.g., GPT-4 or Claude) scores translation quality on dimensions like fluency, adequacy, and terminology accuracy on a 1-5 scale. This catches quality issues that reference-based metrics miss, such as grammatically correct but unnatural phrasing. Cost-effective as a periodic batch evaluation rather than per-request.

**Human annotation** — A small random sample of translations is periodically reviewed by bilingual annotators using a structured rubric (adequacy, fluency, errors). This serves as the ground truth that calibrates both automated metrics and LLM-as-a-judge. User feedback corrections (see Q5) supplement this by providing real-world quality signals at no annotation cost.

**Drift detection via proxy metrics** — Monitor operational signals that don't require reference translations: average output length relative to input length, inference time distribution, and safeguard flag rates. Sudden shifts in these proxies can indicate model or data issues before quality metrics catch them.

### 3. How might this work in practice where multiple calls could be made to the endpoint at the same time?

**Implemented.** Three mechanisms handle concurrency:

- **`asyncio.to_thread`** offloads CPU-bound model inference to a thread pool, preventing it from blocking the async event loop. This allows the API to continue accepting and routing requests while inference runs. PyTorch releases the GIL during tensor operations, so threads provide some real parallelism for this workload.
- **`asyncio.Semaphore`** limits concurrent inferences to a configurable maximum (default: 4) to prevent memory exhaustion. Each model holds ~100MB in memory, and concurrent inferences increase peak memory usage.
- **`asyncio.wait_for`** enforces a request timeout (default: 30s), returning HTTP 504 if inference takes too long.

**Production scaling considerations:** For higher throughput, the most effective approach is running multiple uvicorn workers (`--workers N`), each with its own process and GIL. This provides true parallelism at the cost of duplicated model memory. Beyond that, a task queue (Celery + Redis) or dedicated model serving infrastructure (Triton, TorchServe) would decouple the API from inference entirely.

### 4. How would you monitor this translation service in production?

**Implemented.** Structured JSON logging via `python-json-logger` provides machine-parseable log lines for every request and translation. Each log entry includes: timestamp, request ID (correlation), HTTP method, path, status code, response duration, and for translations specifically: language pair, input/output lengths, inference time, and model name.

Request correlation IDs are generated per-request and returned in the `X-Request-ID` response header, allowing end-to-end request tracing.

**Additional monitoring that would be added in production:**
- **Prometheus metrics** via `prometheus-fastapi-instrumentator`: request count and latency histograms by endpoint, translation count by language pair, safeguard flag counts, model inference duration histograms.
- **Alerting** on error rate spikes, latency P99 breaches, and readiness probe failures.
- **Dashboard** (Grafana) showing request volume, latency distribution, error rates, and model performance over time.

### 5. How can you incorporate end user feedback into the model?

**Proposed approach (not yet implemented):**

A `POST /feedback` endpoint would accept: original text, model output, user-suggested correction (optional), rating (1-5), and free-text comment. Feedback would be stored and used in three ways:

- **Evaluation dataset curation:** User corrections become test cases — if a user provides a better translation, that pair can be added to the evaluation dataset (Q2), strengthening automated quality checks over time.
- **Fine-tuning data:** Accumulated corrections provide supervised training pairs for periodic fine-tuning of the base models. This requires careful data quality filtering — not all user corrections are improvements.
- **Model selection / A/B testing:** Ratings across language pairs can inform which model variant to serve. If a fine-tuned model consistently outscores the base model in user ratings, it can be promoted.

### 6. How could you guard against inappropriate inputs or outputs?

**Implemented.** The `Safeguard` class provides layered protection:

- **Input validation:** Minimum and maximum text length (configurable), whitespace-only rejection.
- **Content filtering:** Language-specific blocklist with word-boundary matching (`\b`) to avoid false positives (e.g., "assistant" does not trigger on "ass"). Applied to both input and output, since models can generate inappropriate content even from clean input.
- **Logging:** Flagged content is logged for review without exposing the actual text in the response, balancing auditability with security.

**Production enhancements:**
- Replace the static blocklist with a lightweight toxicity classifier (e.g., `detoxify`) for better coverage and fewer false negatives.
- Add language detection on input (e.g., `langdetect`) to verify the claimed source language matches the actual text.
- Rate limiting per client to prevent abuse.

## Configuration

All settings are configurable via environment variables prefixed with `TRANSLATE_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSLATE_LOG_LEVEL` | `INFO` | Logging level |
| `TRANSLATE_MODEL_DIR` | `models_cache` | HuggingFace model cache directory |
| `TRANSLATE_MAX_INPUT_LENGTH` | `5000` | Maximum input text length |
| `TRANSLATE_MAX_CONCURRENT_REQUESTS` | `4` | Concurrent inference limit |
| `TRANSLATE_REQUEST_TIMEOUT_SECONDS` | `30` | Per-request timeout |

## CI

GitHub Actions (to be implemented) runs on every push to `main` and on PRs: linting (ruff), tests (pytest), and Docker image build verification.