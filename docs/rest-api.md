---
title: "REST API reference: endpoints, authentication, errors"
description: "Complete REST API reference for the Notebook platform: five endpoints under /v1, JSON-over-HTTPS, bearer-token authentication, cursor pagination, and error codes."
sidebar_position: 4
slug: /rest-api
keywords:
  - notebook rest api
  - clinical notes rest
  - openapi 3.1
  - swagger ui
  - createnote endpoint
  - getnote endpoint
  - listnotes
  - http json api
  - cursor pagination
---

# 4. REST API

*Notebook SDK Guide › Section 4*

> **Quick answer.** The Notebook REST API exposes five operations — CreateNote (POST /v1/notes), GetNote (GET /v1/notes/{id}), ListNotes (GET /v1/notes), AnalyzeNote (POST /v1/notes/{id}/analyze), and GetNoteMetrics (GET /v1/notes/{id}/metrics) — with OAuth2 bearer auth and a Swagger UI at /swagger.

**About this page.** This page is the full REST API reference for the Notebook platform. Every operation is a JSON-over-HTTPS call that any HTTP client can make. Authentication is OAuth2 bearer tokens. A live Swagger UI is available at /swagger on the Notebook gateway.

The REST API is the most broadly compatible entry point to Notebook. Every operation is a plain JSON-over-HTTPS call; any HTTP client works.

## 4.1 Base URL and versioning

All REST endpoints live under:

```
https://api.<your-domain>/v1
```

The `v1` segment is part of the URL. Breaking changes ship under `/v2` and the previous major version is supported for at least 12 months. Non-breaking additions (new fields, new endpoints) are added in place.

All requests and responses use UTF-8 JSON. Timestamps are RFC 3339 UTC (for example, `2026-04-22T15:04:05Z`).

## 4.2 Authentication

Every request must carry a bearer token:

```
Authorization: Bearer <access-token>
```

