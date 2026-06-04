# CLAUDE.md

Guidance for working in the LeagueQL repository.

## Requirements docs come first

LeagueQL maintains **live feature requirements documents** under
[`docs/requirements/`](docs/requirements/README.md). They are the source of truth for what
each feature does and are organized into backend (`BE-xxx`), frontend (`FE-xxx`), and
extension (`EXT-xxx`) features — frontend and backend features are kept in separate files.

**Before writing or changing any code, you MUST:**

1. **Find the relevant feature doc(s)** in `docs/requirements/` (start from the
   [index](docs/requirements/README.md)).
2. **Review** the description, edge cases, and acceptance criteria so the change fits the
   intended behavior.
3. **Update the doc first** when the change adds, removes, or alters behavior — edit the
   description, edge cases, and/or acceptance criteria to reflect the new intended behavior
   **before** implementing it. The doc and the code must land in the same change.
4. **Create a new doc** for any genuinely new feature: add `<ID>-<kebab-title>.md` in the
   appropriate subdirectory and link it in `docs/requirements/README.md`. Use the next free
   ID in that prefix and never reuse a retired ID.

If a code change reveals that a doc is wrong or out of date, fix the doc as part of that
change. Requirements docs should never silently drift from the code.

### Each feature doc contains
- Feature ID + title
- Description (and scope)
- Edge cases
- Acceptance criteria

## Code quality (linting & formatting)

Always lint and format code after changing it, using the project's configured tooling.

### Python
Run the same Ruff linter and formatter defined in
[`.pre-commit-config.yaml`](.pre-commit-config.yaml):

```bash
pipenv run ruff check --fix .   # lint (and auto-fix)
pipenv run ruff format .        # format
```

### TypeScript / frontend
Run Prettier and check ESLint using the scripts in
[`frontend/package.json`](frontend/package.json) (from the `frontend/` directory):

```bash
npm run format:fix   # Prettier formatter (prettier --write .)
npm run lint         # ESLint check (eslint .)
```

Use `npm run format:check` (`prettier --check .`) when you only want to verify formatting
without writing changes.

## Tests come with the code

**On every code change, evaluate whether new component tests are needed or existing ones must
be updated** — and add/update them in the same change. A change is not complete until its tests
reflect the new behavior.

- **Frontend component tests** live beside each feature under `frontend/src/features/**/__tests__/`
  as jest-cucumber pairs — a `*.feature` file (Gherkin scenarios) and its `*.steps.test.tsx`
  step definitions, driven by MSW-mocked API responses. When you add or change a component's
  behavior, user-visible state, or how it handles an API response (success, `4xx`, `5xx`,
  loading, empty), add or update the corresponding scenario + steps. Run them with
  `npx vitest run <path>` (or `npm run test`) from `frontend/`.
- **Backend component tests** live under [`tests/component/`](tests/component/CLAUDE.md) as
  Behave Gherkin pairs — `features/*.feature` + `steps/*.py` — exercising a whole component (the
  FastAPI app, the Stripe webhook, the onboarder→processor chain, …) with every **external**
  dependency (the platform API, Stripe, Lambda) mocked but real DynamoDB/S3 behavior via `moto`.
  When you add or change an endpoint/handler's behavior or how components interact across a
  DynamoDB/S3 boundary, add or update the matching scenario + steps. Run with
  `pipenv run behave tests/component`.
- **Backend unit tests** live under `tests/unit/`, mirroring `src/` (see
  [`tests/CLAUDE.md`](tests/CLAUDE.md)). Keep coverage close to 100%, including error paths.
- When a behavior spans tiers (e.g. a new backend error status the UI must surface, or a
  recovery path crossing a DynamoDB boundary), update **all** the affected layers — backend
  unit, backend component, and frontend component tests.

## Related references
- API contract: [`docs/api/openapi_spec.yaml`](docs/api/openapi_spec.yaml) — keep in sync
  with backend API changes.
- Data model: [`docs/db/dynamodb_spec.md`](docs/db/dynamodb_spec.md) — keep in sync with
  precomputed view / item schema changes.

## Tech stack (orientation)
- **Backend:** FastAPI + Python on AWS API Gateway + Lambda; data in DynamoDB, raw payloads
  in S3; DuckDB used for transforms. Source under `src/`.
- **Frontend:** React + TypeScript (Vite), hosted on Cloudflare Pages. Source under
  `frontend/src/`, organized by feature in `frontend/src/features/`.
- **Extension:** Chrome extension under `extension/` for auto-filling ESPN cookies.
- **Infrastructure:** Terraform under `infrastructure/`.
