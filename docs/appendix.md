---
title: "Appendix: glossary, full error catalog, changelog"
description: "Reference material for the Notebook SDK: domain glossary, exhaustive cross-protocol error catalog with retry guidance, changelog, and links to relevant standards."
sidebar_position: 10
slug: /appendix
keywords:
  - notebook glossary
  - error catalog
  - api changelog
  - openapi spec
  - grpc status codes reference
  - graphql spec
  - hipaa security rule
  - rfc 3339
---

# 10. Appendix

*Notebook SDK Guide › Section 10*

> **Quick answer.** Reference material: a glossary of Notebook domain terms, the complete cross-protocol error catalog (HTTP ↔ gRPC ↔ GraphQL) with retry guidance, the release changelog, and links to relevant external standards.

**About this page.** This page is lookup material for the Notebook SDK. Use it when you need the authoritative definition of a term, the exhaustive error-code catalog, or pointers to external standards.

## 10.1 Glossary

- **Analysis service** — Internal gRPC microservice that performs heavier, optional processing (sentiment, summarization, entity extraction). On the roadmap; placeholder in v1.
- **BAA (Business Associate Agreement)** — A HIPAA contract between a covered entity and a vendor that processes PHI on their behalf. Required before real PHI is transmitted to Notebook.
- **Body** — The free-text content of a clinical note. Considered PHI.
- **Compute-first** — Notebook's design principle of computing expensive signals once at write time and serving cheap lookups at read time.
- **Encounter** — A single clinical visit, admission, or interaction. Modeled via `encounter_id` on the Note.
- **Idempotency key** — A caller-supplied UUID that lets Notebook deduplicate retried `CreateNote` calls within a 24-hour window.
- **Metrics** — Derived measurements of a note: word count, character count, sentence count, reading-time estimate, and (roadmap) sentiment, summary, and entities.
- **Metrics service** — Internal gRPC microservice that computes the core text metrics.
- **Notebook API (gateway)** — The single public-facing service that exposes REST, gRPC, and GraphQL and owns the SQLite data store.
- **Note** — The primary entity: a single clinical report tied to one patient, one provider, and optionally one encounter.
- **Org / organization** — The tenancy boundary. Every note and every token is scoped to exactly one organization.
- **PHI (Protected Health Information)** — HIPAA-defined data category. In Notebook: the note body, failure reasons, and any join of identifier fields that can identify an individual.
- **Request ID** — A per-request correlation identifier (`req_…`) surfaced on every error and every audit-log entry.
- **Scopes** — OAuth2 permission claims carried in the access token (`notes:read`, `notes:write`, `notes:analyze`, `notes:admin`).
- **Status** — A note's lifecycle state: `DRAFT` (transient), `PROCESSING`, `READY`, or `FAILED`.
- **Tombstone delete** — Deletion mode in which note content is purged but an anonymized audit record is retained.

## 10.2 Full error catalog

The table below is the exhaustive list of Notebook error codes across all three protocols. Use this as the source of truth for client-side error handling.

| Notebook error code         | HTTP | gRPC                  | GraphQL extensions.code     | Meaning                                                                 | Retry strategy               |
|-----------------------------|------|-----------------------|-----------------------------|-------------------------------------------------------------------------|------------------------------|
| `VALIDATION_ERROR`          | 400  | `INVALID_ARGUMENT`    | `VALIDATION_ERROR`          | Bad input: missing field, wrong enum, malformed JSON.                   | No.                          |
| `UNAUTHENTICATED`           | 401  | `UNAUTHENTICATED`     | `UNAUTHENTICATED`           | Missing, expired, or malformed bearer token.                            | Refresh token, then retry.   |
| `PERMISSION_DENIED`         | 403  | `PERMISSION_DENIED`   | `PERMISSION_DENIED`         | Token valid but lacks the required scope.                               | No; request scope from admin.|
| `NOT_FOUND`                 | 404  | `NOT_FOUND`           | `NOT_FOUND`                 | Note does not exist, or belongs to a different org.                     | No.                          |
| `CONFLICT`                  | 409  | `FAILED_PRECONDITION` | `CONFLICT`                  | Note is not in a valid state for the operation (e.g., already `PROCESSING`). | After state change; or `force: true`. |
| `DUPLICATE_IDEMPOTENCY_KEY` | 409  | `ALREADY_EXISTS`      | `DUPLICATE_IDEMPOTENCY_KEY` | Same idempotency key reused with a different body within 24 hours.      | No; generate a new key only for a new logical request. |
| `METRICS_NOT_READY`         | 409  | `FAILED_PRECONDITION` | `METRICS_NOT_READY`         | Metrics requested before `status == READY`.                             | Yes, poll 500 ms–2 s or subscribe. |
| `PAYLOAD_TOO_LARGE`         | 413  | `INVALID_ARGUMENT`    | `PAYLOAD_TOO_LARGE`         | `body` exceeds 1 MB.                                                    | No; split or truncate.       |
| `RATE_LIMITED`              | 429  | `RESOURCE_EXHAUSTED`  | `RATE_LIMITED`              | Per-org rate limit exceeded.                                            | Yes, honor retry-after hint. |
| `INTERNAL`                  | 500  | `INTERNAL`            | `INTERNAL`                  | Unexpected server error.                                                | Yes, exponential backoff.    |
| `SERVICE_UNAVAILABLE`       | 503  | `UNAVAILABLE`         | `SERVICE_UNAVAILABLE`       | Downstream Metrics or Analysis service unreachable.                     | Yes, exponential backoff.    |
| `DEADLINE_EXCEEDED`         | 504  | `DEADLINE_EXCEEDED`   | `DEADLINE_EXCEEDED`         | Upstream timed out before responding.                                   | Yes, with larger deadline.   |

## 10.3 Changelog

| Version | Date        | Changes                                                        |
|---------|-------------|----------------------------------------------------------------|
| 1.0     | _TBD_       | Initial release. REST, gRPC, and GraphQL v1 with five operations: `CreateNote`, `GetNote`, `ListNotes`, `AnalyzeNote`, `GetNoteMetrics`. GraphQL subscription `noteAnalyzed`. Metrics: word count, character count, sentence count, reading-time estimate. |

## 10.4 Further reading

- OpenAPI 3.1 specification — `https://spec.openapis.org/oas/v3.1.0`
- gRPC status codes — `https://grpc.github.io/grpc/core/md_doc_statuscodes.html`
- GraphQL spec — `https://spec.graphql.org/`
- HIPAA Security Rule — `https://www.hhs.gov/hipaa/for-professionals/security/`
- RFC 3339 (Date and Time on the Internet) — `https://datatracker.ietf.org/doc/html/rfc3339`