Tokens are obtained via the OAuth2 client-credentials flow described in [§3.2](./03-getting-started.md#32-get-an-access-token). The token's claims determine the caller's `org_id` and permitted scopes. Full details are in [§8.2](./08-security-and-compliance.md#82-authentication-and-authorization).

Missing or invalid tokens return `401` with `code: UNAUTHENTICATED`. Tokens lacking the required scope return `403` with `code: PERMISSION_DENIED`. Use the Notebook error code — not the HTTP reason phrase — when branching.

## 4.3 Swagger / OpenAPI

An interactive Swagger UI is hosted at:

```
https://api.<your-domain>/swagger
```

The machine-readable OpenAPI 3.1 document is at:

```
https://api.<your-domain>/openapi.json
```

> **Hosting your own.** If you operate a self-hosted Notebook deployment, the OpenAPI document is generated at build time and served by the API gateway. Point your Swagger UI, Postman collection, or codegen tool at `/openapi.json` on your internal hostname. The document reflects exactly the endpoints enabled on that deployment, including any feature flags.

## 4.4 Endpoint reference

The REST API exposes five operations. All paths are relative to the base URL in §4.1.

| Method | Path                             | Operation         | Description                                  |
|--------|----------------------------------|-------------------|----------------------------------------------|
| POST   | `/notes`                         | CreateNote        | Ingest a new clinical note.                  |
| GET    | `/notes/{id}`                    | GetNote           | Fetch a single note and its metrics.         |
| GET    | `/notes`                         | ListNotes         | Paginated list of notes for the caller's org.|
| POST   | `/notes/{id}/analyze`            | AnalyzeNote       | Re-run or deepen analysis on an existing note.|
| GET    | `/notes/{id}/metrics`            | GetNoteMetrics    | Fetch only the metrics payload for a note.   |

Pagination is cursor-based. List responses return a `next_page_token`; pass it back as `?page_token=…` to fetch the next page. Maximum `page_size` is `100` (default `25`).

### 4.4.1 CreateNote — `POST /notes`

Creates a note and kicks off asynchronous analysis. Returns `202 ACCEPTED` with the persisted note and `status: PROCESSING`.

**Headers**

| Header             | Required | Description                                                             |
|--------------------|----------|-------------------------------------------------------------------------|
| `Authorization`    | yes      | `Bearer <access-token>`.                                                |
| `Idempotency-Key`  | yes      | Caller-supplied UUID. Retried requests with the same key within 24h return the original response. |
| `Content-Type`     | yes      | `application/json`.                                                     |

**Request body**

```json
{
  "patient_id": "pt_001",
  "provider_id": "pr_042",
  "encounter_id": "enc_12345",
  "note_type": "PROGRESS",
  "source_system": "epic",
  "body": "Patient reports improved mobility since last visit."
}
```

**Response — 202 ACCEPTED**

```json
{
  "id": "3b7a9c12-5e4d-4b2f-8c1a-9d2e6f3b4a5c",
  "org_id": "org_9f0a",
  "patient_id": "pt_001",
  "provider_id": "pr_042",
  "encounter_id": "enc_12345",
  "note_type": "PROGRESS",
  "source_system": "epic",
  "status": "PROCESSING",
  "created_at": "2026-04-22T15:04:05Z",
  "updated_at": "2026-04-22T15:04:05Z"
}
```

**curl**

```bash
curl -X POST https://api.<your-domain>/v1/notes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d @note.json
```

**Python**

```python
import os, uuid, requests

r = requests.post(
    "https://api.<your-domain>/v1/notes",
    headers={
        "Authorization": f"Bearer {os.environ['NOTEBOOK_TOKEN']}",
        "Idempotency-Key": str(uuid.uuid4()),
    },
    json={
        "patient_id": "pt_001",
        "provider_id": "pr_042",
        "note_type": "PROGRESS",
        "body": "Patient reports improved mobility since last visit.",
    },
    timeout=10,
)
r.raise_for_status()
note = r.json()
```

**Node / TypeScript**

```ts
import { randomUUID } from "node:crypto";

const res = await fetch("https://api.<your-domain>/v1/notes", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${process.env.NOTEBOOK_TOKEN}`,
    "Content-Type": "application/json",
    "Idempotency-Key": randomUUID(),
  },
  body: JSON.stringify({
    patient_id: "pt_001",
    provider_id: "pr_042",
    note_type: "PROGRESS",
    body: "Patient reports improved mobility since last visit.",
  }),
});
if (!res.ok) throw new Error(`CreateNote failed: ${res.status}`);
const note = await res.json();
```

Notable operation-specific errors: `400 VALIDATION_ERROR` (missing required field, `body` > 1 MB), `409 DUPLICATE_IDEMPOTENCY_KEY` (same key used with a different body within 24h), `429 RATE_LIMITED`.

### 4.4.2 GetNote — `GET /notes/{id}`

Returns a single note. When `status == READY`, the response includes an embedded `metrics` object.

**Response — 200 OK**

```json
{
  "id": "3b7a9c12-5e4d-4b2f-8c1a-9d2e6f3b4a5c",
  "patient_id": "pt_001",
  "provider_id": "pr_042",
  "note_type": "PROGRESS",
  "status": "READY",
  "body": "Patient reports improved mobility since last visit.",
  "created_at": "2026-04-22T15:04:05Z",
  "updated_at": "2026-04-22T15:04:07Z",
  "metrics": {
    "word_count": 7,
    "character_count": 52,
    "sentence_count": 1,
    "reading_time_seconds": 3,
    "metrics_version": "1.0.0",
    "computed_at": "2026-04-22T15:04:07Z"
  }
}
```

**Python**

```python
r = requests.get(
    f"https://api.<your-domain>/v1/notes/{note_id}",
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=5,
)
r.raise_for_status()
note = r.json()
```

Request and response shapes are identical in curl and Node/TS — only the HTTP client changes. See §4.4.1 for the pattern.

Notable errors: `404 NOT_FOUND` (note doesn't exist, or belongs to a different org — see §2.11).

### 4.4.3 ListNotes — `GET /notes`

Paginated list. Filter by `patient_id`, `provider_id`, `note_type`, or `status` via query parameters.

**Query parameters**

| Param         | Type    | Description                                              |
|---------------|---------|----------------------------------------------------------|
| `patient_id`  | string  | Exact match.                                             |
| `provider_id` | string  | Exact match.                                             |
| `note_type`   | enum    | `PROGRESS`, `DISCHARGE`, `RADIOLOGY`, `LAB`, `REFERRAL`, `OTHER`. |
| `status`      | enum    | `PROCESSING`, `READY`, `FAILED`.                         |
| `page_size`   | int     | 1–100, default 25.                                       |
| `page_token`  | string  | Opaque cursor from a previous response.                  |

**Response — 200 OK**

```json
{
  "notes": [ { "id": "…", "status": "READY", /* …fields… */ } ],
  "next_page_token": "eyJvZmZzZXQiOjI1fQ=="
}
```

When `next_page_token` is absent or empty, you've reached the end.

**Node / TypeScript**

```ts
const url = new URL("https://api.<your-domain>/v1/notes");
url.searchParams.set("patient_id", "pt_001");
url.searchParams.set("page_size", "50");

