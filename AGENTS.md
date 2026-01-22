# Repository Guidelines

## Project Structure & Module Organization
- `main.py` is the entry point when running via `python main.py`.
- Core modules live at repo root: `mc3000_gui.py`, `mc3000_usb.py`, `mc3000_protocol.py`, `mc3000_config.py`, `mc3000_profiles.py`, `mc3000_graphs.py`, `mc3000_backup.py`.
- `data/` holds device-related reference data (e.g., `data/factory_defaults_fw123_reference.json`).
- `docs/` contains protocol references and examples (`docs/mc3000.java`, `docs/mc3000usb.java`).
- `build/` and `*.egg-info/` are generated artifacts; avoid editing.

## Build, Test, and Development Commands
- `pip install .` installs the package and console scripts (`mc3000-gui`, `mc3000-backup`).
- `pip install .[dev]` installs developer tooling (pytest/black/mypy).
- `mc3000-gui` runs the GUI entry point.
- `python main.py` runs the GUI directly without installing.

## Coding Style & Naming Conventions
- Python code uses 4-space indentation and PEP 8 naming (snake_case for functions/modules, CapWords for classes).
- Keep new modules aligned with the existing root-level `mc3000_*.py` naming pattern.
- Optional tooling: `black` for formatting and `mypy` for type checking (both listed under `dev` extras).

## Testing Guidelines
- No test suite is present in this repo; there are no `tests/` directories or test files.
- If you add tests, prefer `pytest` and name files `test_*.py`.
- Example: `pytest -q` from the repo root.

## Commit & Pull Request Guidelines
- Git history is not available in this checkout, so no local commit conventions can be inferred.
- Use concise, imperative commit messages (e.g., "Add backup CLI flag").
- PRs should explain device impact, include screenshots for GUI changes, and link any related issues.

## Configuration Tips (Linux USB)
- For non-root access, add udev rules in `/etc/udev/rules.d/99-mc3000.rules` as described in `README.md`, then reload rules with `sudo udevadm control --reload-rules`.
