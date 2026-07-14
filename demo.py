"""
Research Agent — Live Demo
Agentic Workflows session · AI Forum Hackathon · Training Sessions 2026

WHAT THIS SHOWS
    The core agent loop (perceive → decide → act → observe → repeat) in ~50
    lines. PydanticAI runs the loop for us: no manual message list, no hand-written
    tool schemas, no stop-reason checking. We declare tools + an output shape,
    the framework orchestrates.

RUN IT
    ./run_demo.sh              # Beat 1 — main demo
    ./run_demo.sh direct       # optional — model answers without tools
    ./run_demo.sh trace        # Beat 3 — compact message trace

WALKTHROUGH GUIDE (open this file while the terminal runs)
    Stop 1  →  ResearchResult          structured output shape
    Stop 2  →  agent = Agent(...)       one declaration = model + instructions + output
    Stop 3  →  web_search / calculator  tools (docstring + types = schema)
    Stop 4  →  LiveDemoPresenter        live loop on screen (DECIDE → ACT → OBSERVE)
    Stop 5  →  print_answer_panel       what your app actually consumes
    Stop 6  →  print_message_trace      observability / debugging
    Stop 7  →  run()                    ties it all together
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
)
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# Icons shown next to each tool name in the live terminal view.
TOOL_ICONS = {
    "web_search": "🔍",
    "calculator": "🧮",
}


# =============================================================================
# STOP 1 — STRUCTURED OUTPUT
# =============================================================================
# SAY: "The answer isn't loose text — it's a validated Pydantic object your app
#       can consume directly. Field descriptions guide the model too."
#
# PydanticAI calls `final_result` under the hood to force the model to return
# exactly this shape. If validation fails, the agent retries automatically.

class ResearchResult(BaseModel):
    answer: str = Field(description="The final answer to the question")
    sources_used: list[str] = Field(description="Which tools were called")
    confidence: int = Field(description="0-10 confidence", ge=0, le=10)


# =============================================================================
# STOP 2 — THE AGENT
# =============================================================================
# SAY: "Three things in one declaration: which model, what it's told to do, and
#       what shape the answer must take. PydanticAI owns the loop from here."
#
# That's it for the agent definition — no manual message list, no tool schema
# boilerplate, no while-loop checking stop reasons.

agent = Agent(
    "openai:gpt-5-mini",
    output_type=ResearchResult,
    instructions=(
        "You are a research assistant. Use your tools to find facts before "
        "answering. Never guess a number you could look up. "
        "Use short, simple web_search queries (e.g. 'population of new zealand'). "
        "For any arithmetic, call calculator — do not calculate yourself. "
        "Always give a final numeric answer; do not ask clarifying questions. "
        "For definitions or conceptual questions, answer directly without tools."
    ),
)


# =============================================================================
# STOP 3 — TOOLS  ★ main teaching moment
# =============================================================================
# SAY: "Normal Python functions. The docstring becomes the tool description the
#       model reads. Type hints become the JSON schema. That's the whole
#       interface — vague docstrings cause more failures than bad code."
#
# @agent.tool_plain  →  registers the function as a tool this agent can call.
# The model decides WHEN to call; your function decides WHAT happens.

@agent.tool_plain
def web_search(query: str) -> str:
    """Search the web for facts. Use short queries like 'population of new zealand'."""
    # Fake DB keeps the demo reliable on stage — no live internet needed.
    # Swap this dict for a real API call in production.
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

    # Fuzzy match: models often phrase queries differently — this catches them.
    if "new zealand" in q or " nz " in f" {q} ":
        if "population" in q or "people" in q:
            return fake_db["population of new zealand"]
        if "capital" in q:
            return fake_db["capital of new zealand"]

    return (
        f"No results found for '{query}'. "
        "Try a simpler query like 'population of new zealand'."
    )


@agent.tool_plain
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression, e.g. '5200000 * 0.3'."""
    try:
        # Locked-down eval — no access to builtins, safe for a demo.
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as e:
        # Return errors as strings so the model can recover and retry.
        return f"Error: {e}"


