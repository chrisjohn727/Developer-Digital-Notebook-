---
title: "Troubleshooting and FAQ for the Notebook SDK"
description: "Answers to common Notebook SDK integration questions: stuck PROCESSING notes, duplicate notes, 404 NOT_FOUND, rate limits, subscription drops, and more."
sidebar_position: 9
slug: /troubleshooting-and-faq
keywords:
  - notebook faq
  - notebook troubleshooting
  - api errors
  - rate_limited retry
  - idempotency key problems
  - metrics not ready
  - grpc unavailable
  - subscription disconnect
---

# 9. Troubleshooting and FAQ

*Notebook SDK Guide › Section 9*

> **Quick answer.** Quick answers to the most common Notebook SDK integration problems, plus a FAQ on architecture and operational questions. Each entry is self-contained so it can be surfaced individually in search.

**About this page.** This page is question-and-answer formatted for direct lookup. Use it when you hit an unexpected error, see a confusing response, or need a quick operational answer about how the Notebook platform works.

## 9.1 Common problems

**"I created a note and the metrics are still null."**  
Check the note's `status`. If it's `PROCESSING`, the analysis pipeline hasn't finished yet — poll `GetNote` or subscribe to `noteAnalyzed`. If it's `FAILED`, read `failure_reason` and call `AnalyzeNote` with `force: true` to retry. If the note has been in `PROCESSING` for more than 60 seconds, contact support with the `request_id`.

**"I'm getting `NOT_FOUND` on a note I know exists."**  
The note belongs to a different organization than your token. Cross-org reads deliberately return `NOT_FOUND` rather than `PERMISSION_DENIED` to prevent organization enumeration (see [§2.11](./02-core-concepts.md#211-multi-tenancy-and-org-scoping)). Confirm your token's `org_id` claim matches the note's owning org.

**"My retries keep creating duplicate notes."**  
You're generating a fresh `Idempotency-Key` on each retry. Reuse the original key for all retries of the same logical request. Generate a new key only when starting a new logical request.

**"My GraphQL subscription disconnects after an hour."**  
Your access token expired. Refresh the token and re-subscribe; Notebook will deliver any emissions you missed if the note is now `READY` or `FAILED`. For long-lived subscribers, refresh the token before it expires and reconnect proactively.

**"`RATE_LIMITED` on every request."**  
You're exceeding the per-org rate limit. Honor the `Retry-After` hint (REST), `retry-after-ms` trailing metadata (gRPC), or `extensions.retryAfterMs` (GraphQL). If you need a higher sustained rate, contact your administrator to raise the limit rather than retrying harder.

**"gRPC calls fail with `UNAVAILABLE` intermittently."**  
The downstream Metrics or Analysis service is in a brief failure window. This is the retry-with-backoff case described in [§7.3](./07-error-handling.md#73-retry-guidance). If it persists for more than a few minutes, check Notebook's status page or contact support.

**"My OAuth token works for REST but not for gRPC."**  
Confirm you're passing the token as `authorization` metadata (lowercase), not `Authorization`. gRPC metadata keys are case-insensitive per spec but some clients normalize aggressively; lowercase is the safest form.

**"The Swagger UI shows endpoints I don't have."**  
Swagger reflects the endpoints the gateway is configured to expose on your deployment. Scopes are enforced at call time, not at documentation time — you'll see the endpoint but calls will return `PERMISSION_DENIED` until an admin grants the right scope.

## 9.2 FAQ

**Why is there no synchronous `CreateNote` that returns metrics in one call?**  
Because metric computation runs in a separate microservice to keep the ingestion path fast and isolated from analysis load spikes. A blocking variant would reintroduce the coupling the compute-first architecture is designed to avoid. Poll or subscribe instead.

**Can I compute my own metrics client-side and push them in?**  
Not in v1. The `metrics_version` field is controlled server-side so that every consumer sees a consistent, auditable derivation. If you need custom metrics, open a feature request with the specific computation.

**Is there a prebuilt client library?**  
Not in v1. Use generated gRPC stubs, a GraphQL code generator, or any HTTP client. A typed client library is on the roadmap.

**Does Notebook store the raw note body after analysis?**  
Yes. The compute-first model derives metrics from the body *once*, but the body itself is retained (in encrypted SQLite) so that future analyzers — sentiment, summarization, entity extraction — can re-derive new signals without re-ingestion. Retention can be shortened per organization; see [§8.5](./08-security-and-compliance.md#85-data-retention-and-deletion).

**Can one note belong to multiple patients?**  
No. A note has exactly one `patient_id`. If you have a document that references multiple patients (for example, a care-team huddle note), either split it into per-patient notes or store it in a separate system.

**What happens if `body` contains non-English text?**  
`character_count` and `word_count` use UTF-8 codepoints and whitespace tokenization respectively, which works for most languages. `sentence_count` and `reading_time_seconds` are tuned for English and may be approximate for other languages. Language-aware analysis is on the roadmap.

**How do I test against Notebook without real PHI?**  
Use the sandbox deployment, which accepts API-key authentication and synthetic-only data. Never send real PHI to a sandbox; that's a compliance incident. Request sandbox credentials from your administrator.

**Who do I contact when something is wrong?**  
Your organization's Notebook administrator is the first line. Include the `request_id` from the error, the Notebook error code, the operation name, and the approximate timestamp. Most issues are resolvable from those four values alone.
