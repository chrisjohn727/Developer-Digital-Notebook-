---
title: "Notebook SDK Guide"
description: "Complete developer guide for the Notebook healthcare platform — create and analyze clinical notes over REST, gRPC, or GraphQL, with OAuth2 auth, HIPAA-aware security, and a unified error model."
sidebar_position: 0
slug: /
keywords:
  - notebook sdk
  - healthcare api
  - clinical notes api
  - rest api
  - grpc api
  - graphql api
  - hipaa api
  - oauth2 healthcare
---

# Notebook SDK Guide

> **Quick answer.** Notebook is a compute-first healthcare platform for storing and analyzing clinical notes. Pick one of three protocols — REST for simplicity, gRPC for throughput, GraphQL for flexible queries — authenticate with OAuth2, and the same five operations (CreateNote, GetNote, ListNotes, GetNoteMetrics, DeleteNote) are available on all of them with a unified error model.

**About this guide.** This is the developer documentation for the Notebook platform — an intelligent notebook system that ingests healthcare reports as notes, computes text metrics through gRPC microservices, persists them in SQLite, and exposes them to clinicians so they can diagnose more precisely. The guide is written for engineers who are comfortable with gRPC and GraphQL but new to Notebook itself. It covers all three protocols in equal depth, with executable code samples in curl, Python, and Node/TypeScript.

## Start here

New to Notebook? Read these in order:

1. [Introduction](./01-introduction.md) — what Notebook is, who it's for, what it does and doesn't do in v1.
2. [Core concepts](./02-core-concepts.md) — notes, metrics, the async lifecycle, idempotency, multi-tenancy.
3. [Getting started](./03-getting-started.md) — a five-minute quickstart: get a token, create your first note, read the metrics back.

## Pick your protocol

The same five operations are available on all three protocols. Pick the one that fits your stack:

- [REST API](./04-rest-api.md) — JSON over HTTPS. The simplest surface; best for quick integrations, webhooks, and browser clients.
- [gRPC API](./05-grpc-api.md) — Protocol Buffers over HTTP/2. Best for high-throughput server-to-server calls; supports mTLS.
- [GraphQL API](./06-graphql-api.md) — Single endpoint with typed queries, mutations, and the `noteAnalyzed` subscription for push-based completion signals.

## Operate it safely

- [Error handling](./07-error-handling.md) — the unified error model across all three protocols, with code tables and retry guidance.
- [Security and compliance](./08-security-and-compliance.md) — OAuth2 scopes, mTLS, HIPAA/PHI handling, BAA, audit logs.
- [Troubleshooting and FAQ](./09-troubleshooting-and-faq.md) — common issues, how to debug them, and answers to the questions we hear most.
- [Appendix](./10-appendix.md) — the full OpenAPI / proto / SDL references, a glossary, and change log.

## What's in v1

Five operations, three protocols, async metrics computation, OAuth2 + mTLS, multi-tenancy by `org_id`, SQLite persistence, and a documented error model. The analysis service (deeper clinical signal) is on the roadmap — see §1 for the full scope.

## Conventions used in this guide

- Base URL placeholder: `https://api.<your-domain>` — substitute your deployment hostname.
- Code samples are shown in curl, Python, and Node/TypeScript. All are executable once you substitute credentials.
- Cross-references like [§8.2](./08-security-and-compliance.md#82-authentication-and-authorization) link directly to the relevant subsection.
- The Microsoft Writing Style Guide is the default: active voice, second person, sentence-case headings.
