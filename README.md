# BharatSe API

The service layer for BharatSe, the market linkage and cataloguing platform for
government supported artisans. SIH 2026, problem statement 26090.

This is the only thing that touches the database. The Flutter app and the
ministry dashboard both talk to it over HTTPS and neither of them calls an AI
provider directly, which is what lets us swap a model later without shipping an
app update to a phone that may never receive one.

## Running it

```bash
make install          # python3.12 venv, editable install
cp .env.example .env
make keys             # Craft Passport signing keypair, paste into .env
make up               # Postgres with pgvector, on 5432
make migrate
make dev              # http://localhost:8000/docs
```

Python is pinned to 3.12 on purpose. sentence-transformers does not classify
above 3.13 and CLIP embeddings are on the critical path for search.

## Layout

```
app/
  core/        settings, logging, JWT, the error types we raise deliberately
  db/          engine and session
  models/      SQLModel tables. Anything missing from models/__init__.py
               silently never gets a migration.
  schemas/     request and response shapes
  api/v1/      routes, one file per surface
  services/
    ai/        listing generation behind a provider interface
    images/    background removal and the e commerce studio pass
    pricing/   the price band, see below
    passport/  Ed25519 signing and verification
    search/    CLIP embeddings for pgvector
alembic/       migrations
scripts/       key generation, seed data download
```

## Pricing

Three layers, in `app/services/pricing/`.

**The floor** (`floor.py`) is materials, plus hours at a fair wage, plus a
small overhead. It is arithmetic and not learned, deliberately. A model trained
on market prices learns what artisans are currently paid, which is the thing
this programme exists to change. The hours figure comes from the artisan
herself, which is why the app makes it an editable field.

**The band** (`model.py`) is LightGBM with a quantile objective, three
boosters at P10, P50 and P90. LightGBM rather than XGBoost because the quantile
objective is native, so the band comes out of the model rather than being
bolted on, and it is faster on small tabular data.

**Reconciliation** (`service.py`) puts them together, and the floor always
wins. The market may push a price up. Nothing in this system can push it below
the maker's wage. `validate_price` enforces the same rule server side before a
listing is published, so the guarantee does not live only in the app.

Three things that will bite you if you touch this code:

- `alpha` must be passed explicitly. It defaults to 0.9, so omitting it
  silently trains three identical P90 models and the band collapses.
- Quantiles are fit independently, so P10 can land above P90 on an individual
  row. `predict` sorts each row. A P10 above a P90 on stage destroys the demo.
- On macOS, `brew install libomp` first. LightGBM's wheel does not bundle
  OpenMP, so `import lightgbm` fails at dlopen with an error that never
  mentions LightGBM. Pricing degrades to the cost based band rather than
  returning a 500, and there are tests for that, but you will want the model.

Quote pinball loss, not RMSE. If asked whether the intervals are calibrated,
answer with empirical coverage on a holdout, which should sit near 0.80 for a
P10 to P90 band. Both helpers are in `model.py`.

### Training

```bash
./scripts/fetch_seed_data.sh
make train
```

The seed data is a public Flipkart product dump from PromptCloud, CC BY SA 4.0,
so attribute it. Roughly 1,700 craft adjacent rows. It was crawled in 2016, so
prices are a decade stale, and we say so rather than hiding it. The model is
used for structure, meaning how material and category move price relative to
each other, not for absolute rupee truth. Layer a small current price table on
top for the crafts actually being pitched.

## Language

`LISTING_PROVIDER` selects the path, and every provider implements the same
interface so switching one is a config change and not a rewrite.

**Gemini** is the default. One call takes the artisan's audio and returns the
finished listing, both languages in the same pass, so the Hindi is not a
machine translation of the English. This replaces a three step chain of speech
to text, then translation, then generation.

**Bhashini** is the first fallback and a scoring point in its own right, since
Dhruva hosts the AI4Bharat models and it is MeitY's own platform. The two step
config call is made once at boot and cached, and re-fetched on a 401.

**Sarvam** is transcription only, and its synchronous endpoint caps at 30
seconds, so real voice notes need chunking.

The listing schema is validated with Pydantic and not trusted. Neither Gemini
nor Claude honours length or item count constraints declared in a schema, so
those are enforced in validators.

## Images

`REMBG_MODEL` must stay set. rembg's own default is now BRIA RMBG, which
requires a paid commercial agreement, so calling `remove()` without a session
ships a model we are not licensed to ship on a government problem statement.
`isnet-general-use` is Apache 2.0 and good on textile and jewellery edges.
There is a test asserting the default never drifts.

## Craft Passport

Ed25519, raw 32 byte keys, plain RFC 8032, so the Dart client interoperates.

The QR carries the encoded bytes that were signed plus the signature. Do not
re-serialise the payload on the client to verify it: Dart's `jsonEncode` and
Python's `json.dumps` differ in key order and spacing, so a re-serialised
payload fails verification even when the signature is correct.

The public key is pinned in the app bundle and is never read from the QR. An
attacker would otherwise ship their own key next to their own signature.

## Offline sync

`POST /products/sync` drains the phone's outbox. It upserts on `client_id`,
which the device generates, so retries are safe. Every offline failure a judge
will actually try, meaning airplane mode, tapping save three times, then
reconnecting, is a duplicate row problem rather than a sync problem.

## Search

CLIP puts an image and a text query into the same 512 dimensional space, so
`GET /search?q=` and an image upload run identical SQL downstream.

Use HNSW, not IVFFlat. IVFFlat must be built after data exists, so creating it
in a migration on an empty table produces meaningless centroids and silently
wrong neighbours.

## Tests

```bash
make test
```

Covers the pricing rules, the degraded paths when the model cannot load,
passport signing and tampering, listing validation, settings parsing, and that
the app boots and serves its contract without a database present.
