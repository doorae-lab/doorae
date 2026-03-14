# Doorae

AI-powered team meeting system built on [LangGraph](https://github.com/langchain-ai/langgraph). Autonomous AI agents with distinct roles participate in structured meetings, discuss agendas, and produce actionable outcomes — all from your terminal.

## Overview

Doorae creates realistic team meetings where AI agents collaborate like real team members. Each agent has a defined role, responsibilities, and expertise. A Host facilitates, a PM tracks progress, a TechLead makes architecture decisions — and they all discuss your agenda items with context-aware responses.

```
$ doorae --message "Start the sprint meeting"
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
<img width="1080" height="1794" alt="image" src="https://github.com/user-attachments/assets/75135a4c-1789-4cf5-9202-2f7a9198b132" />

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
git clone https://github.com/doorae-lab/doorae.git
cd doorae
uv sync
```

Optional global install:

```bash
uv tool install .
```

If `doorae` is not available in PowerShell after `uv tool install .`, run `uv tool update-shell` once and restart the terminal.

### 2. Initialize the workspace

```bash
uv run doorae init
```

### 3. Create a project scaffold

```bash
uv run doorae project create demo
```

This creates `.doorae/projects/demo/` with `project.yaml`, `config/agent_profiles.yaml`, `config/agendas.yaml`, and `config/mcp_servers.json`.

### 4. Configure

Edit `.env` with your API key, preferred model, and the project config paths you want to use:

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://openrouter.ai/api/v1  # or https://api.openai.com/v1
AGENT_PROFILES_PATH=.doorae/projects/demo/config/agent_profiles.yaml
AGENDAS_PATH=.doorae/projects/demo/config/agendas.yaml

LLM_MAIN_MODEL=deepseek/deepseek-v3.2
LLM_TASK_MODEL=google/gemini-2.5-flash
```

> [!TIP]
> OpenRouter is recommended for cost efficiency. See `.env.example` for all configuration options including Azure OpenAI, local Ollama, and LangSmith tracing.

### 5. Run

```bash
uv run doorae
```

## Usage

```bash
# Default meeting
uv run doorae

# Initialize a workspace and scaffold a project
uv run doorae init
uv run doorae project create demo

# Custom message
uv run doorae -m "Emergency bug response meeting"

# Classic CLI (no TUI)
uv run doorae --classic

# Custom profiles & config
uv run doorae --profiles config/custom_profiles.yaml --config .env.prod

# With LangSmith tracing
uv run doorae --trace

# Verbose logging
uv run doorae -v
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
| `LLM_TASK_MAX_TOKENS` | Utility task token cap | `256` |
| `MENTION_EXTRACTION_MAX_TOKENS` | Human mention fallback token cap | `64` |
| `MAX_TURNS` | Max meeting turns | `1000` |
| `AGENT_PROFILES_PATH` | Path to profiles YAML | `config/agent_profiles.yaml` |
| `AGENDAS_PATH` | Path to agendas YAML | `config/agendas.yaml` |

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

AI participants must call other participants with `@Name` prefixes such as `@PM` or `@TechLead`. The routing layer treats AI responses without `@Name` as non-routing text and only keeps natural-language fallback for human input during the migration period.

## Server Mode

For web integrations and shared rooms, Doorae can run in client/server mode with a
FastAPI WebSocket backend:

```bash
uv sync --extra server
uv run doorae serve -s 0.0.0.0:8000
```

The legacy entrypoint still works for compatibility, but it is deprecated:

```bash
uv run doorae-server
```

### Multi-participant flow

1. Start the server:

   ```bash
   uv run doorae serve -s 0.0.0.0:8000
   ```

2. Alice creates a room:

   ```bash
   uv run doorae create -u alice -s localhost:8000
   ```

3. Bob joins the same room with the shared room ID:

   ```bash
   uv run doorae join <room_id> -u bob -s localhost:8000
   ```

4. Anyone can inspect the room list:

   ```bash
   uv run doorae rooms -s localhost:8000
   ```

```text
Alice client                 Doorae server                  Bob client
------------                 -------------                  ----------
doorae serve --------------> listen on :8000
doorae create -------------> create room
share <room_id> ------------------------------------------> receive room ID
message stream <----------> /ws/<room_id>?username=alice
doorae join -------------------------------------> /ws/<room_id>?username=bob <----------> message stream
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
