---
title: Glossary
description: Domain terminology and abbreviations for MAS Coordinator
version: 1.0.0
last_updated: 2025-12-31
related: [README.md, architecture.md]
tags: [glossary, terminology, reference]
---

# Glossary

Definitions of domain-specific terms, abbreviations, and concepts used in the MAS Coordinator project.

## A

**Agent**  
A specialized AI system that handles specific types of tasks. The MAS Coordinator routes requests to two agents: GPA and UMS.

**API Key**  
Authentication token required to access DIAL services and LLM models. Format: `dial_api_key` for local development, actual keys for production.

**AsyncDial**  
Asynchronous Python client from `aidial-client` package for making API calls to DIAL-compatible services.

**Attachment**  
File or image included in a message, such as PDFs, images (PNG/JPEG), CSV files. Stored as base64-encoded data or URLs.

## C

**Chat Completion**  
OpenAI-compatible API endpoint for conversational AI interactions. Format: `POST /openai/deployments/{model}/chat/completions`.

**Choice**  
DIAL SDK object representing a single response option in a chat completion. Contains message content, custom_content, and state.

**Coordination Request**  
Pydantic model representing LLM's routing decision: which agent to use and optional additional instructions.

**Coordination Stage**  
First stage of MAS Coordinator flow where LLM analyzes user intent and decides routing.

**Custom Content**  
DIAL-specific message extension containing attachments, state, and stages. Not part of standard OpenAI API.

## D

**DDG**  
DuckDuckGo - Privacy-focused search engine used by GPA for web search. Accessed via MCP server.

**DIAL**  
**D**istributed **I**ntelligent **A**gent **L**ayer - EPAM's framework for building multi-agent AI systems. Provides SDK, core services, and UI.

**DIAL Core**  
Central gateway service in DIAL ecosystem. Routes requests between UI, agents, and LLM models. Runs on port 8080.

**DIAL SDK**  
Python framework (`aidial-sdk`) for building DIAL-compatible chat applications. Provides ChatCompletion base class and utilities.

**Deployment Name**  
Identifier for LLM model in DIAL Core config. Examples: `gpt-4o`, `dall-e-3`, `mas-coordinator`.

## E

**EPAM AI Proxy**  
EPAM's gateway to OpenAI models (GPT-4o, DALL-E). URL: `https://ai-proxy.lab.epam.com`.

## G

**Gateway**  
Design pattern isolating agent-specific communication logic. See [ADR-001](adr/001-gateway-pattern.md).

**GPA**  
**G**eneral-**P**urpose **A**gent - Multi-tool agent equipped with web search (DuckDuckGo), RAG, Python interpreter, and image generation. Runs on port 8052.

## J

**JSON Schema**  
Schema definition for structured LLM output. Used in coordination stage to ensure valid `CoordinationRequest` responses.

## L

**LLM**  
**L**arge **L**anguage **M**odel - AI model for text generation. MAS Coordinator uses GPT-4o for routing decisions and synthesis.

## M

**MAS**  
**M**ulti-**A**gent **S**ystem - Architecture where multiple specialized agents collaborate. MAS Coordinator routes between GPA and UMS.

**MCP**  
**M**odel **C**ontext **P**rotocol - Protocol for connecting language models to external tools and services. Used by GPA to access Python interpreter and web search.

**Message**  
Individual unit in conversation history. Contains role (user/assistant/system), content (text), and optional custom_content.

## P

**Pydantic**  
Python library for data validation using type hints. Used for models like `CoordinationRequest` and `AgentName`.

**Python Interpreter MCP**  
MCP server providing code execution capability to GPA. Runs on port 8050.

## R

**RAG**  
**R**etrieval-**A**ugmented **G**eneration - Technique for answering questions by searching uploaded documents. GPA supports PDF, TXT, CSV.

**Redis**  
In-memory data store used by DIAL Core for conversation state and caching. Runs on port 6379.

**Request**  
DIAL SDK object representing incoming chat completion request. Contains messages, headers, and metadata.

## S

**SSE**  
**S**erver-**S**ent **E**vents - Streaming protocol for real-time updates. Format: `data: {json}\n\ndata: [DONE]`.

