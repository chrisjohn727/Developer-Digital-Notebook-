---
title: "GraphQL API reference: schema, queries, mutations, subscriptions"
description: "GraphQL API reference: full schema, queries (note, notes, noteMetrics), mutations (createNote, analyzeNote), and the noteAnalyzed subscription for live updates."
sidebar_position: 6
slug: /graphql-api
keywords:
  - notebook graphql
  - graphql api reference
  - graphql schema
  - graphql subscription
  - noteanalyzed subscription
  - graphql-transport-ws
  - apollo sandbox
  - graphql healthcare
---

# 6. GraphQL API

*Notebook SDK Guide › Section 6*

> **Quick answer.** The Notebook GraphQL endpoint is /graphql (HTTP) and /graphql over WebSocket for subscriptions. Queries: note, notes, noteMetrics. Mutations: createNote, analyzeNote. Subscription: noteAnalyzed(noteId) pushes one final state (READY or FAILED) and closes.

**About this page.** This page is the full GraphQL API reference for the Notebook platform. GraphQL is the recommended protocol for UIs, dashboards, and any application that benefits from push-delivered notifications when asynchronous analysis completes.

The GraphQL API is the right choice when your client wants to fetch only the fields it needs, combine multiple reads into one round trip, or subscribe to live updates. It's the protocol we recommend for UIs, clinician-facing dashboards, and any application that benefits from push-delivered notifications when analysis finishes.

## 6.1 Endpoint and playground

- **HTTP endpoint:** `https://api.<your-domain>/graphql`
- **Subscriptions endpoint (WebSocket):** `wss://api.<your-domain>/graphql`  
  Subscriptions use the `graphql-transport-ws` sub-protocol.
- **Interactive playground:** `https://api.<your-domain>/graphql/playground`

The playground is Apollo Sandbox with schema introspection enabled on non-production environments. In production, introspection is disabled to reduce attack surface; use the published SDL (§6.3) for tooling.

> **Hosting your own.** Self-hosted deployments serve the playground behind the same auth gate as the API. You can disable it entirely with the `NOTEBOOK_GRAPHQL_PLAYGROUND=off` feature flag on the gateway. The SDL is regenerated on every deployment and is available at `/graphql/schema.graphql`.

## 6.2 Authentication

Authentication is the same OAuth2 bearer token used for REST and gRPC. Pass it in the `Authorization` header on HTTP requests:

```
Authorization: Bearer <access-token>
```

For subscriptions, pass the token in the `connection_init` payload when opening the WebSocket:

```json
{ "type": "connection_init", "payload": { "Authorization": "Bearer <access-token>" } }
```

Most GraphQL client libraries (`graphql-request`, Apollo Client, `gql`) expose a `connectionParams` hook for this.

## 6.3 Schema overview

Abbreviated SDL. The full, versioned schema is published at `https://api.<your-domain>/graphql/schema.graphql`.

```graphql
scalar DateTime
scalar UUID

enum NoteType     { PROGRESS DISCHARGE RADIOLOGY LAB REFERRAL OTHER }
enum NoteStatus   { DRAFT PROCESSING READY FAILED }

type Note {
  id: UUID!
  orgId: UUID!
  patientId: String!
  providerId: String!
  encounterId: String
  noteType: NoteType!
  sourceSystem: String
  body: String!
  status: NoteStatus!
  failureReason: String
  createdAt: DateTime!
  updatedAt: DateTime!
  metrics: NoteMetrics            # null when status != READY
}

type NoteMetrics {
  noteId: UUID!
  wordCount: Int!
  characterCount: Int!
  sentenceCount: Int!
  readingTimeSeconds: Int!
  metricsVersion: String!
  computedAt: DateTime!
}

type NoteConnection {
  nodes: [Note!]!
  nextPageToken: String
}

input NoteFilter {
  patientId: String
  providerId: String
  noteType: NoteType
  status: NoteStatus
}

input CreateNoteInput {
  patientId: String!
  providerId: String!
  encounterId: String
  noteType: NoteType!
  sourceSystem: String
  body: String!
  idempotencyKey: UUID!   # required
}

input AnalyzeNoteInput {
  id: UUID!
  force: Boolean = false
  analyses: [String!] = ["metrics"]
}

type Query {
  note(id: UUID!): Note
  notes(filter: NoteFilter, pageSize: Int = 25, pageToken: String): NoteConnection!
  noteMetrics(noteId: UUID!): NoteMetrics
}

type Mutation {
  createNote(input: CreateNoteInput!): Note!
  analyzeNote(input: AnalyzeNoteInput!): Note!
}

type Subscription {
  noteAnalyzed(noteId: UUID!): Note!
}
```

