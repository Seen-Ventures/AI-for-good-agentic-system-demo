"""
Multi-Agent Research Demo — Live Demo
Agentic Workflows session · AI Forum Hackathon · Training Sessions 2026

WHAT THIS SHOWS
    Orchestrator–workers + evaluator–optimiser patterns from slide 6.
    Four agents with visible handovers: Orchestrator delegates to Researcher
    and Analyst, then runs a Writer + Critic review loop before returning a
    validated FinalReport.

RUN IT
    ./run_demo.sh multi

WALKTHROUGH GUIDE (open this file while the terminal runs)
    Stop 1  →  output models (FinalReport, Calculation, Review)   typed shapes
    Stop 2  →  researcher / analyst / writer / critic             specialist agents
    Stop 3  →  web_search / calculator                            tools live on sub-agents
    Stop 4  →  orchestrator                                       lead agent — delegates only
    Stop 5  →  MultiAgentPresenter                                handover visualization
    Stop 6  →  delegate_research / delegate_analysis              orchestrator–workers
    Stop 7  →  delegate_writing                                   evaluator–optimiser loop
    Stop 8  →  run()                                              ties it all together

ARCHITECTURE (read top-to-bottom)
    User question
        → Orchestrator
            → delegate_research  → Researcher  → web_search
            → delegate_analysis  → Analyst     → calculator
            → delegate_writing   → Writer ↔ Critic (max 2 revisions)
        → FinalReport
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import AsyncIterable
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import (
    Agent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    RunContext,
    UsageLimits,
)
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from demo import print_message_trace

console = Console()

TOOL_ICONS = {
    "web_search": "🔍",
    "calculator": "🧮",
    "delegate_research": "📚",
    "delegate_analysis": "🧮",
    "delegate_writing": "✍️",
}

# Colour + icon for each agent in the terminal handover view.
AGENT_STYLES: dict[str, tuple[str, str, str]] = {
    "orchestrator": ("ORCHESTRATOR", "magenta", "🎯"),
    "researcher": ("RESEARCHER", "bright_blue", "📚"),
    "analyst": ("ANALYST", "yellow", "🧮"),
    "writer": ("WRITER", "green", "✍️"),
    "critic": ("CRITIC", "red", "🔎"),
}

# Orchestrator tools that trigger a handover (printed differently from plain tool calls).
DELEGATION_TOOLS = frozenset(
    {"delegate_research", "delegate_analysis", "delegate_writing"}
)

# Guardrail: critic can request at most 2 revisions before we accept the draft.
MAX_CRITIC_REVISIONS = 2


# =============================================================================
# STOP 1 — OUTPUT MODELS
# =============================================================================
# SAY: "Each agent returns a typed shape. The orchestrator assembles them into
#       one FinalReport your app consumes — same idea as demo.py, but richer."
#
# Calculation + Review are intermediate shapes returned by sub-agents.
# FinalReport is what the orchestrator must produce at the end.

class Calculation(BaseModel):
    expression: str = Field(description="The arithmetic expression evaluated")
    result: float = Field(description="The numeric result")


class Review(BaseModel):
    approved: bool = Field(description="True if the brief is ready to publish")
    feedback: str = Field(description="Revision notes if not approved")


class WritingResult(BaseModel):
    brief: str
    revisions: int


class FinalReport(BaseModel):
    answer: str = Field(description="The final numeric or factual answer")
    key_facts: list[str] = Field(description="Facts gathered during research")
    calculation: str = Field(
        description="Calculation shown as 'expression = result', e.g. '5200000 * 0.3 = 1560000'"
    )
    brief: str = Field(description="One-paragraph brief written by the writer agent")
    revisions: int = Field(description="How many critic-driven revisions were needed", ge=0)
    confidence: int = Field(description="0-10 confidence", ge=0, le=10)


# =============================================================================
# STOP 2 — SPECIALIST SUB-AGENTS
# =============================================================================
# SAY: "Each agent has one job and its own tools. The orchestrator never does
#       the work itself — it delegates and gets control back."
#
# Pattern: sub_agent.run(..., usage=ctx.usage) inside an orchestrator tool.
# Passing ctx.usage aggregates token counts across all agents into one total.

researcher = Agent(
    "openai:gpt-5-mini",
    name="researcher",
    output_type=list[str],
    instructions=(
        "You are a research specialist. Use web_search to find facts. "
        "Return 2-4 concise fact strings. Use short queries like "
        "'population of new zealand'. Never guess numbers."
    ),
)

analyst = Agent(
    "openai:gpt-5-mini",
    name="analyst",
    output_type=Calculation,
    instructions=(
        "You are an analysis specialist. Use calculator for all arithmetic — "
        "never calculate yourself. Return the expression and numeric result."
    ),
)

writer = Agent(
    "openai:gpt-5-mini",
    name="writer",
    output_type=str,
    instructions=(
        "Write a clear one-paragraph brief. Include the numeric answer, "
        "mention the source year when available, and keep it under 80 words."
    ),
)

critic = Agent(
    "openai:gpt-5-mini",
    name="critic",
    output_type=Review,
    instructions=(
        "Review the brief. Approve only if it: (1) states the numeric answer, "
        "(2) mentions 2026 or the data year, (3) is a single paragraph. "
        "Otherwise reject with specific revision feedback."
    ),
)


# =============================================================================
# STOP 3 — TOOLS (owned by sub-agents, not the orchestrator)
# =============================================================================
# SAY: "Same tool pattern as demo.py — but each tool lives on the agent that
#       actually needs it. Researcher owns search, Analyst owns calculator."

@researcher.tool_plain
def web_search(query: str) -> str:
    """Search the web for facts. Use short queries like 'population of new zealand'."""
    # Same fake DB as demo.py — keeps the multi-agent demo reliable on stage.
    fake_db = {
        "population of new zealand": (
            "New Zealand's population is about 5.2 million (2026). "
            "Use 5200000 for calculations."
        ),
        "capital of new zealand": "The capital of New Zealand is Wellington.",
    }
    q = query.lower().strip()
    if q in fake_db:
        return fake_db[q]

    if "new zealand" in q or " nz " in f" {q} ":
        if "population" in q or "people" in q:
            return fake_db["population of new zealand"]
        if "capital" in q:
            return fake_db["capital of new zealand"]

    return (
        f"No results found for '{query}'. "
        "Try a simpler query like 'population of new zealand'."
    )


@analyst.tool_plain
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression, e.g. '5200000 * 0.3'."""
    try:
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as e:
        return f"Error: {e}"


