# TheTable

AI-powered team meeting system built on [LangGraph](https://github.com/langchain-ai/langgraph). Autonomous AI agents with distinct roles participate in structured meetings, discuss agendas, and produce actionable outcomes — all from your terminal.

## Overview

TheTable creates realistic team meetings where AI agents collaborate like real team members. Each agent has a defined role, responsibilities, and expertise. A Host facilitates, a PM tracks progress, a TechLead makes architecture decisions — and they all discuss your agenda items with context-aware responses.

```
$ thetable --message "Start the sprint meeting"
```

```
┌──────────────── 📋 Agenda Status ────────────────┐
│  🔄 1. Project Roadmap Discussion (Host) [2:15] ← │
│  ⏳ 2. Sprint Review (PM)                         │
│  ⏳ 3. Sprint Planning (TechLead)                  │
└───────────────────────────────────────────────────┘

[Host]
Hello everyone, let's begin today's sprint meeting. The first agenda item is...

[PM]
Let me share the current project status. Based on the GitHub issues...
```

## Features

- **Autonomous agents** — Each agent has a role, responsibilities, and expertise that shape their responses
- **Agenda-driven workflow** — Structured meeting flow with automatic agenda progression
- **Hierarchical delegation** — Supervisors (e.g., TechLead) can delegate to sub-agents (Backend, Frontend)
- **MCP tool integration** — Agents access external tools like GitHub for real data
- **Per-agent LLM config** — Different models/providers per agent with `${ENV_VAR}` support
- **Two-brain LLM strategy** — Main LLM for conversation, Task LLM for extraction and analysis
- **TUI & CLI modes** — Rich terminal UI with live progress, or classic streaming output
- **Human participation** — Join the meeting as a real participant alongside AI agents

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- An OpenAI-compatible API key (OpenAI, OpenRouter, Azure OpenAI, etc.)

## Getting Started

### 1. Install

```bash
git clone https://github.com/yaklevel/thetable.git
cd thetable
uv sync
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your API key and preferred model:

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://openrouter.ai/api/v1  # or https://api.openai.com/v1

LLM_MAIN_MODEL=deepseek/deepseek-v3.2
LLM_TASK_MODEL=google/gemini-2.5-flash
```

> [!TIP]
> OpenRouter is recommended for cost efficiency. See `.env.example` for all configuration options including Azure OpenAI, local Ollama, and LangSmith tracing.

### 3. Run

```bash
uv run thetable
```

## Usage

```bash
# Default meeting
uv run thetable

# Custom message
uv run thetable -m "Emergency bug response meeting"

# Classic CLI (no TUI)
uv run thetable --no-tui

# Batch mode (non-streaming)
uv run thetable --no-stream

# Custom profiles & config
uv run thetable --profiles config/custom_profiles.yaml --config .env.prod

# With LangSmith tracing
uv run thetable --trace

# Verbose logging
uv run thetable -v
```

## Configuration

### Agent Profiles (`config/agent_profiles.yaml`)

Define meeting participants with roles, responsibilities, and optional per-agent LLM settings:

```yaml
agents:
  - name: PM
    role: project_manager
    responsibilities:
      - Project schedule management
      - Issue status tracking
    expertise:
      - Schedule planning
    mcp_tools:
      - github
    llm:  # Optional: per-agent model override
      model: "gpt-4.1-mini"
      api_key: "${OPENROUTER_API_KEY}"
      base_url: "https://openrouter.ai/api/v1"

  - name: TechLead
    role: tech_lead
    responsibilities:
      - Technical decision making
    agents:  # Hierarchical sub-agents
      - name: Backend
        role: backend_engineer
        responsibilities:
          - API design and implementation
```

> [!NOTE]
> Per-agent `llm` fields support `${ENV_VAR}` syntax for environment variable substitution. Unset fields fall back to the global `.env` configuration.

### Agendas (`config/agendas.yaml`)

```yaml
agendas:
  - title: "Sprint Review"
    description: "Review completed work from the sprint"
    required_speakers: ["PM", "TechLead"]
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key (common fallback) | — |
| `OPENAI_BASE_URL` | Base URL for API | — |
| `LLM_MAIN_MODEL` | Main conversation model | `gpt-4o-mini` |
| `LLM_TASK_MODEL` | Utility task model | `gpt-4o-mini` |
| `LLM_MAIN_TEMPERATURE` | Main LLM temperature | `0.7` |
| `LLM_TASK_TEMPERATURE` | Task LLM temperature | `0.0` |
| `MAX_TURNS` | Max meeting turns | `1000` |
| `AGENT_PROFILES_PATH` | Path to profiles YAML | `config/agent_profiles.yaml` |

See `.env.example` for the full list.

## Architecture

```
User ──► CLI/TUI ──► LangGraph StateGraph
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
      refill_speakers  AgentNodes   process_response
            │          (Host, PM,       │
            │          TechLead...)     │
            │             │             │
            │         MCP Tools     summarize
            │        (GitHub...)        │
            └───────────────────────────┘
                    ▼
              Meeting Output
```

**Key components:**

- **LangGraph StateGraph** — Orchestrates the meeting as a state machine with turn-based routing
- **AgentNode** — Each participant runs as an independent node with its own LLM and system prompt
- **ProcessResponseNode** — Extracts mentions, detects agenda completion, manages speaker queue
- **RefillSpeakersNode** — Ensures required speakers participate in each agenda item
- **SummarizationNode** — Compresses conversation history to stay within context limits

## WebSocket Server

For web integrations, TheTable also provides a FastAPI WebSocket server:

```bash
uv sync --extra server
uv run thetable-server
```

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run specific test
uv run pytest tests/core/test_profile.py -v
```

## Tech Stack

[LangGraph](https://github.com/langchain-ai/langgraph) |
[LangChain](https://github.com/langchain-ai/langchain) |
[Textual](https://github.com/Textualize/textual) |
[Typer](https://github.com/tiangolo/typer) |
[Pydantic](https://github.com/pydantic/pydantic) |
[FastAPI](https://github.com/tiangolo/fastapi)
