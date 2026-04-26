# Contributing Guidelines
Follow the instructions below to set up your development environment and contribute to the project.

## Environment Setup

### Loading Environment Variables
Before running the API locally, you need to load the environment variables from the `src/api/.env` file into your shell session. Run the following command from the project root:

```bash
export $(grep -v '^#' src/api/.env | xargs)
```

### Running the API
After loading environment variables, start up the uvicorn server:

```bash
pipenv run uvicorn src.api.main:app --reload
```

## Contributing

### Writing Tests with Claude

Unit tests for this project are written using the `/write-unit-tests` slash command in Claude Code. The command follows the rules defined in `tests/unit/CLAUDE.md` and enforces:

- 100% line and branch coverage
- Clean ruff formatting and linting
- No real network calls, disk writes, or shared state mutations

**Usage:**

```
/write-unit-tests @onboarder/<module>.py
```

For example, to generate tests for `espn_client.py`:

```
/write-unit-tests @onboarder/espn_client.py
```

Claude will create `tests/unit/test_<module>.py`, run the full fix loop (format → lint → coverage), and only finish when all four gates in `CLAUDE.md` are green.

### Running Tests

Install dev dependencies first:

```bash
pipenv install --dev
```

Run the full test suite:

```bash
pipenv run pytest tests/unit
```

Run with branch coverage for a specific module:

```bash
pipenv run pytest --cov=<module> --cov-branch --cov-report=term-missing tests/unit
```

Replace `<module>` with the module name (e.g. `espn_client`, `handler`, `transformer`).

Enforce the 100% coverage threshold:

```bash
pipenv run pytest --cov=<module> --cov-branch --cov-fail-under=100 tests/unit
```