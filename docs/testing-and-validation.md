# Testing and Validation

Backend tests cover existing country-risk services, Case Pack structure and references, ZIP traversal rejection, atomic import behavior, prediction semantics, analytical-support registry resolution, before-reveal support validation, formula known answers, basis-point conversion, sign conventions, matrix dimensions, and correlation bounds. The Event Lab smoke flow checks its pedagogical visual stages; it does not assert confidentiality of pre-reveal values because the current API sends the complete case payload to the browser. Public source checkout tests use clearly synthetic temporary case fixtures; private packs are not included in the repository. Frontend validation is completed with `npm run build` and a smoke run through Case Library -> Event Lab -> prediction -> theory/formula -> reveal -> calculation -> Formula Playground. The Indicator Registry is also checked through the public API and UI.

Focused local commands:

```bash
PYTHONPATH=backend backend/.venv/bin/pytest -q backend/app/tests
npm run build
```

The repository contains a separate nested project under `hk-china-demand-monitor`; its tests require that project's own environment and are outside this application's release gate.

Historical facts are not validated by mathematical tests alone. The pack's source registry and manifest are part of the evidence boundary.
