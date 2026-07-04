# Release Checklist

Use this checklist before any production or UAT release.

## Automated Gates

- [ ] Backend tests pass: `PYTHONPATH=backend backend/.venv/bin/pytest backend/app/tests -q`
- [ ] Frontend build passes: `npm run build`
- [ ] Registry integrity passes: `python3 scripts/registry_integrity_check.py`
- [ ] SQLite migration check passes.
- [ ] Security check passes: `python3 scripts/security_check.py`
- [ ] Disaster recovery check passes: `python3 scripts/disaster_recovery_check.py`
- [ ] Production readiness passes: `python3 scripts/production_readiness_check.py`
- [ ] OpenAPI contract exported: `python3 scripts/export_openapi.py`
- [ ] Release evidence pack generated: `python3 scripts/generate_release_evidence.py`

## Manual Gates

- [ ] Manual QA checklist completed.
- [ ] Production environment variables reviewed.
- [ ] OIDC/JWKS or gateway identity integration configured.
- [ ] SIEM or central audit sink configured.
- [ ] Managed database or approved durable registry target configured.
- [ ] Model-risk approval records completed for any non-learning use.
- [ ] Rollback path and backup manifest reviewed.
- [ ] Release owner, business owner, and operations owner signed off.

