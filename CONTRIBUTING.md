# Contributing to DataGuard AI

Thanks for taking an interest in DataGuard AI. Contributions that improve data-quality checks, observability, documentation, or test coverage are welcome.

## Local setup

1. Fork the repository and create a focused branch.
2. Create a virtual environment and install the project with development dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. Run the full suite before opening a pull request:

   ```bash
   pytest -v
   ```

## Pull request guidelines

- Keep each pull request focused on one improvement.
- Add or update tests when behavior changes.
- Keep public API changes documented in the README.
- Never commit credentials, production datasets, or generated database files.

## Reporting issues

Use a clear title, expected behavior, actual behavior, and a minimal reproducible example. For data-related issues, provide only anonymized or synthetic data.