# =============================================================================
# STOP 4 — ORCHESTRATOR  (lead agent — delegates, never does domain work)
# =============================================================================
# SAY: "The orchestrator has no domain tools — only delegation tools. It decides
#       WHO does the work, not HOW. That's the orchestrator–workers pattern."
#
# Its only tools are delegate_research, delegate_analysis, delegate_writing
# (defined in Stop 6–7 below).

orchestrator = Agent(
    "openai:gpt-5-mini",
    name="orchestrator",
    output_type=FinalReport,
    instructions=(
        "You coordinate a research team. For every question:\n"
        "1. Call delegate_research to gather facts.\n"
        "2. Call delegate_analysis with the facts to compute any numbers needed.\n"
        "3. Call delegate_writing to produce a one-paragraph brief.\n"
        "4. Return a FinalReport combining all results.\n"
        "Never guess numbers — always delegate. Never skip a delegation step."
    ),
)


# =============================================================================
# STOP 5 — HANDOVER PRESENTER
# =============================================================================
# SAY: "Each handover prints on screen so you can see control pass between agents.
#       Indented lines = activity inside the sub-agent that was handed to."
#
# on_handover_start  →  "ORCHESTRATOR → HANDOVER  delegate_research(...)"
# on_sub_tool_call   →  "    ├─ RESEARCHER  web_search(...)"
# on_handover_end    →  "    └─ RETURN  ← facts handed back"

