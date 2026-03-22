# MAARS Critical Gap Registry: Adversarial Audit Findings

**Date:** March 22, 2026
**Project:** MAARS — Master Autonomous Agentic Runtime System
**Classification:** Internal Audit Report

---

## Executive Summary

Following the discovery that the entire MCP/API integration layer was missing from the MAARS Technical Architecture Design Spec, an adversarial, line-by-line audit was conducted across all documentation. The goal was to identify "phantom architecture" — components, protocols, or data flows that are named and relied upon by the system, but lack the implementation detail required for a development team to actually build them.

The audit revealed **seven critical implementation gaps** across the orchestration, observability, and economic layers. If left unaddressed, these gaps will cause immediate blockers during Phase 1 and Phase 2 development.

This registry catalogs each gap, assesses its blast radius, and provides the exact remediation specification required to unblock the engineering team.

---

## 1. The "Phantom Protocol" Gaps

### Gap 1.1: The Universal Meta-Language for Prompts
**Severity:** CRITICAL (Blocker for Phase 1)
**Location in Spec:** Section 5.5.1 (`vessel-llm-router`)
**The Claim:** *"Translates prompts from a universal meta-language into model-specific formats. This ensures that prompts designed for one model work correctly on another."*
**The Reality:** The spec never defines this "universal meta-language." There is no schema, no syntax, and no mapping logic provided.
**Blast Radius:** Without this, the `vessel-llm-router` cannot function as described. If developers build prompts natively for GPT-4.1, the fallback chain to Claude 3.5 or Llama 3 will fail because the tool-calling syntax and system prompt structures are fundamentally different.
**Remediation Required:**
- Define a JSON-based abstract syntax tree (AST) for prompts that standardizes `system`, `user`, `assistant`, and `tool` roles.
- Provide the exact mapping functions (in Go) that translate this AST into OpenAI's `tools` array, Anthropic's `tools` block, and Mistral's tool-calling format.

### Gap 1.2: The A2A JSON-RPC 2.0 Payload Schemas
**Severity:** HIGH (Blocker for Phase 3)
**Location in Spec:** Section 5.3.5 (A2A Protocol Server)
**The Claim:** *"Exposes a JSON-RPC 2.0 over HTTPS endpoint... Key A2A operations implemented: `message/send`, `tasks/get`, `tasks/cancel`, `tasks/subscribe`."*
**The Reality:** The spec lists the method names but provides zero payload schemas. What does a `message/send` payload actually look like? How is the Verifiable Credential attached?
**Blast Radius:** Cross-org commerce is impossible without strict, byte-for-byte payload definitions. Two different organizations building MAARS instances will not be able to communicate.
**Remediation Required:**
- Provide the exact JSON Schema definitions for all four A2A JSON-RPC methods.
- Define the HTTP headers required (e.g., `X-A2A-Signature`, `X-A2A-DID`).

---

## 2. The "Missing Engine" Gaps

### Gap 2.1: The Right-Sizing Engine Heuristics
**Severity:** CRITICAL (Blocker for Phase 1)
**Location in Spec:** Section 5.2.2 (`vessel-orchestrator`)
**The Claim:** *"The orchestrator's Right-Sizing Engine analyzes each task's complexity and assigns the appropriate cognitive tier (Nano, Mid, Frontier)."*
**The Reality:** The spec states *what* the engine does, but not *how* it does it. Is it a heuristic ruleset? Is it an LLM call? Is it a trained classifier?
**Blast Radius:** If the orchestrator cannot automatically assign tiers, every task defaults to Frontier (burning massive amounts of capital) or Nano (failing complex tasks). The core economic value proposition of MAARS collapses.
**Remediation Required:**
- Define the exact algorithm for the Right-Sizing Engine.
- **Recommendation:** Implement it as a fast, deterministic heuristic based on the `TaskDefinition`'s `tool_allowlist` size, instruction token count, and required output schema complexity, rather than a slow LLM call.

