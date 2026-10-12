# EchoLens scientific governance — review stage

**Status:** Proposed; independent scientific ratification pending. This documentation does not grant confirmatory status to any experiment.

- [Unified Scientific Standards v1.0 — proposed](https://docs.google.com/document/d/1cvXK9HbHZwHh49dVLQJ0y___aLkcWX2x4YvmgGc5an0/edit)
- [Scientific Protocol Alignment Audit](https://docs.google.com/document/d/1VMDCJkA7Cbjs8xL-5GELac1lWtRa6Mbqxp69Wsa8TuM/edit)
- [Formal Review and Adoption Record](https://docs.google.com/document/d/1_HhhjGiaw9I1c3tO_Fu54UOfzkIGvw7eWoqFi0F8IUE/edit)
- [Central Research Index](https://docs.google.com/document/d/1JoFrcVJeFAqP7F2ISA5XZo-H8lZQkCVEHzCu1e7wO5I/edit)
- [Governance adoption checklist — Issue #31](https://github.com/gittenssexton/echolens-api/issues/31)

## Governance gate

Research data remain unmodified. Before standards ratification: assign an independent scientific reviewer, reconcile the PR2/PR3 Gaia sample identities and source checksums, resolve TV01-B's null tail and holdout definition, audit SP01 methodological limitations, and resolve source integrity blockers. Record the reviewer, disposition, approved version and effective UTC timestamp.

## Future repository organization

Retain `app/`, `scripts/`, `tests/`, `docs/`, `data/`, and `reports/` as currently used. New governance metadata belongs under `docs/governance/`. New experiments may use `experiments/<program>/<run>/` for small versioned protocol, manifest and code artifacts; keep bulk FITS and scientific source archives in durable external storage referenced by ID and SHA-256. No files should be moved until import paths and provenance links have been checked.

This entry is documentation only. It neither deploys code nor performs scientific approval.