**Stage**  
Real-time progress indicator in DIAL UI. Shows current operation with collapsible content. Example: "🧭 Coordination", "🤖 GPA Agent".

**Stage Mirroring**  
Pattern where coordinator replicates agent's internal stages for UI visibility. See [ADR-005](adr/005-stage-mirroring.md).

**Stage Propagation**  
Process of forwarding stage updates from agent to coordinator to UI.

**State**  
Arbitrary JSON object stored in message's `custom_content.state` for conversation continuity. GPA stores tool call history, UMS stores conversation ID.

**Streaming**  
Incremental response delivery via SSE. Enables real-time display of LLM output before completion.

**Structured Output**  
LLM response constrained to follow JSON schema. Ensures type-safe, parsable output.

**Synthesis Stage**  
Final stage where LLM transforms agent's technical output into user-friendly response.

## T

**TTFT**  
**T**ime **T**o **F**irst **T**oken - Latency metric measuring time until first content chunk arrives.

## U

**UMS**  
**U**sers **M**anagement **S**ervice - Backend API for CRUD operations on user data. Runs on port 8040.

**UMS Agent**  
AI agent specialized in user management tasks via UMS MCP server. Runs on port 8042.

**UMS MCP Server**  
MCP server providing user management tools to UMS Agent. Runs on port 8041.

**Uvicorn**  
ASGI server for running Python web applications. MAS Coordinator runs via `uvicorn task.app:app`.

## Abbreviations

| Abbreviation | Full Term |
|--------------|-----------|
| ADR | Architecture Decision Record |
| API | Application Programming Interface |
| ASGI | Asynchronous Server Gateway Interface |
| CLI | Command Line Interface |
| CRUD | Create, Read, Update, Delete |
| CSV | Comma-Separated Values |
| DALL-E | OpenAI's image generation model |
| DDG | DuckDuckGo |
| DIAL | Distributed Intelligent Agent Layer |
| GPT | Generative Pre-trained Transformer |
| GPA | General-Purpose Agent |
| HTTP | Hypertext Transfer Protocol |
| JSON | JavaScript Object Notation |
| LLM | Large Language Model |
| MAS | Multi-Agent System |
| MCP | Model Context Protocol |
| MIME | Multipurpose Internet Mail Extensions |
| PDF | Portable Document Format |
| RAG | Retrieval-Augmented Generation |
| REST | Representational State Transfer |
| SDK | Software Development Kit |
| SSE | Server-Sent Events |
| TTFT | Time To First Token |
| UI | User Interface |
| UMS | Users Management Service |
| URL | Uniform Resource Locator |
| UUID | Universally Unique Identifier |

## DIAL-Specific Terms

**aidial-client**  
Python package for making API calls to DIAL services. Provides `AsyncDial` client class.

**aidial-sdk**  
Python framework for building DIAL-compatible applications. Provides `DIALApp`, `ChatCompletion`, `Request`, `Response` classes.

**custom_content**  
DIAL extension to OpenAI message format. Adds `attachments`, `state`, and `stages` fields.

**x-conversation-id**  
HTTP header for conversation tracking across requests. Used by DIAL Core and agents for context management.

## Port Reference

| Service | Port | Description |
|---------|------|-------------|
| DIAL Chat UI | 3000 | Web interface |
| DIAL Themes | 3001 | Theme service |
| DIAL Core | 8080 | API gateway |
| MAS Coordinator | 8055 | This application |
| GPA Agent | 8052 | General-purpose agent |
| UMS Agent | 8042 | User management agent |
| UMS MCP Server | 8041 | User mgmt MCP |
| User Service | 8040 | User database API |
| Python Interpreter MCP | 8050 | Code execution |
| DuckDuckGo MCP | 8051 | Web search |
| Redis | 6379 | State storage |
| Redis Insight | 6380 | Redis GUI |

## Related Documents

- [Architecture](architecture.md) - System design details
- [API Reference](api.md) - Interface specifications
- [Setup Guide](setup.md) - Installation instructions
- [ADR Index](adr/README.md) - Architecture decisions

---

**Last Updated**: 2025-12-31  
**Maintainer**: Documentation team
