# Dynamic Pricing Engine — README

## Overview
An explainable hybrid pricing engine for marginalized artisans. Combines artisan production cost, comparable market prices, regional/craft context, demand signals, and LightGBM ML to recommend a competitive price range with a transparent reliability score.

## Project status
**MVP complete.** 140/140 tests green across 5 phases.

## Quick start

```powershell
cd dynamic-pricing-engine
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

python scripts\prepare_data.py     # data/processed/*.parquet
python scripts\train_model.py      # models/v1/*.{txt,json}
python scripts\evaluate_model.py   # docs/eval_metrics.json
uvicorn src.api.main:app --reload  # http://127.0.0.1:8000
```

## API
- `GET /health` — `{"status":"ok","model_version":"v1"}` or `503` if artefacts missing.
- `POST /pricing/predict` — see `docs/architecture.md` for request/response schemas.

## Layout
- `data/` — source CSVs (unchanged) and `processed/` (written by `scripts/prepare_data.py`).
- `src/data/` — loaders and validators.
- `src/features/` — pre-aggregated tables (market, demand, regional, material) + inference vector assembly.
- `src/pricing/` — cost engine, policy layer, reliability score.
- `src/models/` — preprocessing, baselines, training, evaluation, leakage audit, inference, artefacts.
- `src/schemas/` — Pydantic request/response schemas.
- `src/api/` — FastAPI service.
- `scripts/` — `prepare_data.py`, `train_model.py`, `evaluate_model.py`.
- `models/v1/` — written by `scripts/train_model.py` (4 LightGBM `.txt` + `manifest.json`).
- `docs/` — architecture, PRD, data doc, model card, evaluation, experiment log, learnings.
- `tests/` — 140 tests, 5 phases.

## Tech stack
- Python 3.11+, pandas, numpy, scikit-learn, LightGBM, joblib, Pydantic, FastAPI, uvicorn, pytest, httpx.

## Documentation
- `docs/project_context.md` — one-liner + scope
- `docs/PRD.md` — problem statement + success criteria
- `docs/tech_stack.md` — technologies and tradeoffs
- `docs/architecture.md` — final system overview
- `docs/folder_structure.md` — tree + phase status
- `docs/tasks.md` — checkbox tracker
- `docs/data_doc.md` — dataset schemas + processing
- `docs/eval.md` — evaluation protocol
- `docs/model_card.md` — model overview + limitations
- `docs/experiment_log.md` — per-phase experiments
- `docs/learnings.md` — what surprised us
- `docs/design_prompt.md` — UI/UX for the artisan-facing screen