# =============================================================================
# STOP 4 — LIVE PRESENTER  (maps to the agent loop on screen)
# =============================================================================
# SAY: "Watch the loop happen live — DECIDE → ACT → OBSERVE, straight from
#       the slides. PydanticAI streams events; we print them as they arrive."
#
# FunctionToolCallEvent  = model decided to call a tool       → DECIDE → ACT
# FunctionToolResultEvent = tool returned a result            → OBSERVE

class LiveDemoPresenter:
    """Prints the agent loop live as PydanticAI streams tool events."""

    def __init__(self) -> None:
        self.step = 0
        self.thinking_active = False

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

    def on_tool_call(self, tool_name: str, args: Any) -> None:
        self._clear_thinking()
        self.step += 1
        icon = TOOL_ICONS.get(tool_name, "⚙️")
        console.print(
            f"[bold yellow]STEP {self.step}[/bold yellow]  "
            f"[bold cyan]DECIDE → ACT[/bold cyan]   "
            f"{icon} [bold]{tool_name}[/bold]"
            f"[dim]{self._format_args(args)}[/dim]"
        )

    def on_tool_result(self, content: Any) -> None:
        console.print(
            "        [bold green]OBSERVE[/bold green]        "
            f"← [italic]{self._truncate(content)}[/italic]"
        )

    async def handle_events(self, event_stream: AsyncIterable[Any]) -> None:
        # Show "thinking..." until the first tool call arrives.
        if not self.thinking_active and self.step == 0:
            console.print("[dim italic]thinking...[/dim italic]")
            self.thinking_active = True

        async for event in event_stream:
            if isinstance(event, FunctionToolCallEvent):
                # final_result is PydanticAI packing the structured output — skip it.
                if event.part.tool_name == "final_result":
                    self._clear_thinking()
                else:
                    self.on_tool_call(event.part.tool_name, event.part.args)
            elif isinstance(event, FunctionToolResultEvent):
                if event.part.tool_name != "final_result":
                    self.on_tool_result(event.part.content)


# =============================================================================
# STOP 5 — DISPLAY HELPERS  (what the audience sees after the loop)
# =============================================================================

def confidence_bar(score: int, width: int = 10) -> str:
    filled = round(score / 10 * width)
    return "█" * filled + "░" * (width - filled)


def clean_sources(sources: list[str]) -> str:
    names: list[str] = []
    for source in sources:
        name = source.split(":")[0].replace("functions.", "")
        if name not in names:
            names.append(name)
    return ", ".join(names) if names else "none (direct answer)"


def print_question_panel(question: str) -> None:
    console.print()
    console.print(
        Panel(
            Text(f"Q: {question}", style="bold white"),
            title="[bold]RESEARCH AGENT[/bold]",
            border_style="bright_blue",
            padding=(0, 1),
        )
    )
    console.print()


def print_answer_panel(result: ResearchResult) -> None:
    # SAY: "Green panel = validated ResearchResult. answer, sources_used,
    #       confidence — ready for your app, not raw model text."
    body = Text.assemble(
        (result.answer, "bold white"),
        "\n\n",
        ("Sources:    ", "dim"),
        (clean_sources(result.sources_used), "cyan"),
        "\n",
        ("Confidence: ", "dim"),
        (confidence_bar(result.confidence), "green"),
        "  ",
        (f"{result.confidence}/10", "bold green"),
    )
    console.print()
    console.print(
        Panel(
            body,
            title="[bold green]ANSWER[/bold green]",
            border_style="green",
            padding=(0, 1),
        )
    )


def print_footer(usage: Any, elapsed_s: float, step_count: int) -> None:
    total_tokens = usage.input_tokens + usage.output_tokens
    console.print(
        f"  [dim]{step_count} tool call{'s' if step_count != 1 else ''} · "
        f"{total_tokens:,} tokens · {elapsed_s:.1f}s[/dim]"
    )
    console.print()


def print_no_tools_note() -> None:
    # Shown when --direct is used, or the model answers without calling tools.
    console.print(
        "[dim italic]No tools used — the model answered directly "
        "(still a valid agent decision).[/dim italic]"
    )


# =============================================================================
# STOP 6 — MESSAGE TRACE  (observability / Beat 3)
# =============================================================================
# SAY: "If you need to debug, PydanticAI gives you the full message history.
#       We format it compactly here — every request, tool call, and return."
#
# Run with:  ./run_demo.sh trace

