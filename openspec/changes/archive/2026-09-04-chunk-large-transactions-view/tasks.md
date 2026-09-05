## 1. Processor: chunked writes

- [x] 1.1 Add a `chunked: bool = False` field to `KeySchema` in `src/processor/handler.py`; verify existing schema construction still type-checks and unaffected schemas keep `chunked=False`.
- [x] 1.2 Add a size-bounded chunk splitter (target ~300 KB per item, conservative headroom under 400 KB) that measures each sanitized row's serialized size and packs rows into chunks, never emitting an empty chunk and emitting an over-cap single row as its own chunk; verify with a unit test covering: many small rows split into >1 chunk, a season that fits one chunk, and each emitted chunk's payload under the cap.
- [x] 1.3 Update `dataframe_to_dynamo_items` so that when `schema.chunked` is set it emits one item per chunk with SK `f"{sk}#{index:04d}"` (zero-padded), and otherwise emits exactly one item per sort key as before; verify a unit test asserts non-chunked schemas produce byte-identical items to the current behavior and chunked schemas produce ordered `#0000`, `#0001`, ... SKs.
- [x] 1.4 Set `chunked=True` on `TRANSACTIONS_SCHEMA` (leave all other schemas unchanged); verify a unit test that processing a Sleeper league with transactions writes `TRANSACTIONS#{season}#{chunk}` items and no bare `TRANSACTIONS#{season}` item.
- [x] 1.5 Before writing a season's transaction chunks, delete any pre-existing bare `TRANSACTIONS#{season}` item for that season (delete-before-write, so a mid-run crash never leaves a bare item coexisting with chunks); the delete fires only for the seasons in `seasons_to_process`, leaving other seasons' items untouched. Verify a unit test asserts the bare-key delete is issued for each written season and precedes its chunk writes, and that seasons outside the process set get no delete.

## 2. API: prefix read for transactions

- [x] 2.1 In `src/api/routes.py`, route a suffixed `TRANSACTIONS#{season}` query through the paginated `begins_with` branch (prefix `TRANSACTIONS#{season}`, no trailing `#`) instead of `get_item`, keeping every other suffixed `queryType` on the exact `get_item` path; verify a unit test asserts transactions uses `query`/`begins_with` and, e.g., `STANDINGS#{season}` still uses `get_item`.
- [x] 2.2 Verify the transactions read concatenates every chunk's `data` in sort-key order and paginates `LastEvaluatedKey`; unit test with a mocked multi-page, multi-chunk response asserts a single flat, ordered list.
- [x] 2.3 Verify backward compatibility: a unit test where only a legacy bare `TRANSACTIONS#{season}` item exists returns its rows via the prefix query, and a season with no items returns `404`.

## 3. Component tests (round-trip)

- [x] 3.1 Add/extend a backend component scenario (`tests/component`) where a Sleeper league season has enough transactions to exceed a single item, and assert onboarding → `GET /leagues/{id}/query?queryType=TRANSACTIONS#{season}` succeeds (no `ValidationException`) and returns every row exactly once.
- [x] 3.2 Add a backend component scenario that reprocesses (`reprocess_all`) a season previously stored as a single bare `TRANSACTIONS#{season}` item and asserts the query returns each row exactly once (no duplication from a stale bare key).

## 4. Docs & spec sync

- [x] 4.1 Update `docs/db/dynamodb_spec.md` to describe the chunked `TRANSACTIONS#{season}#{chunk}` item shape; verify the described SK/attribute shape matches the processor output.
- [x] 4.2 Confirm `docs/api/openapi_spec.yaml` needs no change (same request/response contract) and note it in the change; verify by diffing the transactions request/response against the current schema.

## 5. Quality gates

- [x] 5.1 Run `pipenv run ruff check --fix .` and `pipenv run ruff format .`; verify clean.
- [x] 5.2 Run backend unit + component suites (`pipenv run pytest tests/unit`, `pipenv run behave tests/component`) and the existing frontend transactions tests; verify all pass.
- [x] 5.3 Run `openspec validate chunk-large-transactions-view --strict`; verify it passes.
