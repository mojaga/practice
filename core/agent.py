"""Claude agent loop & orchestration.

Primary entry point: ask() — an agentic tool-use loop where Claude decides
which provider tools to call, calls them as many times as needed, and returns
a final operational answer.

Legacy methods generate_query / execute_query / summarize remain for reference
but are no longer called by the UI.

This module depends ONLY on the `Provider` contract (core.interfaces) — it has
no knowledge of any specific platform.
"""
import json

import anthropic

from core import config as cfg
from core.interfaces import Provider
from core.retrieval import retrieve, source_records, knowledge_context

# Number of prior turns passed to Claude as conversation context.
_HISTORY_LIMIT = 4
# Maximum tool-call iterations per ask() to prevent infinite loops.
_MAX_TOOL_ITERATIONS = 10


class ObservabilityAgent:
    """Wraps the Anthropic client and the provider-agnostic orchestration."""

    def __init__(self, api_key, model=cfg.CLAUDE_MODEL):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    # -- Step A -----------------------------------------------------
    def generate_query(self, provider: Provider, question, history=None):
        """Translate a natural-language question into the provider's query language.

        history: list of {question, query, answer} dicts from prior turns.
        Prior (question → query) pairs are replayed as a multi-turn conversation
        so Claude understands follow-ups like "now filter that by production only".
        """
        from utils.formatters import extract_query

        system = (
            f"{provider.spec.query_gen_prompt}\n"
            "Return ONLY the raw query string with NO code fences, markdown backticks, or explanation."
        )

        messages = []
        for turn in (history or [])[-_HISTORY_LIMIT:]:
            messages.append({"role": "user", "content": turn["question"]})
            messages.append({"role": "assistant", "content": turn["query"]})
        messages.append({"role": "user", "content": question})

        res = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=system,
            messages=messages,
        )
        return extract_query(res.content[0].text)

    # -- Step B -----------------------------------------------------
    def execute_query(self, provider: Provider, query, verify_ssl=True):
        """Dispatch the generated query through the provider contract."""
        return provider.execute(query, verify_ssl=verify_ssl)

    # -- L3: agentic tool-use loop ----------------------------------
    def ask(self, provider: Provider, question, history=None, verify_ssl=True, on_progress=None):
        """Tool-use agentic loop — replaces the fixed 3-step flow.

        Claude calls provider tools as many times as needed, then returns a
        final text answer. An optional on_progress callback receives public execution events.
        Returns (answer_text, tool_calls_log, step_groups) where
        tool_calls_log is [{tool, input, result}, ...] for the debug view.
        """
        system = provider.spec.query_gen_prompt + (
            "\n\nFormat your final answer with these Markdown headings: "
            "## Summary, ## Findings, ## Evidence, ## Recommended actions. "
            "Keep each section concise. Reference the tools and returned data supporting findings. "
            "State when evidence is missing or results are partial. Do not invent severity, "
            "metrics, causes, or successful actions. Use tables for comparable records. "
            "For a clarification request, ask the question directly instead of forcing sections."
        )

        def report(stage, **details):
            if on_progress is not None:
                on_progress({"stage": stage, **details})

        report("retrieving")
        retrieval_query = " ".join([t["question"] for t in (history or [])[-1:]] + [question])
        passages = retrieve(retrieval_query, provider.spec.id)
        report("knowledge", sources=source_records(passages))
        system += "\n\n" + knowledge_context(passages)

        messages = []
        for turn in (history or [])[-_HISTORY_LIMIT:]:
            messages.append({"role": "user",      "content": turn["question"]})
            messages.append({"role": "assistant", "content": turn["answer"]})
        messages.append({"role": "user", "content": question})

        tool_calls_log = []
        step_groups = []
        iterations = 0

        while iterations < _MAX_TOOL_ITERATIONS:
            report("reviewing", iteration=iterations + 1)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                tools=provider.tools(),
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                answer = next((b.text for b in response.content if b.type == "text"), "")
                report("complete", tool_count=len(tool_calls_log))
                return answer, tool_calls_log, step_groups

            if response.stop_reason == "max_tokens":
                # Partial response — return whatever text exists, flag it
                partial = next((b.text for b in response.content if b.type == "text"), "")
                report("partial", reason="Response reached the output limit.")
                return (partial or "Response truncated: max token limit reached."), tool_calls_log, step_groups

            # stop_reason == "tool_use": dispatch each tool block, feed results back
            iterations += 1
            messages.append({"role": "assistant", "content": response.content})

            # Capture Claude's planning text before tool calls (shown in UI steps)
            step_text = next((b.text for b in response.content if b.type == "text"), "")
            step_tool_names = []

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    report("tool_started", tool=block.name)
                    result = provider.dispatch_tool(block.name, block.input, verify_ssl)
                    report("tool_finished", tool=block.name, result=result)
                    tool_calls_log.append({
                        "tool":   block.name,
                        "input":  dict(block.input),
                        "result": result,
                    })
                    step_tool_names.append(block.name)
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     json.dumps(result)[:8000],
                    })

            step_groups.append({
                "iteration":  iterations,
                "count":      len(step_tool_names),
                "tools":      step_tool_names,
                "text":       f"Executed: {', '.join(step_tool_names)}",
            })
            messages.append({"role": "user", "content": tool_results})

        report("partial", reason="Maximum investigation steps reached.")
        return "Could not complete: exceeded maximum tool call iterations.", tool_calls_log, step_groups

    # -- Step C -----------------------------------------------------
    def summarize(self, provider: Provider, question, query, telemetry_data, history=None):
        """Summarize raw telemetry into an operational answer.

        history: list of {question, query, answer} dicts from prior turns.
        Prior (question → answer) pairs are included so Claude can reference
        earlier findings when answering follow-up questions.
        """
        lang = provider.spec.query_lang

        def _user_prompt(q, qry, data_json):
            return (
                f"User asked: \"{q}\"\n"
                f"{lang} query executed: \"{qry}\"\n"
                f"Telemetry from {provider.spec.name}:\n{data_json}\n\n"
                "Provide a concise, helpful, and formatted operational summary "
                "explaining the findings and recommended actions."
            )

        messages = []
        for turn in (history or [])[-_HISTORY_LIMIT:]:
            messages.append({"role": "user", "content": _user_prompt(
                turn["question"], turn["query"],
                json.dumps({}, indent=2),   # omit old telemetry — answer already captures the facts
            )})
            messages.append({"role": "assistant", "content": turn["answer"]})

        messages.append({"role": "user", "content": _user_prompt(
            question, query,
            json.dumps(telemetry_data, indent=2)[:8000],
        )})

        res = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=knowledge_context(retrieve(question, provider.spec.id)),
            messages=messages,
        )
        return res.content[0].text
