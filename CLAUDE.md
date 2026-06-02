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
