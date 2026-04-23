---
title: "gRPC API reference: NotebookService, proto, status codes"
description: "Complete gRPC reference: the notebook.v1.NotebookService schema, five RPCs, OAuth2 plus optional mTLS authentication, Python and Node samples, and canonical status codes."
sidebar_position: 5
slug: /grpc-api
keywords:
  - notebook grpc
  - grpc api reference
  - notebookservice proto
  - protobuf schema
  - grpc healthcare
  - grpc reflection
  - grpc mtls
  - grpc python client
  - grpc node client
---

# 5. gRPC API

*Notebook SDK Guide › Section 5*

> **Quick answer.** The Notebook gRPC service notebook.v1.NotebookService is hosted at grpc.<your-domain>:443 and exposes the same five operations as REST. Auth is OAuth2 bearer tokens in metadata, with optional mTLS for server-to-server calls. Server reflection is enabled on non-production.

**About this page.** This page is the full gRPC reference for the Notebook platform. It is the lowest-latency, strongest-typed way to talk to Notebook and the recommended protocol for high-throughput ingestion from EHR-adjacent systems.

The gRPC API is the lowest-latency, strongest-typed way to talk to Notebook. It's the protocol the internal microservices use to talk to each other, and the one we recommend for high-throughput ingestion from EHR-adjacent systems.

