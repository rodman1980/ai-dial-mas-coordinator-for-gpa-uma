---
title: Architecture Decision Records
description: Index of all architecture decisions for MAS Coordinator
version: 1.0.0
last_updated: 2025-12-31
related: [../architecture.md]
tags: [adr, decisions, architecture]
---

# Architecture Decision Records (ADR)

This directory contains records of architectural decisions made during the development of the MAS Coordinator.

## ADR Format

Each ADR follows this structure:
- **Title**: Short, descriptive name
- **Status**: Proposed | Accepted | Rejected | Superseded
- **Context**: Problem or situation requiring a decision
- **Decision**: What was decided and why
- **Consequences**: Implications, trade-offs, and impacts
- **Alternatives Considered**: Other options that were evaluated

## Index of ADRs

| ID | Title | Status | Date |
|----|-------|--------|------|
| [001](001-gateway-pattern.md) | Gateway Pattern for Agent Communication | Accepted | 2025-12-31 |
| [002](002-three-stage-orchestration.md) | Three-Stage Orchestration Flow | Accepted | 2025-12-31 |
| [003](003-structured-output-routing.md) | Structured Output for LLM Routing | Accepted | 2025-12-31 |
| [004](004-state-management-strategy.md) | Differentiated State Management Strategy | Accepted | 2025-12-31 |
| [005](005-stage-mirroring.md) | Stage Mirroring for UI Feedback | Accepted | 2025-12-31 |

## Creating New ADRs

1. **Create file**: `docs/adr/XXX-short-title.md`
2. **Use template**: See [000-template.md](000-template.md)
3. **Number sequentially**: Next number in sequence
4. **Update this index**: Add entry to table above
5. **Link from architecture.md**: Reference in main architecture doc

## Decision Status

- **Proposed**: Under consideration
- **Accepted**: Approved and implemented
- **Rejected**: Considered but not chosen
- **Superseded**: Replaced by a later decision

## Related Documents

- [Architecture Overview](../architecture.md) - System design
- [API Reference](../api.md) - Interface specifications
- [Setup Guide](../setup.md) - Installation instructions
