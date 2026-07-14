# Agentic Workflows — Starter Repo

**AI Forum Hackathon · Training Session · 16 Jul 2026**

A hands-on starter kit from [Seen Ventures](https://seenventures.com) for the AI Forum hackathon training session. Clone it, run the demos, and use the patterns this weekend.

By the end of the session you should know:

- What "agentic" actually means (and when **not** to use it)
- How to build a tool-using agent in Python with [PydanticAI](https://ai.pydantic.dev/)
- How multi-agent handovers work when you genuinely need them

> **Framing:** agents are a tool, not the goal. The hackathon prize goes to working software, not the most autonomous architecture. Start simple.

---

## Quick start

**Requirements:** Python 3.11+, an [OpenAI API key](https://platform.openai.com/account/api-keys)

```bash
git clone <this-repo-url>
cd "Agentic System"

# 1. Add your API key
cp .env.example .env
# Edit .env and paste your real key:
#   OPENAI_API_KEY=sk-proj-...

# 2. Run the main demo
chmod +x run_demo.sh
./run_demo.sh
```

You should see the agent search for NZ population data, calculate 30%, and return a validated answer in a green panel. If that works, you're set.

---

## Run the demos

`run_demo.sh` handles venv creation, dependency install, and loading `.env` automatically.

| Command | What it shows |
|---------|---------------|
| `./run_demo.sh` | **Beat 1** — single agent chains `web_search` → `calculator` |
| `./run_demo.sh direct` | Same agent answers without tools (model's choice) |
| `./run_demo.sh trace` | Beat 1 + compact message trace for debugging |
| `./run_demo.sh multi` | **Beat 4** — 4 agents with orchestrator handovers |
| `./run_demo.sh both` | Main demo, then direct |

Run all four back-to-back:

```bash
./run_demo.sh main && ./run_demo.sh direct && ./run_demo.sh trace && ./run_demo.sh multi
```

Custom questions:

```bash
python demo.py "What is the capital of New Zealand?"
python demo_multi.py --trace
```

---

## What's in this repo

```
Agentic System/
├── demo.py           ← Start here. Single research agent (~50 lines of logic)
├── demo_multi.py     ← Advanced: orchestrator + 3 specialist agents
├── run_demo.sh       ← One-command runner (use this on stage)
├── demo-script.txt   ← Presenter script with talking points
├── preso.md          ← Slide deck outline for the session
├── requirements.txt  ← pydantic-ai, rich
└── .env.example      ← Copy to .env and add your API key
```

### `demo.py` — single agent (clone this for the hackathon)

The core loop from the slides, running live:

```
perceive → decide → act → observe → repeat
```

Open the file and follow the numbered **STOPS** in the header:

| Stop | Section | Key idea |
|------|---------|----------|
| 1 | `ResearchResult` | Structured output — validated object, not loose text |
| 2 | `agent = Agent(...)` | Model + instructions + output in one declaration |
| 3 | `web_search` / `calculator` | **Main lesson** — docstring + types = tool schema |
| 4 | `LiveDemoPresenter` | Live loop on screen (DECIDE → ACT → OBSERVE) |
| 5 | `print_answer_panel` | What your app consumes |
| 6 | `print_message_trace` | Observability / debugging |
| 7 | `run()` | How it wires together |

### `demo_multi.py` — multi-agent (optional, for curiosity)

Shows two patterns from the slides:

- **Orchestrator–workers** — lead agent delegates to Researcher and Analyst
- **Evaluator–optimiser** — Writer drafts, Critic reviews, loop until approved

```
User question
  → Orchestrator
      → delegate_research  → Researcher  → web_search
      → delegate_analysis  → Analyst     → calculator
      → delegate_writing   → Writer ↔ Critic (max 2 revisions)
  → FinalReport
```

Multi-agent costs more tokens. Use it only when a real limitation forces you to.

---

## Core concepts (cheat sheet)

**Agentic workflow** — an LLM that decides its own next steps in a loop, using tools, until a goal is met. You don't hardcode the steps; the model orchestrates.

**The loop**

```
perceive  →  decide  →  act  →  observe  →  repeat
```

**Tools** — plain Python functions. In PydanticAI, the docstring becomes the tool description the model reads, and type hints become the JSON schema. Good docstrings matter more than clever code.

**Structured output** — declare a Pydantic model as `output_type`. The agent must return exactly that shape, validated and typed.

**Observability** — `result.all_messages()` gives you the full conversation history. Use it while building; log every step.

**Guardrails** — set max iterations / request limits. Agents can loop forever without them.

---

## Hackathon checklist

Before you start building:

- [ ] Start with a **workflow**, not an agent. Move right on the spectrum only when forced.
- [ ] One model, a few sharp tools, a bounded loop.
- [ ] Write tool descriptions like documentation — the model reads them.
- [ ] Make every step observable while you build.
- [ ] Clone `demo.py` and swap the fake `web_search` for a real API.
- [ ] Add complexity only when a real limitation forces you.

---

## Customising for your hackathon project

**Swap the fake search for a real API:**

```python
@agent.tool_plain
async def web_search(query: str) -> str:
    """Search the web for facts."""
    # Replace fake_db with a real call — Tavily, SerpAPI, Brave, etc.
    ...
```

**Add a new tool** — write a function, add a docstring, decorate with `@agent.tool_plain`:

```python
@agent.tool_plain
def lookup_hackathon_team(team_id: str) -> str:
    """Look up a hackathon team by ID. Returns team name and members."""
    ...
```

**Change the output shape** — edit `ResearchResult` or create your own `BaseModel`.

---

## Troubleshooting

**`OPENAI_API_KEY is not set`**

```bash
cp .env.example .env
# Edit .env — paste your real key from platform.openai.com
```

**`OPENAI_API_KEY in .env is still a placeholder`**

Open `.env` and replace the placeholder with your actual key (~50+ characters, starts with `sk-proj-` or `sk-`).

**Demo runs but no tool calls**

The model chose to answer directly — that's a valid agent decision. Try the default question or run without `--direct`.

**`pip install` errors**

Use Python 3.11 or 3.12. The script creates a `.venv` automatically.

---

## Resources

- [PydanticAI docs](https://ai.pydantic.dev/) — framework used in the demos
- [PydanticAI multi-agent guide](https://ai.pydantic.dev/multi-agent-applications/) — delegation patterns
- [Anthropic — Building effective agents](https://www.anthropic.com/research/building-effective-agents)
- [LangGraph docs](https://langchain-ai.github.io/langgraph/) — alternative orchestration framework
- Slide outline — see [`preso.md`](preso.md) in this repo

---

## Session details

| | |
|---|---|
| **When** | 16 Jul 2026 · 4–5pm NZST · Online |
| **Who** | Seen Ventures, for the AI Forum |
| **Goal** | Working agent pattern you can clone at the hackathon |
| **Model** | `openai:gpt-5-mini` (swap in `demo.py` / `demo_multi.py`) |

Questions during the session? Ask in the chat. After the session, open an issue or reach out to the Seen Ventures team.

Good luck at the hackathon.