class MultiAgentPresenter:
    """Prints orchestrator handovers and nested sub-agent tool events."""

    def __init__(self) -> None:
        self.step = 0
        self.handover_count = 0
        self.tool_call_count = 0
        self.depth = 0
        self.thinking_active = False
        self._active_handover: str | None = None

    def _clear_thinking(self) -> None:
        if self.thinking_active:
            console.print()
            self.thinking_active = False

    @staticmethod
    def _truncate(text: Any, limit: int = 72) -> str:
        rendered = str(text).replace("\n", " ").strip()
        if len(rendered) <= limit:
            return rendered
        return rendered[: limit - 3] + "..."

    @staticmethod
    def _format_args(args: Any) -> str:
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                return f"({args!r})"
        if isinstance(args, dict):
            parts = [f"{key}={value!r}" for key, value in args.items()]
            return f"({', '.join(parts)})"
        return f"({args!r})"

    def _indent(self) -> str:
        return "    " * self.depth

    def _agent_label(self, agent_key: str) -> str:
        name, color, icon = AGENT_STYLES[agent_key]
        return f"[bold {color}]{icon} {name}[/bold {color}]"

    def on_thinking(self) -> None:
        if not self.thinking_active and self.step == 0:
            console.print("[dim italic]orchestrator thinking...[/dim italic]")
            self.thinking_active = True

    def on_handover_start(self, target_agent: str, tool_name: str, args: Any) -> None:
        self._clear_thinking()
        self.step += 1
        self.handover_count += 1
        self.depth = 1
        self._active_handover = target_agent
        icon = TOOL_ICONS.get(tool_name, "⚙️")
        console.print(
            f"[bold yellow]STEP {self.step}[/bold yellow]  "
            f"{self._agent_label('orchestrator')}  "
            f"[bold cyan]→ HANDOVER[/bold cyan]   "
            f"{icon} [bold]{tool_name}[/bold]"
            f"[dim]{self._format_args(args)}[/dim]"
        )

    def on_handover_end(self, target_agent: str, summary: str) -> None:
        console.print(
            f"{self._indent()}[bold green]└─ RETURN[/bold green]      "
            f"← {self._agent_label(target_agent)} "
            f"[italic]{self._truncate(summary)}[/italic]"
        )
        self.depth = 0
        self._active_handover = None

    def on_sub_tool_call(self, agent_key: str, tool_name: str, args: Any) -> None:
        self.tool_call_count += 1
        icon = TOOL_ICONS.get(tool_name, "⚙️")
        console.print(
            f"{self._indent()}[bold]├─[/bold] {self._agent_label(agent_key)}  "
            f"{icon} [bold]{tool_name}[/bold]"
            f"[dim]{self._format_args(args)}[/dim]"
        )

    def on_sub_tool_result(self, content: Any) -> None:
        console.print(
            f"{self._indent()}[bold]├─[/bold] [bold green]OBSERVE[/bold green]     "
            f"← [italic]{self._truncate(content)}[/italic]"
        )

    def on_draft(self, version: int, content: str) -> None:
        console.print(
            f"{self._indent()}[bold]├─[/bold] {self._agent_label('writer')}  "
            f"draft v{version}  [italic]{self._truncate(content, 60)}[/italic]"
        )

    def on_review(self, approved: bool, feedback: str) -> None:
        verdict = "✓ approved" if approved else "✗ revise"
        style = "green" if approved else "red"
        console.print(
            f"{self._indent()}[bold]├─[/bold] {self._agent_label('critic')}  "
            f"[bold {style}]{verdict}[/bold {style}]  "
            f"[italic]{self._truncate(feedback, 60)}[/italic]"
        )

    def _handle_event(self, agent_key: str, event: Any) -> None:
        if isinstance(event, FunctionToolCallEvent):
            if event.part.tool_name == "final_result":
                self._clear_thinking()
                return
            if agent_key == "orchestrator":
                if event.part.tool_name in DELEGATION_TOOLS:
                    return  # handover lines printed by delegation tools directly
                self.on_sub_tool_call(agent_key, event.part.tool_name, event.part.args)
            else:
                self.on_sub_tool_call(agent_key, event.part.tool_name, event.part.args)
        elif isinstance(event, FunctionToolResultEvent):
            if event.part.tool_name == "final_result":
                return
            if agent_key == "orchestrator" and event.part.tool_name in DELEGATION_TOOLS:
                return  # return line already printed by on_handover_end
            self.on_sub_tool_result(event.part.content)

    def make_handler(self, agent_key: str):
        # Each agent gets its own handler so we can label events by agent name.
        async def handler(
            _ctx: RunContext[None],
            event_stream: AsyncIterable[Any],
        ) -> None:
            if agent_key == "orchestrator":
                self.on_thinking()
            async for event in event_stream:
                self._handle_event(agent_key, event)

        return handler


