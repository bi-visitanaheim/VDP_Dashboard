# Legal & Compliance Memo — Dana Point PULSE

**Prepared for:** Wilton John Picou, GloCon Solutions LLC
**Subject:** Keeping the Dana Point PULSE platform legally sound, with Visit
Dana Point as the sole authorized user
**Last reviewed:** 2026-05-28

> **Disclaimer.** This memo is an engineering and compliance reference, not legal
> advice. It documents how the project is structured to protect ownership and
> stay compliant. For binding protection and enforceability, have a licensed
> attorney review the LICENSE and any agreement with Visit Dana Point, and
> register the copyright with the U.S. Copyright Office (see Section 8).

---

## 1. Ownership & copyright

- **Author/owner:** Wilton John Picou, GloCon Solutions LLC, is the sole author
  and copyright holder of all original code, schemas, pipeline logic, dashboard
  design, and documentation in this repository.
- **How it is asserted in the codebase:**
  - `LICENSE` — full proprietary license agreement (perpetual exclusive grant to
    Visit Dana Point).
  - `COPYRIGHT` — standalone ownership/attribution notice.
  - A per-file copyright header embedded at the top of **every** first-party
    source file (`scripts/`, `dashboard/`, `tests/`, root scripts) and stylesheet.
  - A visible `(c)` notice in the dashboard UI (login screen + fixed footer +
    Board Report footer).
- **Copyright is automatic** on creation/fixation in a tangible medium (here, the
  Git history is strong evidence of authorship and date). Registration is **not**
  required for ownership, but it **is** required to file an infringement suit and
  to be eligible for statutory damages and attorney's fees (see Section 8).

## 2. License model — Visit Dana Point as sole user

- Visit Dana Point holds a **perpetual, exclusive, non-transferable,
  non-sublicensable** license to *use* the Software (LICENSE Section 2).
- **Ownership is not transferred.** The grant is a right to use, not an
  assignment of copyright. This is the key protection: VDP can rely on continued
  use, but cannot copy, resell, modify for redistribution, or hand the code to a
  competitor (LICENSE Section 3).
- **"Sole authorized user"** is enforced both contractually (LICENSE) and
  technically — the dashboard ships with `streamlit-authenticator` login gating
  and an admin-only mode (`?admin=true`).
- **Action item:** the LICENSE is a notice. Pair it with a **signed** services or
  license agreement between GloCon Solutions LLC and Visit Dana Point that
  references these terms. A signature is what makes the obligations mutually
  binding on VDP.

## 3. Open-source dependencies

All runtime dependencies (`requirements.txt`) are under **permissive** licenses
(Apache-2.0, BSD-3-Clause, MIT). These permit use inside a proprietary,
commercially distributed application. The only obligation is to **retain each
component's copyright and license text** — satisfied by `THIRD_PARTY_NOTICES.md`.

- No copyleft (GPL/AGPL/LGPL) dependencies are present, so there is **no
  obligation to open-source** this application. **Keep it that way:** before
  adding any new dependency, confirm it is not GPL/AGPL.
- **Action item:** re-verify each package's license at the version pinned in
  `requirements.txt` before any redistribution.

## 4. Data-source licensing (the highest-risk area)

The platform's value comes from third-party data. The Owner does **not** own this
data; each source has its own terms. Because VDP is the **sole user**, the
deployment aligns well with single-licensee data terms, but each source must have
a valid underlying subscription/agreement held by VDP or GloCon.