This section assumes you're comfortable generating stubs from a `.proto` file. If you're not, start with [§4 REST](./04-rest-api.md#4-rest-api) or [§6 GraphQL](./06-graphql-api.md#6-graphql-api).

## 5.1 Service endpoint and reflection

All RPCs live on a single service, `notebook.v1.NotebookService`, hosted at:

```
grpc.<your-domain>:443
```

TLS is mandatory on the public endpoint. Plain-text gRPC is available only inside the deployment's private network for service-to-service calls that use mTLS (see [§5.2](#52-authentication)).

Server reflection is enabled, so tools like `grpcurl`, BloomRPC, and Evans can discover the service without a local `.proto` copy:

```bash
grpcurl grpc.<your-domain>:443 list
# notebook.v1.NotebookService

grpcurl grpc.<your-domain>:443 describe notebook.v1.NotebookService
```

> **Hosting your own.** Self-hosted deployments expose reflection by default on non-production environments. In production, disable reflection and ship the `.proto` file (§5.3) alongside your client to reduce attack surface.

## 5.2 Authentication

Authentication is OAuth2 bearer tokens in gRPC metadata:

```
authorization: Bearer <access-token>
```

Pass it via your language's metadata/credentials API (see the code samples below). The token is obtained the same way as for REST — see [§3.2](./03-getting-started.md#32-get-an-access-token).

**mTLS (optional but recommended for server-to-server).** When the caller is another backend service rather than a user-facing application, add mTLS on top of the bearer token. Your Notebook administrator issues a client certificate scoped to your organization. Present it during the TLS handshake; the server validates both the certificate and the bearer token before accepting the RPC. mTLS is required for Notebook's own internal gRPC traffic and is what the Metrics and Analysis services mutually authenticate with.

API keys are available for non-PHI sandbox testing only. They are passed as `x-api-key` metadata and are rejected on production endpoints.

## 5.3 .proto definition

The full schema is published at:

```
https://api.<your-domain>/proto/notebook/v1/notebook.proto
```

Abbreviated here for reference:

```proto
syntax = "proto3";

package notebook.v1;

import "google/protobuf/timestamp.proto";
import "google/protobuf/empty.proto";

service NotebookService {
  rpc CreateNote     (CreateNoteRequest)     returns (Note);
  rpc GetNote        (GetNoteRequest)        returns (Note);
  rpc ListNotes      (ListNotesRequest)      returns (ListNotesResponse);
  rpc AnalyzeNote    (AnalyzeNoteRequest)    returns (Note);
  rpc GetNoteMetrics (GetNoteMetricsRequest) returns (NoteMetrics);
}

enum NoteType {
  NOTE_TYPE_UNSPECIFIED = 0;
  PROGRESS   = 1;
  DISCHARGE  = 2;
  RADIOLOGY  = 3;
  LAB        = 4;
  REFERRAL   = 5;
  OTHER      = 6;
}

enum NoteStatus {
  NOTE_STATUS_UNSPECIFIED = 0;
  DRAFT       = 1;
  PROCESSING  = 2;
  READY       = 3;
  FAILED      = 4;
}

message Note {
  string id = 1;
  string org_id = 2;
  string patient_id = 3;
  string provider_id = 4;
  string encounter_id = 5;
  NoteType note_type = 6;
  string source_system = 7;
  string body = 8;
  NoteStatus status = 9;
  google.protobuf.Timestamp created_at = 10;
  google.protobuf.Timestamp updated_at = 11;
  string failure_reason = 12;
  NoteMetrics metrics = 13;   // populated when status == READY
}

message NoteMetrics {
  string note_id = 1;
  int32 word_count = 2;
  int32 character_count = 3;
  int32 sentence_count = 4;
  int32 reading_time_seconds = 5;
  string metrics_version = 6;
  google.protobuf.Timestamp computed_at = 7;
}

message CreateNoteRequest {
  string patient_id = 1;
  string provider_id = 2;
  string encounter_id = 3;
  NoteType note_type = 4;
  string source_system = 5;
  string body = 6;
  // REQUIRED. Caller-supplied UUID for idempotency.
  // May be set on this field OR sent as `idempotency-key` metadata (but not both with different values).
  string idempotency_key = 7;
}

message GetNoteRequest        { string id = 1; }
message GetNoteMetricsRequest { string note_id = 1; }

message ListNotesRequest {
  string patient_id  = 1;
  string provider_id = 2;
  NoteType note_type = 3;
  NoteStatus status  = 4;
  int32 page_size    = 5;   // 1..100, default 25
  string page_token  = 6;
}

message ListNotesResponse {
  repeated Note notes = 1;
  string next_page_token = 2;
}

message AnalyzeNoteRequest {
  string id = 1;
  bool force = 2;
  repeated string analyses = 3;   // v1: ["metrics"]
}
```

Generate stubs with `protoc` or your language's native toolchain (`grpc_tools.protoc` for Python, `@grpc/proto-loader` or `ts-proto` for Node).

## 5.4 RPC reference

### 5.4.1 CreateNote

Creates a note and kicks off asynchronous analysis. Returns a `Note` with `status: PROCESSING`.

The `idempotency_key` is **required** (matching REST and GraphQL). It may be passed either as the `CreateNoteRequest.idempotency_key` field or as an `idempotency-key` metadata entry. If both are present, they must match or the call is rejected with `INVALID_ARGUMENT`. Missing in both locations returns `INVALID_ARGUMENT`.

**Python**

```python
import os, uuid, grpc
from notebook.v1 import notebook_pb2, notebook_pb2_grpc

channel = grpc.secure_channel(
    "grpc.<your-domain>:443",
    grpc.ssl_channel_credentials(),
)
stub = notebook_pb2_grpc.NotebookServiceStub(channel)

request = notebook_pb2.CreateNoteRequest(
    patient_id="pt_001",
    provider_id="pr_042",
    note_type=notebook_pb2.PROGRESS,
    body="Patient reports improved mobility since last visit.",
    idempotency_key=str(uuid.uuid4()),
)

metadata = (("authorization", f"Bearer {os.environ['NOTEBOOK_TOKEN']}"),)
note = stub.CreateNote(request, metadata=metadata, timeout=10)
print(note.id, note.status)
```

**Node / TypeScript**

```ts
import * as grpc from "@grpc/grpc-js";
import { randomUUID } from "node:crypto";
import { NotebookServiceClient } from "./generated/notebook/v1/notebook_grpc_pb";
import { CreateNoteRequest, NoteType } from "./generated/notebook/v1/notebook_pb";

const client = new NotebookServiceClient(
  "grpc.<your-domain>:443",
  grpc.credentials.createSsl(),
);

const req = new CreateNoteRequest();
req.setPatientId("pt_001");
req.setProviderId("pr_042");
req.setNoteType(NoteType.PROGRESS);
req.setBody("Patient reports improved mobility since last visit.");
req.setIdempotencyKey(randomUUID());

const metadata = new grpc.Metadata();
metadata.add("authorization", `Bearer ${process.env.NOTEBOOK_TOKEN}`);

client.createNote(req, metadata, (err, note) => {
  if (err) throw err;
  console.log(note.getId(), note.getStatus());
});
```

Notable status codes: `INVALID_ARGUMENT` (missing field, body > 1 MB, mismatched idempotency key), `ALREADY_EXISTS` (same `idempotency_key` with a different payload), `RESOURCE_EXHAUSTED` (rate limit).

### 5.4.2 GetNote

Returns a `Note`. If `status == READY`, `Note.metrics` is populated.

**Python**

```python
note = stub.GetNote(
    notebook_pb2.GetNoteRequest(id=note_id),
    metadata=metadata,
    timeout=5,
)
```

Notable status codes: `NOT_FOUND` (note doesn't exist or belongs to a different org).

### 5.4.3 ListNotes

Paginated listing. `next_page_token` is empty when you reach the end.

**Node / TypeScript**

```ts
import { ListNotesRequest } from "./generated/notebook/v1/notebook_pb";

const req = new ListNotesRequest();
req.setPatientId("pt_001");
req.setPageSize(50);

client.listNotes(req, metadata, (err, res) => {
  if (err) throw err;
  const notes = res.getNotesList();
  const nextToken = res.getNextPageToken();
});
```

Notable status codes: `INVALID_ARGUMENT` (bad `page_token`, `page_size` > 100).

### 5.4.4 AnalyzeNote

Re-runs analysis on an existing note. Returns the updated `Note` with `status: PROCESSING`.

**Python**

```python
note = stub.AnalyzeNote(
    notebook_pb2.AnalyzeNoteRequest(id=note_id, force=True, analyses=["metrics"]),
    metadata=metadata,
    timeout=10,
)
```

Notable status codes: `NOT_FOUND`, `FAILED_PRECONDITION` (note is already `PROCESSING` and `force` is false), `UNAVAILABLE` (downstream Metrics service is down).

### 5.4.5 GetNoteMetrics

Fetches only the metrics. Cheaper than `GetNote` when you don't need the body.

**Python**

```python
try:
    metrics = stub.GetNoteMetrics(
        notebook_pb2.GetNoteMetricsRequest(note_id=note_id),
        metadata=metadata,
        timeout=5,
    )
except grpc.RpcError as e:
    if e.code() == grpc.StatusCode.FAILED_PRECONDITION:
        # Note exists but metrics aren't READY yet.
        ...
    else:
        raise
```

Notable status codes: `NOT_FOUND`, `FAILED_PRECONDITION` (status != READY).

## 5.5 gRPC status codes

gRPC uses its canonical status-code set. Notebook maps every error into one of these. Each status code is also surfaced in trailing metadata with `x-notebook-error-code` (the Notebook-specific string from [§7.1](./07-error-handling.md#71-unified-error-model)) and `x-notebook-request-id`.

| gRPC code            | Numeric | When Notebook returns it                                             |
|----------------------|---------|----------------------------------------------------------------------|
| `OK`                 | 0       | Success.                                                             |
| `INVALID_ARGUMENT`   | 3       | Malformed request, missing required field, bad enum, body too large. |
| `NOT_FOUND`          | 5       | Note doesn't exist or is in a different org.                         |
| `ALREADY_EXISTS`     | 6       | `idempotency_key` collision with a different payload.                |
| `PERMISSION_DENIED`  | 7       | Token lacks the required scope.                                      |
| `RESOURCE_EXHAUSTED` | 8       | Rate limit. See trailing `retry-after-ms` metadata.                  |
| `FAILED_PRECONDITION`| 9       | Note not in a valid state for the RPC (for example, metrics not ready, or already processing). |
| `UNAUTHENTICATED`    | 16      | Missing, expired, or malformed bearer token.                         |
| `UNAVAILABLE`        | 14      | Downstream service unreachable. Retry with exponential backoff.      |
| `DEADLINE_EXCEEDED`  | 4       | Your deadline elapsed. Retry with a larger deadline or backoff.      |
| `INTERNAL`           | 13      | Unexpected server error. Safe to retry.                              |

The unified Notebook error-code strings (for example, `METRICS_NOT_READY`, `DUPLICATE_IDEMPOTENCY_KEY`) are identical across all three protocols and are listed in [§7.1](./07-error-handling.md#71-unified-error-model) and the catalog in [§10.2](./10-appendix.md#102-full-error-catalog).