## 6.4 Queries, mutations, subscriptions

### 6.4.1 Mutation: `createNote`

Creates a note. The `idempotencyKey` is required; reuse it on retries to avoid duplicates (same 24-hour contract as REST/gRPC).

```graphql
mutation CreateNote($input: CreateNoteInput!) {
  createNote(input: $input) {
    id
    status
    createdAt
  }
}
```

Variables:

```json
{
  "input": {
    "patientId": "pt_001",
    "providerId": "pr_042",
    "noteType": "PROGRESS",
    "body": "Patient reports improved mobility since last visit.",
    "idempotencyKey": "7b8f0e2a-3d4c-4e8b-9f2a-1c6e5a9b4d7f"
  }
}
```

**curl**

```bash
curl -X POST https://api.<your-domain>/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation($input: CreateNoteInput!){ createNote(input:$input){ id status } }",
    "variables": { "input": { "patientId":"pt_001","providerId":"pr_042","noteType":"PROGRESS","body":"...","idempotencyKey":"7b8f0e2a-3d4c-4e8b-9f2a-1c6e5a9b4d7f" } }
  }'
```

**Python (`gql`)**

```python
import os, uuid
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

transport = RequestsHTTPTransport(
    url="https://api.<your-domain>/graphql",
    headers={"Authorization": f"Bearer {os.environ['NOTEBOOK_TOKEN']}"},
)
client = Client(transport=transport, fetch_schema_from_transport=False)

query = gql("""
  mutation CreateNote($input: CreateNoteInput!) {
    createNote(input: $input) { id status createdAt }
  }
""")

result = client.execute(query, variable_values={
    "input": {
        "patientId": "pt_001",
        "providerId": "pr_042",
        "noteType": "PROGRESS",
        "body": "Patient reports improved mobility since last visit.",
        "idempotencyKey": str(uuid.uuid4()),
    }
})
print(result["createNote"]["id"], result["createNote"]["status"])
```

**Node / TypeScript (`graphql-request`)**

```ts
import { GraphQLClient, gql } from "graphql-request";
import { randomUUID } from "node:crypto";

const client = new GraphQLClient("https://api.<your-domain>/graphql", {
  headers: { Authorization: `Bearer ${process.env.NOTEBOOK_TOKEN}` },
});

const mutation = gql`
  mutation CreateNote($input: CreateNoteInput!) {
    createNote(input: $input) { id status createdAt }
  }
`;

const data = await client.request(mutation, {
  input: {
    patientId: "pt_001",
    providerId: "pr_042",
    noteType: "PROGRESS",
    body: "Patient reports improved mobility since last visit.",
    idempotencyKey: randomUUID(),
  },
});
```

Notable errors (extensions `code`): `VALIDATION_ERROR`, `DUPLICATE_IDEMPOTENCY_KEY`, `RATE_LIMITED`.

### 6.4.2 Query: `note`

