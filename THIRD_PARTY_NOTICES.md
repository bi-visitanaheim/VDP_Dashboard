# Third-Party Notices

Dana Point PULSE is proprietary software, copyright (c) 2026 Wilton John Picou,
GloCon Solutions LLC, licensed exclusively to Visit Dana Point. The proprietary
license in the `LICENSE` file applies only to the original work authored by the
Owner.

The Software incorporates the open-source components listed below. Each is the
property of its respective authors and is governed by its own license. All of
the licenses below are permissive (Apache-2.0, BSD, or MIT) and permit use
within a proprietary, commercially distributed application, provided the
copyright and license text of each component is retained. This file satisfies
that attribution requirement.

> Note: License identifiers reflect each project's stated license at the time of
> writing. Before redistribution, confirm the current license of each package
> version pinned in `requirements.txt`.

## Runtime dependencies

| Package | Typical License | Project |
|---|---|---|
| streamlit | Apache-2.0 | https://github.com/streamlit/streamlit |
| pandas | BSD-3-Clause | https://github.com/pandas-dev/pandas |
| numpy | BSD-3-Clause | https://github.com/numpy/numpy |
| plotly | MIT | https://github.com/plotly/plotly.py |
| anthropic (SDK) | MIT | https://github.com/anthropics/anthropic-sdk-python |
| openai (SDK) | Apache-2.0 | https://github.com/openai/openai-python |
| google-generativeai | Apache-2.0 | https://github.com/google-gemini/generative-ai-python |
| python-dotenv | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| openpyxl | MIT | https://foss.heptapod.net/openpyxl/openpyxl |
| requests | Apache-2.0 | https://github.com/psf/requests |
| playwright | Apache-2.0 | https://github.com/microsoft/playwright-python |
| pdfplumber | MIT | https://github.com/jsvine/pdfplumber |
| beautifulsoup4 | MIT | https://www.crummy.com/software/BeautifulSoup/ |
| pytrends | Apache-2.0 | https://github.com/GeneralMills/pytrends |
| streamlit-authenticator | Apache-2.0 | https://github.com/mkhorasani/Streamlit-Authenticator |

## Development / test dependencies

| Package | Typical License | Project |
|---|---|---|
| pytest | MIT | https://github.com/pytest-dev/pytest |
| pytest-cov | MIT | https://github.com/pytest-dev/pytest-cov |

## Data sources

The Software ingests data from third-party providers. This data is **not** owned
by the Owner and is **not** covered by this Software's license. Use of each data
source is governed by that provider's terms. See `docs/LEGAL_COMPLIANCE.md` for
the full data-source licensing analysis.
