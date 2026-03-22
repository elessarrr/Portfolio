# Learnings From Errors

## 2026-03-22

- Error: Running `pytest -v` from project root failed with `ModuleNotFoundError: No module named 'app'`.
- Fix: Run tests with `PYTHONPATH=. pytest -v` so the project root is on Python's module search path.
- Prevention: Use `PYTHONPATH=. pytest -v` as the default local test command for this repository.