const res = await fetch(url, {
  headers: { Authorization: `Bearer ${process.env.NOTEBOOK_TOKEN}` },
});
const { notes, next_page_token } = await res.json();
```

Notable errors: `400 VALIDATION_ERROR` (bad `page_token`, bad enum value, `page_size` > 100).

### 4.4.4 AnalyzeNote — `POST /notes/{id}/analyze`

Re-triggers analysis. Use this to retry after `FAILED`, or to recompute metrics after a `metrics_version` bump. Returns `202 ACCEPTED` and transitions the note back to `PROCESSING`.

**Request body (all fields optional)**

```json
{
  "force": true,
  "analyses": ["metrics"]
}
```

- `force: true` recomputes even if metrics are already present and current.
- `analyses` selects which analyzers to run. v1 accepts only `"metrics"`. `"sentiment"` and `"summary"` are reserved for a future release.

**curl**

```bash
curl -X POST https://api.<your-domain>/v1/notes/$NOTE_ID/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

Notable errors: `404 NOT_FOUND`, `409 CONFLICT` (note already in `PROCESSING`; wait for it to settle or pass `force: true`), `503 SERVICE_UNAVAILABLE` (the downstream Metrics service is unreachable — safe to retry with backoff).

### 4.4.5 GetNoteMetrics — `GET /notes/{id}/metrics`

Cheap read of just the metrics payload, without the note body. Use this when you already know the note exists and only want the counts.

**Response — 200 OK**

```json
{
  "note_id": "3b7a9c12-5e4d-4b2f-8c1a-9d2e6f3b4a5c",
  "word_count": 7,
  "character_count": 52,
  "sentence_count": 1,
  "reading_time_seconds": 3,
  "metrics_version": "1.0.0",
  "computed_at": "2026-04-22T15:04:07Z"
}
```

**Python**

```python
r = requests.get(
    f"https://api.<your-domain>/v1/notes/{note_id}/metrics",
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=5,
)
if r.status_code == 409 and r.json()["error"]["code"] == "METRICS_NOT_READY":
    # Not an error — the note is still PROCESSING. Poll again shortly.
    metrics = None
else:
    r.raise_for_status()
    metrics = r.json()
```

Notable errors: `404 NOT_FOUND`, `409 METRICS_NOT_READY` (note exists but `status != READY`; poll or subscribe).

## 4.5 REST error codes

All errors use the unified error model from [§7.1](./07-error-handling.md#71-unified-error-model). The HTTP status code, the `code` field, and the `message` are the three things you should log.

| HTTP | `code`                       | When it happens                                                  |
|------|------------------------------|------------------------------------------------------------------|
| 400  | `VALIDATION_ERROR`           | Malformed JSON, missing required field, bad enum, body too large.|
| 401  | `UNAUTHENTICATED`            | Missing, expired, or malformed bearer token.                     |
| 403  | `PERMISSION_DENIED`          | Token lacks the required scope (for example, `notes:write`).     |
| 404  | `NOT_FOUND`                  | Note doesn't exist, or belongs to a different org.               |
| 409  | `DUPLICATE_IDEMPOTENCY_KEY`  | Same `Idempotency-Key` with a different request body within 24h. |
| 409  | `CONFLICT`                   | AnalyzeNote called on a note that's already `PROCESSING`.        |
| 409  | `METRICS_NOT_READY`          | GetNoteMetrics called before `status == READY`.                  |
| 413  | `PAYLOAD_TOO_LARGE`          | `body` exceeds 1 MB.                                             |
| 429  | `RATE_LIMITED`               | Per-org rate limit exceeded. Respect the `Retry-After` header.   |
| 500  | `INTERNAL`                   | Unexpected server error. Safe to retry with exponential backoff. |
| 503  | `SERVICE_UNAVAILABLE`        | Downstream Metrics or Analysis service is unreachable. Retry.    |
| 504  | `DEADLINE_EXCEEDED`          | Upstream timed out. Retry with backoff.                          |

Every error response body follows this shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "patient_id is required.",
    "details": [
      { "field": "patient_id", "issue": "missing" }
    ],
    "request_id": "req_01HRZP8Q9X"
  }
}
```

The `request_id` is the single most useful value to include when contacting support.