def _format_trace_args(args: Any) -> str:
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
        except json.JSONDecodeError:
            return args
        else:
            args = parsed
    if isinstance(args, dict):
        return json.dumps(args, ensure_ascii=False)
    return str(args)


def print_message_trace(messages: list[Any]) -> None:
    """Print a compact, readable view of the agent message history."""
    console.print("[bold dim]--- Message trace (observability) ---[/bold dim]")

    turn = 0
    for msg in messages:
        if isinstance(msg, ModelRequest):
            turn += 1
            console.print(f"\n[bold cyan]TURN {turn} → request[/bold cyan]")
            for part in msg.parts:
                if isinstance(part, UserPromptPart):
                    content = (
                        part.content
                        if isinstance(part.content, str)
                        else str(part.content)
                    )
                    console.print(
                        f"  [bold]user[/bold]         "
                        f"{LiveDemoPresenter._truncate(content, 88)}"
                    )
                elif isinstance(part, ToolReturnPart):
                    if part.tool_name == "final_result":
                        continue
                    console.print(
                        f"  [bold green]tool return[/bold green]  "
                        f"[cyan]{part.tool_name}[/cyan] ← "
                        f"[italic]{LiveDemoPresenter._truncate(part.content, 72)}[/italic]"
                    )
        elif isinstance(msg, ModelResponse):
            usage = msg.usage
            model = msg.model_name or "model"
            console.print(
                f"\n[bold yellow]TURN {turn} ← response[/bold yellow]  "
                f"[dim]{model} · {usage.input_tokens:,} in / "
                f"{usage.output_tokens:,} out[/dim]"
            )
            for part in msg.parts:
                if isinstance(part, ThinkingPart):
                    if part.content.strip():
                        label = LiveDemoPresenter._truncate(part.content, 72)
                    else:
                        label = "reasoning (provider-hidden)"
                    console.print(f"  [dim]thinking[/dim]     {label}")
                elif isinstance(part, ToolCallPart):
                    args_text = _format_trace_args(part.args)
                    if part.tool_name == "final_result":
                        console.print(
                            f"  [bold green]final output[/bold green]  "
                            f"{LiveDemoPresenter._truncate(args_text, 88)}"
                        )
                    else:
                        console.print(
                            f"  [bold]tool call[/bold]    "
                            f"[cyan]{part.tool_name}[/cyan]"
                            f"({LiveDemoPresenter._truncate(args_text, 56)})"
                        )

    console.print()


# =============================================================================
# STOP 7 — RUN  (entry point — everything wires together here)
# =============================================================================

def run(question: str, *, show_trace: bool = False, direct: bool = False) -> None:
    """Run the agent with a live, presentation-friendly terminal view."""
    print_question_panel(question)

    presenter = LiveDemoPresenter()
    started = time.perf_counter()

    # event_stream_handler hooks into PydanticAI's event stream so we can
    # print each tool call and result as it happens (the live loop on screen).
    async def event_stream_handler(
        _ctx: RunContext[None],
        event_stream: AsyncIterable[Any],
    ) -> None:
        await presenter.handle_events(event_stream)

    run_kwargs: dict[str, Any] = {
        "event_stream_handler": event_stream_handler,
    }

    # --direct mode: force the model to answer without tools (optional Beat 2).
    # SAY: "Same agent, different decision — no tool calls. That's still agentic."
    if direct:
        run_kwargs["instructions"] = (
            "Answer the question directly in one concise line."
        )
        run_kwargs["model_settings"] = {"tool_choice": "none"}

    # agent.run_sync blocks until the loop finishes and output is validated.
    result = agent.run_sync(question, **run_kwargs)
    elapsed = time.perf_counter() - started

    if presenter.step == 0:
        presenter._clear_thinking()
        print_no_tools_note()

    print_answer_panel(result.output)
    print_footer(result.usage, elapsed, presenter.step)

    if show_trace:
        # result.all_messages() = full conversation history for debugging.
        print_message_trace(result.all_messages())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Research Agent live demo")
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print compact message trace after the pretty view",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Answer without tools (optional second demo beat)",
    )
    parser.add_argument(
        "question",
        nargs="?",
        default="What is 30% of New Zealand's population?",
    )
    return parser.parse_args()


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    args = parse_args()
    run(args.question, show_trace=args.trace, direct=args.direct)