# Module-level presenter ref so delegation tools (below) can print handovers.
_presenter: MultiAgentPresenter | None = None


def _get_presenter() -> MultiAgentPresenter:
    if _presenter is None:
        raise RuntimeError("Presenter not initialised")
    return _presenter


# =============================================================================
# STOP 6 — DELEGATION TOOLS  (orchestrator–workers pattern)
# =============================================================================
# SAY: "Each tool hands work to a sub-agent and waits for the result. The
#       orchestrator regains control when the sub-agent finishes. Notice
#       usage=ctx.usage — token counts roll up across all agents."
#
# This is PydanticAI's agent-delegation pattern:
#   https://ai.pydantic.dev/multi-agent-applications/#agent-delegation

@orchestrator.tool
async def delegate_research(ctx: RunContext[None], topic: str) -> list[str]:
    """Hand off to the researcher agent to gather facts on a topic."""
    presenter = _get_presenter()
    presenter.on_handover_start("researcher", "delegate_research", {"topic": topic})

    result = await researcher.run(
        f"Research and return 2-4 key facts about: {topic}",
        usage=ctx.usage,
        event_stream_handler=presenter.make_handler("researcher"),
    )

    facts = result.output
    presenter.on_handover_end("researcher", f"{len(facts)} facts gathered")
    return facts


@orchestrator.tool
async def delegate_analysis(
    ctx: RunContext[None],
    task: str,
    facts: list[str],
) -> Calculation:
    """Hand off to the analyst agent to compute numbers from gathered facts."""
    presenter = _get_presenter()
    presenter.on_handover_start(
        "analyst",
        "delegate_analysis",
        {"task": task, "facts": facts},
    )

    facts_text = "\n".join(f"- {fact}" for fact in facts)
    result = await analyst.run(
        f"Task: {task}\n\nFacts:\n{facts_text}\n\n"
        "Use calculator for any arithmetic. Return expression and result.",
        usage=ctx.usage,
        event_stream_handler=presenter.make_handler("analyst"),
    )

    calc = result.output
    presenter.on_handover_end(
        "analyst",
        f"{calc.expression} = {calc.result}",
    )
    return calc


# =============================================================================
# STOP 7 — WRITER + CRITIC LOOP  (evaluator–optimiser pattern)
# =============================================================================
# SAY: "One agent writes, another critiques, loop until approved. Bounded to
#       2 revisions — that's a guardrail from slide 10. Multi-agent is a cost,
#       not a badge of honour — notice the token count in the footer."

