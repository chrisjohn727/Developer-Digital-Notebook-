---
title: "Core concepts: architecture, data model, async processing"
description: "The Notebook platform's architecture, Note and Metrics entities, compute-first model, async processing, idempotency, multi-tenancy, and versioning."
sidebar_position: 2
slug: /core-concepts
keywords:
  - notebook architecture
  - clinical notes data model
  - compute-first
  - async api
  - idempotency key
  - multi-tenancy
  - healthcare sdk architecture
  - oauth2 scopes
---

# 2. Core concepts

*Notebook SDK Guide › Section 2*

> **Quick answer.** Notebook computes expensive signals once at write time and serves cheap lookups at read time. A Note is the primary entity; Metrics are computed asynchronously via a gRPC microservice and attached to the Note. CreateNote returns immediately with status PROCESSING; clients poll or subscribe for completion.

**About this page.** This page explains the mental model behind the Notebook platform — data entities, lifecycle, architecture, and design trade-offs. Read it before using the REST, gRPC, or GraphQL reference pages, which assume familiarity with these concepts.

This section gives you the mental model you need before you touch any of the three APIs. Read it once; the REST, gRPC, and GraphQL reference sections assume you know everything here.

## 2.1 Why Notebook exists

Clinicians read long, dense reports — discharge summaries, radiology reads, progress notes, referral letters — and important nuances get missed. The Notebook platform ingests those reports as structured notes, computes text-derived signals (word counts today; sentiment, summaries, and entity extraction on the roadmap), and stores the results so that downstream tools — dashboards, clinical-decision-support systems, triage queues — can query them in milliseconds instead of re-running expensive analysis on every view.

## 2.2 The compute-first model

Notebook follows a **compute-once, read-many** design. When a note is created, expensive work (text analysis, and later LLM inference) runs once through dedicated gRPC microservices, and the results are persisted to SQLite. Every subsequent read — whether over REST, gRPC, or GraphQL — is a cheap lookup.

> **Why this matters.** Naive designs recompute text metrics on every request. That's fine at demo scale and catastrophic at hospital scale, where a single dashboard can issue thousands of reads per second. Compute-first trades a small write-time cost for bounded, predictable read latency, which is what production clinical workflows need.

## 2.3 Architecture at a glance

```
                    ┌───────────────────────────────┐
                    │        Notebook API           │
  Client  ────────▶ │  (REST  ·  gRPC  ·  GraphQL)  │ ───────▶  SQLite
                    │         gateway               │           (notes +
                    └──────────────┬────────────────┘            metrics)
                                   │ gRPC
                      ┌────────────┴────────────┐
                      ▼                         ▼
              ┌──────────────┐          ┌──────────────┐
              │   Metrics    │          │   Analysis   │
              │   service    │          │   service    │
              │  (word/char  │          │ (sentiment,  │
              │   counts)    │          │  LLM — v2)   │
              └──────────────┘          └──────────────┘
```

The API gateway is the only component you call directly. Internal service-to-service calls use gRPC with mTLS and never cross the public network.

## 2.4 The Note entity

A Note is the primary object you work with. Every note belongs to an organization, a patient, and a provider.

| Field           | Type      | Required | Description                                                                 |
|-----------------|-----------|----------|-----------------------------------------------------------------------------|
| `id`            | UUID      | server   | Server-assigned identifier.                                                 |
| `org_id`        | UUID      | server   | Derived from the caller's auth token; you never set this.                   |
| `patient_id`    | string    | yes      | Opaque patient identifier from your EHR.                                    |
| `provider_id`   | string    | yes      | Opaque clinician identifier.                                                |
| `encounter_id`  | string    | no       | Links the note to a visit or admission.                                     |
| `note_type`     | enum      | yes      | One of `PROGRESS`, `DISCHARGE`, `RADIOLOGY`, `LAB`, `REFERRAL`, `OTHER`.    |
| `source_system` | string    | no       | Originating EHR or system tag (for example, `epic`, `cerner`).              |
| `body`          | string    | yes      | The free-text clinical narrative. Max 1 MB.                                 |
| `status`        | enum      | server   | `DRAFT`, `PROCESSING`, `READY`, or `FAILED`. See 2.6.                       |
| `created_at`    | timestamp | server   | RFC 3339 UTC.                                                               |
| `updated_at`    | timestamp | server   | RFC 3339 UTC.                                                               |

## 2.5 The Metrics entity

Metrics are computed asynchronously and attached to a note by `note_id`. You read them through `GetNoteMetrics` or embed them in a `GetNote`/`note` response.

