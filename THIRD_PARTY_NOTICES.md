# Third-party notices

EcoLogic application source is covered by the repository's private-preview
rights notice. The items below remain under their own licenses; nothing in the
root notice relicenses them or implies endorsement.

## Bundled font software

The repository redistributes three Plus Jakarta Sans 2.071 TTF files (Regular,
Bold, and ExtraBold).

- Copyright: 2020 The Plus Jakarta Sans Project Authors
- License: SIL Open Font License 1.1
- License text: [static/fonts/OFL.txt](static/fonts/OFL.txt)
- Upstream: <https://github.com/tokotype/PlusJakartaSans>

## Direct runtime dependencies

| Package | Validated version | License | Upstream |
|---|---:|---|---|
| Flask | 3.1.3 | BSD-3-Clause | <https://github.com/pallets/flask> |
| Gunicorn | 23.0.0 | MIT | <https://github.com/benoitc/gunicorn> |
| OpenAI Python | 2.53.0 | Apache-2.0 | <https://github.com/openai/openai-python> |
| python-dotenv | 1.2.2 | BSD-3-Clause | <https://github.com/theskumar/python-dotenv> |

## Runtime transitive dependency inventory

The exact Python 3.12 environment recorded in `requirements.lock` also includes:

| Package | Version | Declared license |
|---|---:|---|
| annotated-types | 0.8.0 | MIT |
| anyio | 4.14.2 | MIT |
| blinker | 1.9.0 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| click | 8.4.2 | BSD-3-Clause |
| colorama | 0.4.6 | BSD |
| distro | 1.9.0 | Apache-2.0 |
| h11 | 0.16.0 | MIT |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpx | 0.28.1 | BSD-3-Clause |
| idna | 3.18 | BSD-3-Clause |
| itsdangerous | 2.2.0 | BSD |
| Jinja2 | 3.1.6 | BSD-3-Clause |
| jiter | 0.16.0 | MIT |
| MarkupSafe | 3.0.3 | BSD-3-Clause |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pydantic | 2.13.4 | MIT |
| pydantic-core | 2.46.4 | MIT |
| sniffio | 1.3.1 | MIT OR Apache-2.0 |
| tqdm | 4.70.0 | MPL-2.0 AND MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.2 | MIT |
| Werkzeug | 3.1.8 | BSD-3-Clause |

Development-only tools are pinned in `requirements-dev.txt` and include
Bandit (Apache-2.0), mypy (MIT), pip-audit (Apache-2.0), pytest (MIT), and
Ruff (MIT). Their transitive packages are fetched at development-install time
and remain under their upstream licenses.

This inventory was reviewed on 2026-08-08. `requirements.lock` is an exact
version lock for the validated environment, not a hash-verified artifact lock.
Re-audit licenses and vulnerabilities whenever dependencies change.