@orchestrator.tool
async def delegate_writing(
    ctx: RunContext[None],
    brief_request: str,
    answer: str,
    facts: list[str],
) -> WritingResult:
    """Hand off to writer + critic loop to produce a reviewed one-paragraph brief."""
    presenter = _get_presenter()
    presenter.on_handover_start(
        "writer",
        "delegate_writing",
        {"request": brief_request},
    )

    facts_text = "\n".join(f"- {fact}" for fact in facts)
    base_context = (
        f"Facts:\n{facts_text}\n\n"
        f"Answer: {answer}\n\n"
        f"Request: {brief_request}"
    )

    draft = ""
    revisions = 0
    feedback = ""

    # Up to MAX_CRITIC_REVISIONS + 1 drafts (initial + revisions).
    for attempt in range(MAX_CRITIC_REVISIONS + 1):
        if attempt == 0:
            writer_prompt = f"Write a one-paragraph brief.\n\n{base_context}"
        else:
            writer_prompt = (
                f"Revise the brief based on critic feedback.\n\n"
                f"Feedback: {feedback}\n\n"
                f"Previous draft: {draft}\n\n"
                f"{base_context}"
            )

        writer_result = await writer.run(
            writer_prompt,
            usage=ctx.usage,
            event_stream_handler=presenter.make_handler("writer"),
        )
        draft = writer_result.output
        presenter.on_draft(attempt + 1, draft)

        critic_result = await critic.run(
            f"Review this brief:\n\n{draft}",
            usage=ctx.usage,
            event_stream_handler=presenter.make_handler("critic"),
        )
        review = critic_result.output
        presenter.on_review(review.approved, review.feedback)

        if review.approved:
            break

        revisions += 1
        feedback = review.feedback

    presenter.on_handover_end("writer", f"brief ready ({revisions} revision(s))")
    return WritingResult(brief=draft, revisions=revisions)


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def confidence_bar(score: int, width: int = 10) -> str:
    filled = round(score / 10 * width)
    return "█" * filled + "░" * (width - filled)


def print_question_panel(question: str) -> None:
    console.print()
    console.print(
        Panel(
            Text(f"Q: {question}", style="bold white"),
            title="[bold]MULTI-AGENT RESEARCH SYSTEM[/bold]",
            border_style="bright_magenta",
            padding=(0, 1),
        )
    )
    console.print()


def print_report_panel(report: FinalReport) -> None:
    # SAY: "One validated object with everything — facts, calculation, brief,
    #       revision count, confidence. That's what ships to your app."
    facts_block = "\n".join(f"  • {fact}" for fact in report.key_facts)
    body = Text.assemble(
        ("Answer:      ", "dim"),
        (report.answer, "bold white"),
        "\n",
        ("Calculation: ", "dim"),
        (report.calculation, "cyan"),
        "\n\n",
        ("Key facts:\n", "dim"),
        (facts_block, "bright_blue"),
        "\n\n",
        ("Brief:\n", "dim"),
        (report.brief, "white"),
        "\n\n",
        ("Revisions:   ", "dim"),
        (str(report.revisions), "yellow"),
        "\n",
        ("Confidence:  ", "dim"),
        (confidence_bar(report.confidence), "green"),
        "  ",
        (f"{report.confidence}/10", "bold green"),
    )
    console.print()
    console.print(
        Panel(
            body,
            title="[bold green]FINAL REPORT[/bold green]",
            border_style="green",
            padding=(0, 1),
        )
    )


def print_footer(usage: Any, elapsed_s: float, presenter: MultiAgentPresenter) -> None:
    total_tokens = usage.input_tokens + usage.output_tokens
    console.print(
        f"  [dim]{presenter.handover_count} handover"
        f"{'s' if presenter.handover_count != 1 else ''} · "
        f"{presenter.tool_call_count} sub-agent tool call"
        f"{'s' if presenter.tool_call_count != 1 else ''} · "
        f"{total_tokens:,} tokens · {elapsed_s:.1f}s[/dim]"
    )
    console.print()


# =============================================================================
# STOP 8 — RUN
# =============================================================================

def run(question: str, *, show_trace: bool = False) -> None:
    """Run the multi-agent system with live handover visualization."""
    global _presenter

    print_question_panel(question)

    presenter = MultiAgentPresenter()
    _presenter = presenter
    started = time.perf_counter()

    result = orchestrator.run_sync(
        question,
        event_stream_handler=presenter.make_handler("orchestrator"),
        # Guardrail from slide 10: cap total model requests so the loop can't run away.
        usage_limits=UsageLimits(request_limit=25),
    )
    elapsed = time.perf_counter() - started

    presenter._clear_thinking()
    print_report_panel(result.output)
    print_footer(result.usage, elapsed, presenter)

    if show_trace:
        print_message_trace(result.all_messages())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-agent research demo")
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print compact message trace after the pretty view",
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=(
            "What is 30% of New Zealand's population? "
            "Write a one-paragraph brief with the answer."
        ),
    )
    return parser.parse_args()


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    args = parse_args()
    run(args.question, show_trace=args.trace)
