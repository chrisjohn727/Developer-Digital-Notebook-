---
title: "Error handling: unified error model and retry guidance"
description: "Notebook's unified error model across REST, gRPC, and GraphQL. Includes the HTTP ↔ gRPC ↔ GraphQL mapping table and explicit retry guidance per error code."
sidebar_position: 7
slug: /error-handling
keywords:
  - notebook errors
  - api error codes
  - grpc status codes
  - graphql error extensions
  - retry strategy
  - rate_limited
  - metrics_not_ready
  - idempotency duplicate
  - exponential backoff
---

# 7. Error handling

*Notebook SDK Guide › Section 7*

> **Quick answer.** Notebook returns the same logical errors across all three protocols. Branch your client on the Notebook error code (e.g., METRICS_NOT_READY), not on the protocol's HTTP status or gRPC status code. Use exponential backoff for INTERNAL, SERVICE_UNAVAILABLE, and DEADLINE_EXCEEDED.

**About this page.** This page defines Notebook's cross-protocol error model. If you write one error-handling layer keyed on the Notebook error code, you can reuse it verbatim whether your integration is over REST, gRPC, or GraphQL.

Errors in Notebook follow one logical model across all three protocols. Only the wire encoding differs. If you write a single error-handling layer keyed on the Notebook error code, you can reuse it verbatim whether you integrate over REST, gRPC, or GraphQL.

## 7.1 Unified error model

Every error carries four pieces of information:

- **Notebook error code** — a stable, uppercase identifier like `METRICS_NOT_READY`. This is what you branch on.
- **Message** — a human-readable description. Safe to log; never show raw to clinicians because messages occasionally reference internal terminology.
- **Details** — optional structured context, such as which field failed validation or how long to wait before retrying.
- **Request ID** — a correlation identifier (`req_01HRZP8Q9X`) attached to every request. Quote it in every support ticket.

How each protocol surfaces these:

| Field        | REST                             | gRPC                                          | GraphQL                                  |
|--------------|----------------------------------|-----------------------------------------------|------------------------------------------|
| Error code   | `error.code` in JSON body        | Trailing metadata `x-notebook-error-code`     | `errors[].extensions.code`               |
| Message      | `error.message`                  | `status.details` / RPC message                | `errors[].message`                       |
| Details      | `error.details[]`                | Trailing metadata `x-notebook-error-details`  | `errors[].extensions.*`                  |
| Request ID   | `error.request_id`               | Trailing metadata `x-notebook-request-id`     | `errors[].extensions.requestId`          |

The Notebook error code is the source of truth. The REST HTTP status, the gRPC status code, and the GraphQL category are derived from it.

## 7.2 HTTP ↔ gRPC ↔ GraphQL mapping table

Use this table when writing a shared error-handling layer.

| Notebook error code         | HTTP | gRPC status          | GraphQL extensions.code     | Retryable? |
|-----------------------------|------|----------------------|-----------------------------|------------|
| `VALIDATION_ERROR`          | 400  | `INVALID_ARGUMENT`   | `VALIDATION_ERROR`          | No         |
| `UNAUTHENTICATED`           | 401  | `UNAUTHENTICATED`    | `UNAUTHENTICATED`           | After refresh |
| `PERMISSION_DENIED`         | 403  | `PERMISSION_DENIED`  | `PERMISSION_DENIED`         | No         |
| `NOT_FOUND`                 | 404  | `NOT_FOUND`          | `NOT_FOUND`                 | No         |
| `CONFLICT`                  | 409  | `FAILED_PRECONDITION`| `CONFLICT`                  | After state change |
| `DUPLICATE_IDEMPOTENCY_KEY` | 409  | `ALREADY_EXISTS`     | `DUPLICATE_IDEMPOTENCY_KEY` | No         |
| `METRICS_NOT_READY`         | 409  | `FAILED_PRECONDITION`| `METRICS_NOT_READY`         | Yes, with backoff |
| `PAYLOAD_TOO_LARGE`         | 413  | `INVALID_ARGUMENT`   | `PAYLOAD_TOO_LARGE`         | No         |
| `RATE_LIMITED`              | 429  | `RESOURCE_EXHAUSTED` | `RATE_LIMITED`              | Yes, honor hint |
| `INTERNAL`                  | 500  | `INTERNAL`           | `INTERNAL`                  | Yes        |
| `SERVICE_UNAVAILABLE`       | 503  | `UNAVAILABLE`        | `SERVICE_UNAVAILABLE`       | Yes        |
| `DEADLINE_EXCEEDED`         | 504  | `DEADLINE_EXCEEDED`  | `DEADLINE_EXCEEDED`         | Yes        |

The full per-error catalog — including operation-specific error codes not shown here — is in [§10.2](./10-appendix.md#102-full-error-catalog).

## 7.3 Retry guidance

Follow these rules; they're identical across protocols.

- **Never retry on `VALIDATION_ERROR`, `PERMISSION_DENIED`, `NOT_FOUND`, `DUPLICATE_IDEMPOTENCY_KEY`, or `PAYLOAD_TOO_LARGE`.** These are deterministic failures; retrying wastes budget and may cause audit-log noise.
- **Retry on `INTERNAL`, `SERVICE_UNAVAILABLE`, `DEADLINE_EXCEEDED`** with exponential backoff starting at 250 ms, doubling, capped at 30 s, with full jitter. Give up after 5 attempts and surface the failure to a human.
- **Retry on `RATE_LIMITED`** only after the hint. REST returns `Retry-After` in seconds; gRPC returns `retry-after-ms` in trailing metadata; GraphQL exposes `extensions.retryAfterMs`. Don't retry sooner.
- **`METRICS_NOT_READY` is a polling signal**, not a failure. Sleep 500 ms–2 s and retry, or prefer the `noteAnalyzed` subscription for real-time delivery.
- **On retry, always reuse the original `Idempotency-Key`.** Generating a fresh key per attempt defeats the server-side deduplication and can create duplicate clinical notes.

Recommended client-side behavior:

1. Wrap every mutating call (`CreateNote`, `AnalyzeNote`) in a retry policy that respects the list above.
2. Log `request_id`, Notebook error code, and the retry attempt number on every failure.
3. Stop retrying after 5 attempts; raise to a human. For clinical ingestion, missing data is better than silently duplicated data.
