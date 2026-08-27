## What changed

Describe the production problem and the implemented behavior.

## Evidence

- [ ] The change distinguishes cross-model physical evidence, platform-specific behavior, and unverified marketing claims.
- [ ] New or changed public interfaces include tests and documentation.
- [ ] Existing Schema 1.6 behavior remains compatible, or the compatibility impact is explicit.

## Verification

- [ ] `python -m unittest discover -s tests -v`
- [ ] `ruff check .`
- [ ] `mkdocs build --strict`
- [ ] `python scripts/check_local_links.py`
- [ ] The validated example and deterministic release builder still pass.

## Media, privacy, and rights

- [ ] No credential, cookie, private absolute path, cache, rejected candidate, or private project asset is included.
- [ ] Any person shown is fictional or a consenting adult with documented rights.
- [ ] No third-party project prompt or media has been copied into the repository.
