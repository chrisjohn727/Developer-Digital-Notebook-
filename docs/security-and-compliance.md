---
title: "Security and compliance: HIPAA, PHI, OAuth2, mTLS, audit"
description: "HIPAA compliance, PHI handling, OAuth2 scopes, TLS/mTLS transport security, audit logging, and data retention for the Notebook healthcare platform."
sidebar_position: 8
slug: /security-and-compliance
keywords:
  - notebook hipaa
  - phi handling
  - oauth2 scopes
  - mtls grpc
  - audit log
  - data retention healthcare
  - baa business associate
  - tls 1.3
  - healthcare compliance sdk
---

# 8. Security and compliance

*Notebook SDK Guide › Section 8*

> **Quick answer.** Notebook is designed for PHI. Use OAuth2 client credentials (scopes: notes:read, notes:write, notes:analyze, notes:admin). Add mTLS for server-to-server gRPC. A BAA is required before sending real PHI. Audit logs are retained seven years.

**About this page.** This page documents the security and HIPAA-compliance contract between Notebook and your integration. Read it before you deploy against real patient data. Nothing here is legal advice — confirm your specific obligations with your compliance officer.

This section is mandatory reading before you deploy Notebook in a setting that handles real patient data. The guidance here is the contract between Notebook and your integration; ignoring it can turn a working integration into a HIPAA violation.

Nothing in this section is legal advice. Work with your organization's compliance and privacy officers to confirm your specific obligations.

## 8.1 HIPAA and PHI handling

Notebook is designed to process Protected Health Information (PHI). When operated in a HIPAA-covered deployment, the following is in force.

- **What is PHI here.** The `body` field, the `failure_reason` field, and anything that ties a record to an identifiable individual (for example, `patient_id` combined with `encounter_id` and timestamps) are treated as PHI. Metric counts on their own are not PHI; metric counts *joined to* a note identifier are.
- **Business Associate Agreement (BAA).** Before you send real PHI, your organization must have a BAA in place with the Notebook operator. Sandbox deployments accept synthetic data only; real PHI sent to a sandbox is a compliance incident.
- **Minimum necessary.** Request only the fields you need. The GraphQL API makes this easy — drop `body` from your selection set for list views and detail pages that don't display the note text.
- **Never put PHI in logs or URLs.** Notebook deliberately places `patient_id`, `provider_id`, `encounter_id`, and `body` in request bodies and metadata, never in URL paths or query strings, because URLs tend to leak into access logs, browser history, and CDN records. Your client should follow the same rule.
- **Never put PHI in error messages you surface to end users.** Error `message` fields can contain echoed field names or short fragments; treat them as staff-only and show end users a generic message plus the `request_id`.

## 8.2 Authentication and authorization

Notebook uses OAuth2 for all three protocols. The primary flow is **client credentials**, issued per integration:

1. Your Notebook administrator registers your integration and issues a `client_id` and `client_secret`.
2. Your service exchanges those credentials for an access token at `/oauth/token` (see [§3.2](./03-getting-started.md#32-get-an-access-token)).
3. The access token carries three claims that matter: `org_id` (determines which organization's data you see), `scopes` (determines which operations you can perform), and `exp` (one hour from issue).

**Scopes.** Request the narrowest set your integration needs.

| Scope              | Grants                                            |
|--------------------|---------------------------------------------------|
| `notes:read`       | `GetNote`, `ListNotes`, `GetNoteMetrics`, subscriptions |
| `notes:write`      | `CreateNote`                                      |
| `notes:analyze`    | `AnalyzeNote`                                     |
| `notes:admin`      | All of the above, plus future administrative endpoints |

Tokens missing a required scope return `PERMISSION_DENIED`, not `UNAUTHENTICATED` — use that distinction when debugging.

**Secret handling.** Store `client_secret` in a secrets manager (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager, Azure Key Vault). Never commit it to source control. Rotate it at least every 90 days, and immediately on any suspected exposure.

**Token caching.** Cache the access token for its full lifetime minus a 60-second safety margin. Refresh on expiry or on a `401 UNAUTHENTICATED` response, whichever comes first.

**API keys.** Non-PHI sandbox only. They are passed as `x-api-key` header (REST/GraphQL) or metadata (gRPC). Production endpoints reject API-key authentication outright.

## 8.3 Transport security

All public endpoints require TLS 1.2 or higher; TLS 1.3 is preferred. Notebook publishes a `strict-transport-security` header with a one-year `max-age`.

**mTLS for service-to-service gRPC.** When the caller is a backend service on a trusted network, add mTLS on top of the bearer token. Your administrator issues a client certificate; present it during the TLS handshake. Notebook validates both the certificate fingerprint and the bearer token; missing either one rejects the call. Notebook's own internal gRPC traffic between the gateway, the Metrics service, and the Analysis service is mTLS-only and never traverses the public internet.

**REST and GraphQL.** In v1, mTLS is available only on the gRPC endpoint. REST and GraphQL are protected by TLS (bearer-token auth only). If you need certificate-level authentication for HTTP-based traffic, use gRPC for that integration path; a mutually authenticated HTTP variant is on the roadmap.

**Certificate pinning** is optional. If your threat model requires it, pin to the certificate's intermediate CA rather than the leaf certificate; leaf certificates rotate frequently.

## 8.4 Audit logging

Every successful write and every access to PHI is recorded to an append-only audit log. Each entry captures:

- `timestamp` (UTC, millisecond precision)
- `request_id` — the same ID surfaced on errors, so you can correlate
- `actor_type` (`user` via delegated auth, or `service` via client credentials)
- `actor_id` — the `sub` claim from the token
- `org_id`
- `action` — for example, `note.create`, `note.read`, `note.analyze`, `metrics.read`
- `resource_id` — the note ID when applicable
- `result` — `allowed` or `denied`, with the Notebook error code on denial
- `source_ip` and `user_agent`

Audit logs are retained for seven years (the HIPAA-recommended retention window) and are not included in note-deletion operations. Your compliance officer can request an export in JSONL format for a specified time range.

Failed authentication attempts (`UNAUTHENTICATED`) are logged separately to prevent audit-log amplification from credential-stuffing attempts.

## 8.5 Data retention and deletion

- **Default retention.** Notes and their metrics are retained indefinitely by default. Configure a shorter retention window per organization via administrative settings.
- **Deletion.** Deletion is not exposed in the v1 API. Contact your administrator, who uses an internal tooling path that performs a tombstone delete: the note `body` and its metrics are purged, while an anonymized tombstone remains in the audit log for integrity. Deletion is irreversible once confirmed.
- **Right to access / amend.** Patient-initiated requests under HIPAA §164.524/§164.526 are handled administratively. The API does not currently expose a patient-facing endpoint.
- **Backups.** Encrypted backups include PHI and are retained for 35 days. Backups older than 35 days are cryptographically shredded; this is part of the deletion chain-of-custody.
- **Region.** PHI stays in the deployment region you chose at provisioning time. Cross-region replication is opt-in and requires a separate compliance review.
