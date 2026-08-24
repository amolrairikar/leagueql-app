# CLAUDE.md

Guidance for working in the LeagueQL repository.

## Specs come first (OpenSpec)

LeagueQL manages requirements with **[OpenSpec](https://github.com/Fission-AI/OpenSpec)**.
The source of truth for what each feature does lives under
[`openspec/specs/`](openspec/specs/), organized by domain into capability specs at
`openspec/specs/{backend,frontend,extension}/<capability>/spec.md`. Each spec has a
`## Purpose` and a `## Requirements` section of `### Requirement:` statements (each a single
`SHALL`), every one backed by at least one `#### Scenario:` written in WHEN/THEN form. Run the
CLI with `npx @fission-ai/openspec@latest <command>` (no install needed).

**Before writing or changing any code, you MUST:**

1. **Read the relevant capability spec(s)** under `openspec/specs/`. Browse them with
   `openspec list --specs` and `openspec show <capability>`.
2. **Review** the requirements and scenarios so the change fits the intended behavior.
3. **For any change to externally observable behavior, create an OpenSpec change first**
   (before implementing) and follow the propose → apply → archive workflow:
   - Propose with `/opsx:propose` (or `openspec new change "<kebab-name>"`). A change bundles
     `proposal.md`, delta specs under `changes/<name>/specs/<capability>/spec.md` using
     `## ADDED / MODIFIED / REMOVED Requirements`, `design.md`, and `tasks.md`.
   - Implement with `/opsx:apply`; the code and the change land together.
   - When the work is complete, `/opsx:archive` merges the delta into `openspec/specs/` and
     files the change under `openspec/changes/archive/`.
   - Validate with `openspec validate --all` (or `--specs`) — every requirement needs a `SHALL`
     statement and ≥1 scenario, and no reference may dangle.
4. **Add a brand-new capability** via the same change workflow: the delta's `## ADDED
   Requirements` (plus a `## Purpose`) seeds a new `openspec/specs/<domain>/<capability>/spec.md`
   at archive time. Name capabilities in kebab-case under the right domain
   (`backend`/`frontend`/`extension`).

Small, non-behavioral edits (typos, wording) may be made directly in a `spec.md`. If a code
change reveals a spec is wrong or out of date, fix the spec as part of that change — specs must
never silently drift from the code.

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
- Architecture diagram: [`docs/architecture/`](docs/architecture/README.md) — diagram-as-code
  (`architecture_diagram.py`) rendered to `leagueql_architecture.png`. **When a new component
  is deployed (Lambda, Fargate task, queue, data store, scheduled job, external integration,
  worker, …) or an existing one is removed/rewired, update `architecture_diagram.py` and
  regenerate the PNG in the same change** (`pipenv run python docs/architecture/architecture_diagram.py`).

## Tech stack (orientation)
- **Backend:** FastAPI + Python on AWS API Gateway + Lambda; data in DynamoDB, raw payloads
  in S3; DuckDB used for transforms. Source under `src/`.
- **Frontend:** React + TypeScript (Vite), hosted on Cloudflare Pages. Source under
  `frontend/src/`, organized by feature in `frontend/src/features/`.
- **Extension:** Chrome extension under `extension/` for auto-filling ESPN cookies.
- **Infrastructure:** Terraform under `infrastructure/`.