| Source | Nature | Key obligation |
|---|---|---|
| **STR / CoStar** | Proprietary, paid subscription | **Strictest.** Redistribution and public display are restricted. Data may only be shown to the licensed subscriber (VDP). Do **not** expose raw STR records publicly; aggregated KPIs for the licensee are the intended use. Confirm VDP/GloCon holds a current STR/CoStar license that permits dashboard display. |
| **Datafy** | Proprietary, paid | Use per Datafy's subscriber agreement; single-destination license. Don't redistribute raw records. |
| **Zartico** | Proprietary (historical snapshot) | Historical reference only. Confirm the snapshot was obtained under a valid VDP engagement. |
| **FRED (St. Louis Fed)** | Public, API key | Free for use; attribute the source. Not for implying Fed endorsement. |
| **U.S. Census / ACS** | Public domain | Free to use; attribution courtesy. |
| **BLS** | Public domain | Free to use; cite BLS. |
| **NOAA (tides/marine/weather)** | Public domain (US Gov) | Free; no endorsement implied. |
| **EIA (gas prices)** | Public domain (US Gov) | Free; attribute EIA. |
| **TSA checkpoint counts** | Public (US Gov) | Free; attribute TSA. |
| **Visit California** | Provided forecasts/reports | Use per VCA's distribution terms; typically partner-shareable. |
| **Later.com** | VDP's own social exports | VDP owns its own account data; fine to use for VDP. |
| **Google Trends (pytrends)** | Google ToS | `pytrends` is an *unofficial* scraper. Respect Google's ToS and rate limits; treat as illustrative, not contractual data. |
| **Ticketmaster (events)** | API ToS | Use within Ticketmaster Developer terms; attribute as required. |
| **Wikipedia pageviews** | CC BY-SA / public API | Attribute Wikipedia; share-alike applies only to the text, not your code. |
| **AirNow (AQI)** | US Gov / EPA | Free; attribute AirNow; no endorsement implied. |

**Bottom line on data:** the biggest legal exposure is **STR/CoStar and Datafy**.
The "sole user = Visit Dana Point" model is exactly what those vendors expect, so
keep the dashboard access-gated to VDP and never publish raw proprietary records.

## 5. AI / API terms

- **Keys are server-side only** via environment variables (`ANTHROPIC_API_KEY`,
  `OPENAI_API_KEY`, `GOOGLE_AI_API_KEY`, `PERPLEXITY_API_KEY`); never exposed in
  the UI. Maintain this — keys in client code would be both a security and a
  terms-of-service violation.
- Use each provider (Anthropic, OpenAI, Google, Perplexity) under its commercial
  API terms. For business use, confirm each account is on terms that **do not
  train on your inputs/outputs** (the default for paid API tiers of these
  vendors) so VDP's data and your prompts stay private.
- The system prompt embeds the DB schema, not raw proprietary third-party
  records, which limits data leaving the environment.

## 6. Privacy / PII

- The project's stated design rule is **no PII** in `data/analytics.sqlite`
  (market/aggregate data only). This sharply reduces CCPA/CPRA and GDPR exposure.
- **Keep it that way:** do not load named individuals, visitor-level PII, or
  contact lists into the database. Social exports should remain
  account/aggregate-level.
- If a login system stores user credentials, treat those credentials as personal
  data: hash/secure them (handled by `streamlit-authenticator`) and don't commit
  `secrets.toml` (already gitignored).

## 7. Trademark & branding

- "Visit Dana Point" is the client's brand/mark — used here under the client
  relationship, to identify the licensee. Do not use it to market unrelated
  products.
- "Dana Point PULSE" and "GloCon Solutions" are GloCon's product/house marks.
  Consider a state or federal trademark filing if you want to protect the PULSE
  name. Copyright (this memo's focus) protects the *code*; trademark protects the
  *name*.

## 8. Recommended action items (to make it truly binding)

1. **Register the copyright.** File the source code with the U.S. Copyright
   Office (eCO, Form TX). Cost is modest; it unlocks statutory damages and
   attorney's fees and is required before suing. Register within 3 months of
   first publication for maximum remedies.
2. **Sign a written agreement** between GloCon Solutions LLC and Visit Dana Point
   that incorporates the LICENSE terms (scope, exclusivity, fees, term,
   termination). The embedded LICENSE is the notice; the signature makes it
   mutually enforceable.
3. **Confirm data subscriptions** (STR/CoStar, Datafy, Zartico) are current and
   permit dashboard display to VDP.
4. **Verify AI provider terms** are set to no-training / business tier.
5. **Attorney review** of LICENSE + the VDP agreement before relying on them in a
   dispute.
6. **Keep dependencies permissive** — reject any GPL/AGPL package.
7. **Keep PII out** of the database.

---

*Maintained by GloCon Solutions LLC. Update this memo whenever a new data source,
dependency, or AI provider is added (per the Standard Process in CLAUDE.md).*