### Gap 2.2: The Context Graph Engine (Arize Phoenix) Integration
**Severity:** HIGH (Blocker for Phase 3)
**Location in Spec:** Section 5.6.2 (Inline Guardrail Agent)
**The Claim:** *"Feeds its decisions back into the Context Graph Engine (Arize Phoenix), which builds a FailurePattern database over time."*
**The Reality:** The spec lists Arize Phoenix as the tool, but provides no data pipeline or integration logic. How do `GuardrailDecision` records in PostgreSQL become `FailurePattern` records in Arize?
**Blast Radius:** The "compounding intelligence flywheel" and the self-improvement loop will not function. The Guardrail Agent will block the same mistakes repeatedly without ever learning.
**Remediation Required:**
- Define the exact OpenTelemetry span attributes required by Arize Phoenix for LLM evaluation.
- Write the Python background worker that queries Arize's GraphQL API to extract `FailurePattern` clusters and write them back to the MAARS database.

---

## 3. The "Unspecified Data Flow" Gaps

### Gap 3.1: The Materialize Live Data Ingestion Pipeline
**Severity:** HIGH (Blocker for Phase 4)
**Location in Spec:** Section 5.7.2 (`vessel-simulation`)
**The Claim:** *"Powered by Materialize — a real-time SQL engine that ingests live Kafka streams and maintains continuously updated materialized views."*
**The Reality:** The spec mentions Kafka streams, but MAARS's internal Kafka topics (`goal.*`, `task.*`, `agent.*`) do not contain the "current state of the enterprise" (e.g., inventory levels, CRM state). Where is Materialize getting this data?
**Blast Radius:** The Digital Twin is useless if it only simulates internal agent state. It must simulate the *enterprise's* state.
**Remediation Required:**
- Define the Change Data Capture (CDC) pipeline (e.g., Debezium) required to stream external enterprise databases (Salesforce, SAP, custom Postgres) into the MAARS Kafka cluster so Materialize can consume them.

### Gap 3.2: The Memory Provenance Cryptography
**Severity:** MEDIUM (Blocker for Phase 2)
**Location in Spec:** Section 5.5.2 (`vessel-memory`)
**The Claim:** *"Every MemoryNode has a provenance_hash that cryptographically links it to its source... This prevents memory poisoning attacks."*
**The Reality:** The spec does not define how this hash is calculated. What fields are concatenated? What hashing algorithm is used? How is the source signature verified during retrieval?
**Blast Radius:** If the hashing algorithm is not standardized, memory provenance cannot be verified, rendering the "poisoning prevention" claim false.
**Remediation Required:**
- Define the exact SHA-256 concatenation string for `MemoryNode` provenance (e.g., `hash(tenant_id + agent_id + task_id + tool_name + raw_output + timestamp)`).

---

## 4. The "UI/UX Reality" Gap

### Gap 4.1: The "No-Code Canvas" Agent Builder
**Severity:** HIGH (Blocker for Go-To-Market)
**Location in Spec:** Section 9.2.4 (`/app/agents`)
**The Claim:** *"The No-Code Canvas UI allows non-technical business leaders to create agents by selecting from a library of pre-built agent templates... and configuring them via a simple form interface."*
**The Reality:** The spec details the Live Canvas (for observing agents) but provides zero data model or component specs for the *Builder* Canvas. Where are these "pre-built templates" stored? How does a form UI generate a complex LangGraph DAG?
**Blast Radius:** Without this, MAARS remains a developer-only tool. The "non-technical business leader" persona cannot use the platform, destroying the enterprise SaaS value proposition.
**Remediation Required:**
- Define the `AgentTemplate` database schema.
- Specify the React component architecture for the visual DAG builder (node types for Tools, Sub-Agents, and Logic Gates).
- Define the compiler that translates the visual DAG JSON into a `TaskGraph` payload for the orchestrator.

---

## Conclusion & Next Steps

The MAARS architecture is conceptually brilliant, but it suffers from "abstraction leakage" — assuming that naming a complex system (like a "Right-Sizing Engine" or a "Universal Meta-Language") is the same as designing it. 

**Recommended Action:** The development team must pause feature work on Phase 2/3 and immediately draft Technical Design Documents (TDDs) for the seven gaps identified above. Specifically, the **Universal Meta-Language** and the **Right-Sizing Engine** must be fully specified before `vessel-orchestrator` or `vessel-llm-router` code is written, as they dictate the core data structures of the entire platform.
