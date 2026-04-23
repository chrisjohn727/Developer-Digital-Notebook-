---
title: "Getting started: your first Notebook API call"
description: "Five-minute Notebook quickstart. Obtain an OAuth2 token and create a clinical note using curl, Python, or Node.js, then poll or subscribe for analysis completion."
sidebar_position: 3
slug: /getting-started
keywords:
  - notebook getting started
  - oauth2 client credentials
  - create note api
  - createnote example
  - healthcare api quickstart
  - python api client
  - node.js api client
---

# 3. Getting started

*Notebook SDK Guide › Section 3*

> **Quick answer.** Get an OAuth2 access token at /oauth/token, then POST to /v1/notes with an Idempotency-Key. The response returns status: PROCESSING; poll GetNote or subscribe to the GraphQL noteAnalyzed subscription until status becomes READY.

**About this page.** A step-by-step quickstart for the Notebook platform, covering OAuth2 token acquisition, the first CreateNote call in three languages (curl, Python, Node/TypeScript), and how to wait for asynchronous metrics analysis to complete.

In this section you'll make your first successful call to Notebook. By the end, you'll have created a note, waited for analysis to finish, and read the computed metrics back — using whichever of the three protocols you prefer.

## 3.1 Prerequisites

- A Notebook deployment URL. All examples use `https://api.<your-domain>` — substitute your hostname.
- An OAuth2 client credential (client ID + secret) issued by your Notebook administrator.
- One of: curl; Python 3.9+ with `requests`, `grpcio`, or `gql`; or Node 18+ with `fetch`, `@grpc/grpc-js`, or `graphql-request`.

If you don't have credentials yet, request them from your Notebook administrator. Credentials are scoped to one organization, and the resulting token determines which notes you can read and write.

## 3.2 Get an access token

Notebook uses the OAuth2 client-credentials flow. Full details are in [§8.2](./08-security-and-compliance.md#82-authentication-and-authorization); here's the minimum you need to make your first call.

```bash
curl -X POST https://api.<your-domain>/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "<your-client-id>",
    "client_secret": "<your-client-secret>",
    "scope": "notes:read notes:write"
  }'
```

The response contains an `access_token` that is valid for one hour. Pass it as `Authorization: Bearer <access_token>` on every subsequent request.

> **Store client secrets in a secrets manager**, not in source control. See §8 for the full security story.

## 3.3 Your first CreateNote (curl / REST)

This is the shortest path to a working call. It creates a progress note and returns `202 ACCEPTED` immediately with `status: PROCESSING`.

```bash
curl -X POST https://api.<your-domain>/v1/notes \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 7b8f0e2a-3d4c-4e8b-9f2a-1c6e5a9b4d7f" \
  -d '{
    "patient_id": "pt_001",
    "provider_id": "pr_042",
    "note_type": "PROGRESS",
    "body": "Patient reports improved mobility since last visit. Pain well controlled on current regimen."
  }'
```

Expected response:

```json
{
  "id": "3b7a9c12-5e4d-4b2f-8c1a-9d2e6f3b4a5c",
  "status": "PROCESSING",
  "patient_id": "pt_001",
  "provider_id": "pr_042",
  "note_type": "PROGRESS",
  "created_at": "2026-04-22T15:04:05Z"
}
```

Note the `status: PROCESSING`. Metrics are being computed out-of-band. See [§3.6](#36-wait-for-analysis-to-finish) for how to know when they're ready.

## 3.4 Your first CreateNote (Python)

Install the HTTP client:

```bash
pip install requests
```

Then:

```python
import os
import uuid
import requests

API = "https://api.<your-domain>"
TOKEN = os.environ["NOTEBOOK_TOKEN"]

response = requests.post(
    f"{API}/v1/notes",
    headers={
        "Authorization": f"Bearer {TOKEN}",
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
response.raise_for_status()
note = response.json()
print(f"Created note {note['id']} with status {note['status']}")
```

Two things to notice:

1. The `Idempotency-Key` is a fresh UUID per logical create. On retry, reuse it.
2. `raise_for_status()` surfaces `4xx`/`5xx` as exceptions. The error body follows the unified error model in [§7.1](./07-error-handling.md#71-unified-error-model).

## 3.5 Your first CreateNote (Node / TypeScript)

```ts
import { randomUUID } from "node:crypto";

const API = "https://api.<your-domain>";
const TOKEN = process.env.NOTEBOOK_TOKEN!;

const res = await fetch(`${API}/v1/notes`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${TOKEN}`,
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

if (!res.ok) {
  throw new Error(`CreateNote failed: ${res.status} ${await res.text()}`);
}

const note = await res.json();
console.log(`Created note ${note.id} with status ${note.status}`);
```

## 3.6 Wait for analysis to finish

Metrics are computed asynchronously (see [§2.8](./02-core-concepts.md#28-asynchronous-processing)). You have two options.

**Option A — poll.** Simple and fine for batch jobs.

```python
import time

for _ in range(30):  # up to ~30 seconds
    r = requests.get(f"{API}/v1/notes/{note['id']}",
                     headers={"Authorization": f"Bearer {TOKEN}"},
                     timeout=5)
    r.raise_for_status()
    current = r.json()
    if current["status"] == "READY":
        print("Metrics:", current["metrics"])
        break
    if current["status"] == "FAILED":
        raise RuntimeError(f"Analysis failed: {current.get('failure_reason')}")
    time.sleep(1)
else:
    raise TimeoutError("Analysis did not complete in 30s")
```

**Option B — subscribe.** Recommended for UIs and long-lived clients. Use the GraphQL subscription `noteAnalyzed(noteId)`; see [§6.4](./06-graphql-api.md#64-queries-mutations-subscriptions).

## 3.7 Read the metrics

Once `status == READY`, fetch the metrics:

```bash
curl https://api.<your-domain>/v1/notes/3b7a9c12-.../metrics \
  -H "Authorization: Bearer <access-token>"
```

```json
{
  "note_id": "3b7a9c12-5e4d-4b2f-8c1a-9d2e6f3b4a5c",
  "word_count": 14,
  "character_count": 93,
  "sentence_count": 2,
  "reading_time_seconds": 5,
  "metrics_version": "1.0.0",
  "computed_at": "2026-04-22T15:04:07Z"
}
```

## 3.8 Next steps

You've made a round trip. From here:

- For the full REST reference, go to [§4](./04-rest-api.md#4-rest-api).
- For low-latency, strongly typed backend integration, see the gRPC section in [§5](./05-grpc-api.md#5-grpc-api).
- For UI-driven fetch-only-what-you-need access, including the `noteAnalyzed` subscription, see [§6](./06-graphql-api.md#6-graphql-api).
- Before you go to production, read [§8 Security and compliance](./08-security-and-compliance.md#8-security-and-compliance).
