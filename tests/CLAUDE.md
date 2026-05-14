# Unit Tests

## Agent workflow for writing tests

Follow these steps in order when writing or modifying unit tests:

1. **Write tests** — create or update test files under `tests/unit/`, mirroring the source layout. Follow the structure, modularity, and coverage standards below.

2. **Validate tests pass**
   ```bash
   pipenv run pytest tests/unit/
   ```
   All tests must pass with no errors or failures before proceeding.

3. **Validate coverage** — run with coverage and confirm close to 100% line and branch coverage for the module(s) under test:
   ```bash
   pipenv run pytest tests/unit/ --cov=src --cov-report=term-missing --cov-fail-under=90
   ```
   Identify any uncovered lines or branches and add tests to cover them.

4. **Run Ruff linter and formatter** — test code must be lint- and format-clean:
   ```bash
   pipenv run ruff check --fix tests/
   pipenv run ruff format tests/
   ```
   Fix any remaining issues that `--fix` did not auto-resolve before proceeding.

5. **Run pre-commit checks** — simulate what CI will validate on commit:
   ```bash
   pipenv run pre-commit run --files $(git diff --name-only HEAD)
   ```
   Resolve all hook failures before marking the task complete.

---

## Running tests

Run the full test suite from the project root using pipenv:

```bash
pipenv run pytest tests/unit/
```

Run a specific test file:

```bash
pipenv run pytest tests/unit/api/test_some_module.py
```

Run with coverage:

```bash
pipenv run pytest tests/unit/ --cov=src --cov-report=term-missing
```

## Framework
- Use **pytest** for all tests. Only reach for `unittest` constructs (e.g., `unittest.mock`) when pytest has no equivalent (e.g. mocking and patching).
- **Do not modify `sys.path` in test or conftest files.** Use `importlib.util.spec_from_file_location` to load Lambda modules that share common filenames (`handler.py`, `utils.py`) across source directories. Register the loaded module in `sys.modules` before tests run and clean it up after.

## Modularity via fixtures
- Define shared setup (mock clients, env vars, sample data) as **pytest fixtures** in `conftest.py`, not repeated per-test.
- Fixtures that must always run (e.g., patching env vars) should use `autouse=True`.
- Use `side_effect` lists on mocks when a single mock needs to return different values across sequential calls within one test.

## Code quality
- All test code must pass **Ruff** linting with no errors (`ruff check`).
- Unit tests should achieve **close to 100% line and branch coverage**. Add tests for every reachable branch including error paths, empty inputs, and edge cases.

## Structure
- Mirror the source layout: `tests/unit/api/` for `src/api/`, etc.
- Group related tests in classes (e.g., `TestLookupLeague`) so fixtures and parametrize decorators are scoped clearly.
- Use `pytest.mark.parametrize` for tests that differ only in input/expected output.
