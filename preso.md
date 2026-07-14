# Agentic Workflows — Slide Deck Outline

**AI Forum Hackathon · Training Sessions 2026**
**16 Jul · Online · 4–5pm (60 min) · Seen Ventures, for the AI Forum**

> Session goal: by 5pm, attendees know what "agentic" means, when to use it (and when not to), and have a working Python agent pattern they can clone at the hackathon.

---

## Slide 1 — Title

- **Agentic Workflows**
- Core concepts + toolsets to build at the hackathon
- Seen Ventures, for the AI Forum · 16 Jul

---

## Slide 2 — Why this session (2 min)

- By 5pm you'll know what "agentic" actually means, when to reach for it (and when not to), and you'll have a working agent pattern you can clone this weekend.
- **Framing:** agents are a tool, not the goal. The hackathon prize goes to working software, not the most autonomous architecture.

---

## Slide 3 — What is an agentic workflow? (5 min)

- **Plain definition:** an LLM that decides its own next steps in a loop, using tools, until a goal is met — versus a fixed pipeline where you hardcode the steps.
- **The core loop:** perceive → decide → act → observe → repeat.
- **Contrast:** *workflow* (you orchestrate, predictable) vs *agent* (model orchestrates, flexible).
- Most "agents" people ship are actually workflows — and that's completely fine.

---

## Slide 4 — The spectrum (4 min)

- Single LLM call → chained calls (workflow) → router → tool-using agent → multi-agent.
- **Key message: start at the left.** Move right only when a real limitation forces you to.
- Single-agent-first. Multi-agent is a cost, not a badge of honour.

---

## Slide 5 — Core building blocks (6 min)

- **Model** — the reasoning engine.
- **Tools** — functions the model can call (search, code exec, API calls, DB queries).
- **Memory / context** — what the model carries between steps.
- **Loop / control flow** — what decides "keep going" vs "done".
- **Orchestration** — how you wire it together.

---

## Slide 6 — Common patterns (8 min)

- **Prompt chaining** — decompose into fixed steps.
- **Routing** — classify input, send to the right handler.
- **Tool use / ReAct** — reason, call a tool, observe, repeat. (This is the demo.)
- **Orchestrator–workers** — a lead agent delegates subtasks. Heavier; only for genuinely parallel work.
- **Evaluator–optimiser** — one agent generates, another critiques and loops.

---

## Slide 7 — Toolsets you can use today (6 min)

- **Write code:** PydanticAI, LangGraph, OpenAI Agents SDK, Anthropic tool-use API, CrewAI, Mastra (TS).
- **No/low-code:** Flowise, Langflow, Dify, n8n (all free to self-host).
- **Honest take for a hackathon:** a single model + tool-calling + a simple loop beats a heavy framework. Frameworks earn their keep at scale, not at speed.

---

## Slide 8 — Code vs No-code: pick your lane (4 min)

| | Write code (PydanticAI, SDKs) | No/low-code (Flowise, Langflow, Dify) |
|---|---|---|
| **Best for** | Custom logic, full control | Speed, non-coders, standard integrations |
| **Strength** | Flexible, portable, testable | Visual, fast, handles OAuth/connectors |
| **Weakness** | You write the plumbing | Hits walls on dynamic logic; lock-in |
| **Hackathon fit** | When your idea is unusual | When you need a working demo by tomorrow |

- **Bottom line:** prototype fast, eject to code when it hurts. Most visual tools export to code, so it's not either/or.
- **Speaker note:** if you reach for a visual builder this weekend, check it isn't on a deprecation timeline — OpenAI's Agent Builder shuts down Nov 2026. Flowise / Langflow / Dify / n8n are safer bets.

---

## Slide 9 — Designing tools well (5 min)

- Clear names + descriptions — **the model reads these like documentation.**
- One job per tool; return structured, parseable output.
- Handle errors so the model can recover, not crash.
- Fewer, well-described tools > many overlapping ones.
- **The lesson that matters most:** vague tool descriptions cause more failures than bad code.

---

## Slide 10 — Failure modes & guardrails (4 min)

- Loops that never terminate → set **max iterations**.
- Hallucinated tool calls → validate inputs.
- Cost / latency blowout → cap tokens, cache, log every step.
- Always make the agent's reasoning **observable** while you build.

---

## Slide 11 — LIVE DEMO (8–10 min)

**"Build a research agent" — Python, PydanticAI**

- The same core loop from Slide 3, in ~50 lines.
- Watch for three things on screen:
  1. **The tools** — a docstring + type hints *become* the schema the model reads.
  2. **The structured output** — the answer comes back as a validated object, not loose text.
  3. **The trace** — every step of the loop printed: decide → search → observe → calculate → answer.
- **Optional advanced beat:** `./run_demo.sh multi` — four agents with orchestrator handovers and a writer/critic review loop (slide 6 patterns).
- (Demo notes + full code in the companion file.)

---

## Slide 12 — Recap + hackathon checklist (3 min)

- ☐ Start with a workflow, not an agent.
- ☐ One model, a few sharp tools, a bounded loop.
- ☐ Write tool descriptions like documentation.
- ☐ Make every step observable.
- ☐ Add complexity only when forced.

---

## Slide 13 — Resources & Q&A

- Anthropic — "Building effective agents"
- PydanticAI docs · LangGraph docs · Anthropic tool-use guide
- Your starter repo link (the demo code)
- **Q&A**

---

### Timing summary (~60 min)

| Segment | Slides | Min |
|---|---|---|
| Intro + concepts | 2–5 | 17 |
| Patterns + tooling | 6–8 | 18 |
| Tool design + failure modes | 9–10 | 9 |
| Live demo | 11 | 10 |
| Recap + Q&A | 12–13 | 6 |