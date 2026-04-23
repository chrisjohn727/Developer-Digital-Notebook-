---
title: "Introduction to the Notebook SDK"
description: "Overview of the Notebook SDK — an intelligent clinical-notes platform for healthcare that integrates via REST, gRPC, or GraphQL with compute-first text analysis."
sidebar_position: 1
slug: /introduction
keywords:
  - notebook sdk
  - healthcare api
  - clinical notes platform
  - sdk introduction
  - rest api
  - grpc api
  - graphql api
  - text analysis
---

# 1. Introduction

*Notebook SDK Guide › Section 1*

> **Quick answer.** The Notebook SDK integrates your applications with the Notebook platform — an intelligent clinical-notes system that ingests healthcare reports, computes text metrics asynchronously, and exposes the results through REST, gRPC, and GraphQL.

**About this page.** Notebook is a healthcare-focused clinical-notes platform built on a compute-first architecture. It accepts provider notes (progress notes, discharge summaries, radiology reads), processes them once through a gRPC microservice pipeline, stores both the note and its metrics in SQLite, and exposes interchangeable APIs over three protocols. This page is for backend engineers who will integrate with Notebook.

Welcome. The Notebook SDK Guide is the reference for integrating with the Notebook platform — an intelligent clinical-notes system that reads healthcare reports, extracts text metrics and analytical signals from them, and makes those signals available to your applications through three interchangeable APIs: REST, gRPC, and GraphQL.

## What the Notebook platform does

You send a clinical note (a discharge summary, a radiology read, a progress note). Notebook persists it, hands it off to a gRPC microservice for text analysis, stores the computed metrics next to the note in SQLite, and exposes both through a single API gateway. Your applications then query that data through whichever protocol fits the integration — without ever re-running the expensive work.

## Who this guide is for

This guide is written for backend engineers who are comfortable with gRPC and GraphQL but new to the Notebook platform itself. You should be able to read a `.proto` file, write a GraphQL query, and send an HTTP request. You do not need prior domain knowledge of electronic health records; the clinical context you need is explained where it matters.

If you're looking for the architecture-level "how does it work internally," jump to [§2 Core concepts](./02-core-concepts.md#2-core-concepts). If you want running code in five minutes, go to [§3 Getting started](./03-getting-started.md#3-getting-started). If you already understand the platform and want a specific protocol reference, go straight to [§4](./04-rest-api.md#4-rest-api), [§5](./05-grpc-api.md#5-grpc-api), or [§6](./06-graphql-api.md#6-graphql-api).

## How this guide is organized

The guide is structured so you can read it end-to-end or jump in at the section you need:

- Sections 1–3 give you context and a first working call.
- Sections 4–6 document each protocol independently; they cover the same five operations, so you only need to read the section for the protocol you use.
- Section 7 is the cross-protocol error reference.
- Section 8 covers HIPAA, authentication, transport security, auditing, and retention — read it before you go to production.
- Sections 9–10 are troubleshooting, FAQ, glossary, and the full error catalog.

## Conventions

- `fixed-width` text marks identifiers, field names, endpoints, and status codes.
- Placeholder values appear in angle brackets, for example `<your-access-token>`.
- Every URL that begins with `https://api.<your-domain>` is a placeholder you replace with your deployment's hostname.
- Example payloads are illustrative. Real responses may include additional fields; never fail on unknown fields.
- "PHI" means Protected Health Information as defined by HIPAA. See [§8.1](./08-security-and-compliance.md#81-hipaa-and-phi-handling).
