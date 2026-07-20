# Release Checklist

Steps for publishing a PPC Optimizer release.

## Before the release

- [ ] All tests pass: `pytest` (99 tests, includes the slow packaging test)
- [ ] Linter is clean: `ruff check app tests main.py`
- [ ] Formatter applied: `ruff format app tests main.py`
- [ ] No hardcoded paths, debug prints, or TODO comments in code
- [ ] Version bumped in `app/version.py` (pyproject reads it dynamically)
- [ ] `CHANGELOG.md` updated with the new version and date
- [ ] `README.md` reflects the current behavior and options
- [ ] Real-data smoke test: `ppc-optimizer <reports> --dry-run --verbose`
- [ ] Workbook formulas verified (open the generated report in Excel)

## Publishing

- [ ] Commit and push: `git add -A && git commit && git push`
- [ ] Tag: `git tag v<version> && git push --tags`
- [ ] Build distributions: `python -m build` (wheel + sdist in `dist/`)
- [ ] Create a GitHub Release from the tag; paste the changelog section
- [ ] Verify installation from a clean environment: `pip install .`
      then `ppc-optimizer --version`

## After the release

- [ ] Bump `app/version.py` to the next development version if needed
- [ ] Close or move remaining issues to the next milestone