| Field                   | Type    | Description                                                                 |
|-------------------------|---------|-----------------------------------------------------------------------------|
| `note_id`               | UUID    | Back-reference to the note.                                                 |
| `word_count`            | int     | Whitespace-tokenized word count.                                            |
| `character_count`       | int     | UTF-8 codepoint count, including whitespace.                                |
| `sentence_count`        | int     | Approximate, based on terminal punctuation and common medical abbreviations.|
| `reading_time_seconds`  | int     | Estimate at 200 words per minute.                                           |
| `metrics_version`       | string  | Semver of the metrics schema, for example `1.0.0`. See §2.10.               |
| `computed_at`           | timestamp | When the metrics were last written.                                       |

Roadmap fields (populated when the Analysis service ships): `sentiment_score`, `summary`, `entities[]`.

## 2.6 Note status lifecycle

```
  CreateNote                      metrics written                 compute error
  ──────────▶  DRAFT  ──────▶  PROCESSING  ──────▶  READY         or timeout
                                                  │
                                                  └─────▶  FAILED  ──▶ (retry via AnalyzeNote)
```

- `DRAFT` is transient; you almost never see it in responses.
- `PROCESSING` means the note is persisted but metrics aren't ready yet.
- `READY` means metrics are attached and the note is fully queryable.
- `FAILED` means the analysis pipeline gave up. Inspect `failure_reason` and call `AnalyzeNote` to retry.

## 2.7 Choosing a protocol

All three APIs expose the same five operations. Pick based on your integration context.

| Protocol | Choose it when…                                                                 |
|----------|---------------------------------------------------------------------------------|
| REST     | You're writing quick integrations, curl-ing from shell, or your stack has strong HTTP tooling but weak Protobuf support. |
| gRPC     | You need low-latency, high-throughput, strongly typed service-to-service calls — typical for backend workers and EHR-side ingestion pipelines. |
| GraphQL  | You're building UIs or dashboards that want to fetch only the fields they render and subscribe to `noteAnalyzed` for live updates. |

You can mix protocols within a single integration. A common pattern: ingest via gRPC, read via GraphQL.

## 2.8 Asynchronous processing

`CreateNote` returns immediately with `status: PROCESSING`. Metrics computation runs out-of-band. Your client has two ways to know when they're ready:

1. **Poll** `GetNote` or `GetNoteMetrics` until `status == READY` (simple, fine for batch workflows).
2. **Subscribe** to the GraphQL `noteAnalyzed(noteId)` subscription (recommended for UIs — zero polling, push-delivered).

Treat `PROCESSING` responses as a normal success case, not an error. If you need synchronous metrics — for example, a validation step that must see counts before returning to the user — document that constraint and poll with a short timeout; there is no blocking variant of `CreateNote` in v1.

## 2.9 Idempotency

`CreateNote` accepts a caller-supplied `Idempotency-Key` (REST header, gRPC metadata, GraphQL argument). If you retry a request with the same key within 24 hours, Notebook returns the original response instead of creating a duplicate note. This matters in healthcare, where retried ingestion jobs must not produce duplicate clinical records.

Use a fresh UUID per logical create; reuse it only on retry.

## 2.10 Versioning

- **REST** is versioned in the URL: `/v1/…`. Breaking changes ship under `/v2/…` and the previous version is supported for at least 12 months.
- **gRPC** is versioned in the Protobuf package: `notebook.v1`. New services go in new packages; fields are added, never repurposed.
- **GraphQL** evolves additively. Fields are marked `@deprecated(reason: "…")` for at least 6 months before removal.
- **Metrics schema** carries its own `metrics_version` so clients can detect when a new analysis field appears.

## 2.11 Multi-tenancy and org scoping

Every request runs in the context of exactly one organization, derived from the caller's OAuth2 token (see §8.2). You never pass `org_id` yourself. Cross-org access — reading or listing notes that belong to a different organization — returns `404 NOT_FOUND` (REST), `NOT_FOUND` (gRPC), or an equivalent GraphQL error. We deliberately return "not found" rather than "forbidden" so that org membership can't be probed.

## 2.12 What "SDK" means here

This document is an SDK *guide*, not a client library. There is no `pip install notebook-sdk` in v1. The code samples in sections 4 through 6 use standard HTTP, gRPC, and GraphQL clients for each language so you can integrate without adopting a bespoke dependency. A typed client library is on the roadmap; until then, generated gRPC stubs and GraphQL codegen are the recommended path for strongly typed access.

Pagination (cursor-based, max 100 per page), PHI handling, and rate limits are touched on throughout this section and detailed in §4.4, §8.1, and §7.3 respectively.