Fetches one note by ID. Returns `null` if not found (or not in the caller's org — see §2.11).

```graphql
query GetNote($id: UUID!) {
  note(id: $id) {
    id
    status
    body
    metrics {
      wordCount
      characterCount
      sentenceCount
      readingTimeSeconds
      metricsVersion
    }
  }
}
```

Because you specify the selection set, you can drop `body` when rendering a list view and keep only the fields you need, which is the main reason to prefer GraphQL over REST for UIs.

### 6.4.3 Query: `notes`

Paginated, filterable listing. Cursor-based — pass the previous `nextPageToken` as `pageToken` on the next call.

```graphql
query ListNotes($filter: NoteFilter, $pageToken: String) {
  notes(filter: $filter, pageSize: 50, pageToken: $pageToken) {
    nodes { id status noteType updatedAt }
    nextPageToken
  }
}
```

### 6.4.4 Query: `noteMetrics`

Cheap read when you already know the note exists. Returns `null` if the note isn't `READY` yet; inspect the accompanying error extension (`METRICS_NOT_READY`) to distinguish "not ready" from "not found."

```graphql
query { noteMetrics(noteId: "3b7a9c12-…") { wordCount characterCount metricsVersion } }
```

### 6.4.5 Mutation: `analyzeNote`

Re-runs analysis on an existing note. Use when the note is in `FAILED`, or when a new `metricsVersion` ships and you want to refresh historical data.

```graphql
mutation Reanalyze($id: UUID!) {
  analyzeNote(input: { id: $id, force: true, analyses: ["metrics"] }) {
    id
    status
  }
}
```

Notable errors: `NOT_FOUND`, `CONFLICT` (already `PROCESSING`, pass `force: true`), `SERVICE_UNAVAILABLE`.

### 6.4.6 Subscription: `noteAnalyzed`

Pushes a `Note` to the subscriber when analysis completes — either successfully (`status: READY` with `metrics` populated) or with failure (`status: FAILED` with `failureReason`). Either outcome closes the subscription after one emission.

```graphql
subscription OnAnalyzed($id: UUID!) {
  noteAnalyzed(noteId: $id) {
    id
    status
    failureReason
    metrics { wordCount characterCount metricsVersion }
  }
}
```

**Node / TypeScript (`graphql-ws`)**

```ts
import { createClient } from "graphql-ws";

const client = createClient({
  url: "wss://api.<your-domain>/graphql",
  connectionParams: {
    Authorization: `Bearer ${process.env.NOTEBOOK_TOKEN}`,
  },
});

await new Promise((resolve, reject) => {
  client.subscribe(
    {
      query: `subscription($id: UUID!) {
        noteAnalyzed(noteId: $id) {
          id status failureReason
          metrics { wordCount characterCount metricsVersion }
        }
      }`,
      variables: { id: noteId },
    },
    {
      next: ({ data }) => console.log("received:", data),
      error: reject,
      complete: resolve,
    },
  );
});
```

**Python (`gql` with websockets)**

```python
from gql import Client, gql
from gql.transport.websockets import WebsocketsTransport

transport = WebsocketsTransport(
    url="wss://api.<your-domain>/graphql",
    init_payload={"Authorization": f"Bearer {TOKEN}"},
)
client = Client(transport=transport, fetch_schema_from_transport=False)

subscription = gql("""
  subscription($id: UUID!) {
    noteAnalyzed(noteId: $id) {
      id status failureReason
      metrics { wordCount characterCount metricsVersion }
    }
  }
""")

async for result in client.subscribe_async(subscription, variable_values={"id": note_id}):
    print(result)
```

If the subscription disconnects before the note is analyzed (network blip, token expiry), re-subscribe. Notebook deduplicates — if analysis has already completed before your re-subscribe, you receive the final state immediately.

> **One note at a time in v1.** `noteAnalyzed` takes a single `noteId`. To watch many notes from one dashboard, open one subscription per note (multiplex over a single WebSocket connection). A list-scoped `notesAnalyzed` variant is on the roadmap.

## 6.5 GraphQL errors and extensions

GraphQL always returns HTTP `200 OK` for valid, parseable operations, even when the operation itself fails. Errors appear in the top-level `errors` array with a machine-readable `extensions.code` that matches the Notebook-wide code set from [§7.1](./07-error-handling.md#71-unified-error-model).

```json
{
  "errors": [
    {
      "message": "patientId is required.",
      "path": ["createNote"],
      "extensions": {
        "code": "VALIDATION_ERROR",
        "field": "patientId",
        "issue": "missing",
        "requestId": "req_01HRZP8Q9X"
      }
    }
  ],
  "data": null
}
```

Always branch on `extensions.code`, not on the human-readable `message`.

| `extensions.code`            | Equivalent in REST / gRPC            | Meaning                                                |
|------------------------------|--------------------------------------|--------------------------------------------------------|
| `VALIDATION_ERROR`           | 400 / `INVALID_ARGUMENT`             | Bad input.                                             |
| `UNAUTHENTICATED`            | 401 / `UNAUTHENTICATED`              | Missing or invalid token.                              |
| `PERMISSION_DENIED`          | 403 / `PERMISSION_DENIED`            | Token lacks scope.                                     |
| `NOT_FOUND`                  | 404 / `NOT_FOUND`                    | Unknown note or wrong org.                             |
| `DUPLICATE_IDEMPOTENCY_KEY`  | 409 / `ALREADY_EXISTS`               | Idempotency key reused with different payload.         |
| `CONFLICT`                   | 409 / `FAILED_PRECONDITION`          | Invalid state for the operation.                       |
| `METRICS_NOT_READY`          | 409 / `FAILED_PRECONDITION`          | Metrics requested before `status == READY`.            |
| `RATE_LIMITED`               | 429 / `RESOURCE_EXHAUSTED`           | Rate limit; see `extensions.retryAfterMs`.             |
| `SERVICE_UNAVAILABLE`        | 503 / `UNAVAILABLE`                  | Downstream service down; retry with backoff.           |
| `INTERNAL`                   | 500 / `INTERNAL`                     | Unexpected error; safe to retry.                       |

Partial success is possible: a query that selects multiple fields may return some data and a partial error for others. Inspect both `data` and `errors` before concluding the request failed.
