"""Main Streamlit entrypoint — Avior-inspired ObservIQ UI.

Three-panel layout:
  Left  — dark navigation sidebar (brand + agent nav + settings)
  Center— breadcrumb, tool-execution step checklist, chat messages
  Right — Artifacts panel: structured cards built from tool-call results
"""
import sys
import asyncio
import warnings
import csv
import io
import json
from html import escape

import streamlit as st
import anthropic

# -------------------------------------------------------------------
# Windows event-loop fix
# -------------------------------------------------------------------
if sys.platform.startswith("win"):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # pyright: ignore[reportDeprecated]
    except Exception:
        pass

import providers  # noqa: F401 — registers all providers
from core import config as cfg
from core import registry
from core.agent import ObservabilityAgent

# -------------------------------------------------------------------
# Page config
# -------------------------------------------------------------------
st.set_page_config(
    page_title="ObservIQ — Observability AI",
    page_icon="🔵",
    layout="wide",
)

# -------------------------------------------------------------------
# CSS — Avior-inspired design system
# -------------------------------------------------------------------
st.markdown("""
<style>
/* ── Global ─────────────────────────────────────────────────────── */
.block-container { padding-top: 1.4rem !important; padding-bottom: 0.5rem !important; }
#MainMenu         { visibility: hidden; }
footer            { visibility: hidden; }
.stDeployButton   { display: none !important; }

/* ── Sidebar — dark background ───────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #111827 !important;
    border-right: 1px solid #1f2937;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] span {
    color: rgba(255,255,255,0.75) !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
}
section[data-testid="stSidebar"] .stAlert {
    background: rgba(255,255,255,0.05) !important;
}

/* ── Sidebar brand ───────────────────────────────────────────────── */
.observiq-brand {
    font-size: 17px;
    font-weight: 700;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 6px 0 14px 0;
    border-bottom: 1px solid rgba(255,255,255,0.12);
    margin-bottom: 14px;
    letter-spacing: -0.2px;
}
.observiq-brand .dot {
    width: 10px; height: 10px;
    background: #3b82f6;
    border-radius: 50%;
    display: inline-block;
}

/* ── Sidebar nav label ───────────────────────────────────────────── */
.nav-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: rgba(255,255,255,0.35) !important;
    font-weight: 600;
    padding: 10px 0 4px 0;
}

/* ── Breadcrumb ──────────────────────────────────────────────────── */
.observiq-breadcrumb {
    font-size: 13px;
    color: #6b7280;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 5px;
}
.observiq-breadcrumb .sep   { color: #d1d5db; }
.observiq-breadcrumb .curr  { color: #111827; font-weight: 500; }

/* ── Session query description ───────────────────────────────────── */
.session-query {
    font-size: 13.5px;
    color: #374151;
    line-height: 1.65;
    margin-bottom: 14px;
    padding-bottom: 14px;
    border-bottom: 1px solid #e5e7eb;
}

/* ── Tool execution steps ────────────────────────────────────────── */
.step-wrap        { margin-bottom: 16px; }
.step-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid #f3f4f6;
}
.step-check {
    color: #e87722;
    font-size: 13px;
    font-weight: 700;
    min-width: 14px;
    margin-top: 2px;
}
.step-badge {
    background: #1f2937;
    color: #f9fafb;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    white-space: nowrap;
    margin-top: 1px;
}
.step-badge.green { background: #065f46; }
.step-text {
    color: #374151;
    font-size: 13px;
    line-height: 1.5;
}

/* ── Artifacts panel ─────────────────────────────────────────────── */
.art-header   { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; font-weight: 600; }
.art-subtitle { font-size: 13px; color: #6b7280; margin-top: 2px; margin-bottom: 14px; }

.art-card {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 12px;
    background: #ffffff;
}
.art-card-title { font-size: 13px; font-weight: 600; color: #111827; margin-bottom: 10px; }
.art-grid       { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.art-fl         { font-size: 10px; text-transform: uppercase; letter-spacing: 0.4px; color: #9ca3af; margin-bottom: 2px; }
.art-fv         { font-size: 13px; font-weight: 500; color: #1f2937; }
.art-fv.warn    { color: #d97706; }
.art-fv.crit    { color: #dc2626; }
.art-fv.ok      { color: #059669; }

.art-empty {
    color: #9ca3af; font-size: 13px;
    padding: 28px 0; text-align: center;
    border: 1px dashed #e5e7eb; border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# Refined application theme. Keep widget behavior native to Streamlit.
st.markdown("""
<style>
:root { --ink: #17243b; --muted: #64748b; --line: #e2e8f0; --accent: #2563eb; }
.stApp { background: #f5f7fb; color: var(--ink); }
.block-container { max-width: 1480px; padding: 2.2rem 2.5rem 3rem !important; }
h1, h2, h3 { color: var(--ink); letter-spacing: -0.035em; }
h1 { font-size: 2.4rem !important; font-weight: 750 !important; }
section[data-testid="stSidebar"] { background: #101c30 !important; }
section[data-testid="stSidebar"] .block-container { padding: 1.5rem !important; }
section[data-testid="stSidebar"] button { border-radius: 9px; text-align: left; }
section[data-testid="stSidebar"] button[kind="secondary"] { background: transparent; border-color: #30405a; color: #e2e8f0; }
section[data-testid="stSidebar"] button[kind="secondary"]:hover { background: #22334d; border-color: #64748b; }
section[data-testid="stSidebar"] button p { color: #e2e8f0 !important; }
button[kind="primary"] { background: #2563eb; border-color: #2563eb; border-radius: 9px; }
button[kind="primary"]:hover { background: #1d4ed8; border-color: #1d4ed8; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 14px !important; }
[data-testid="stChatMessage"] { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 1.15rem; margin-bottom: 1rem; }
[data-testid="stChatInput"] { border-radius: 14px; border-color: #cbd5e1; }
[data-testid="stBottom"] > div { background: #f5f7fb; }
.observiq-brand { font-size: 22px; letter-spacing: -0.7px; padding-bottom: 20px; }
.observiq-brand .dot { background: #60a5fa; box-shadow: 0 0 0 5px #60a5fa18; }
.observiq-breadcrumb { font-size: 12px; margin-bottom: 20px; }
.hero-eyebrow { color: #2563eb; font-size: 11px; font-weight: 750; letter-spacing: 1.8px; margin-bottom: 8px; }
.hero-copy { max-width: 680px; color: #64748b; font-size: 16px; line-height: 1.7; margin-bottom: 24px; }
.workspace-note { color: #64748b; font-size: 12px; padding: 12px 0 20px; }
.agent-icon { font-size: 28px; margin: 6px 0 14px; }
.agent-description { color: #64748b; font-size: 14px; min-height: 68px; line-height: 1.65; }
.session-query { background: #eaf1ff; border: 1px solid #d6e4ff; border-radius: 12px; padding: 14px 16px; color: #274365; overflow-wrap: anywhere; }
.step-wrap { background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 6px 14px; }
.step-row:last-child { border-bottom: 0; }
.step-check { color: #2563eb; }
.step-badge { background: #eaf1ff; color: #2457a6; font-size: 9px; }
.step-badge.green { background: #dcfce7; color: #166534; }
.art-header { color: #475569; letter-spacing: 1.4px; margin-top: 4px; }
.art-subtitle { overflow-wrap: anywhere; font-size: 12px; line-height: 1.6; }
.art-card { box-shadow: 0 3px 14px #17243b05; border-radius: 13px; padding: 18px; }
.art-grid { gap: 16px 12px; }
.art-fv { overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
.art-fl { overflow-wrap: anywhere; }
.art-empty { background: #fff; padding: 32px 18px; line-height: 1.8; }
@media (max-width: 900px) {
 .block-container { padding: 1.2rem 1rem 2rem !important; }
 h1 { font-size: 1.9rem !important; }
 .art-grid { grid-template-columns: 1fr; }
}
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------------
# Session state initialisation
# -------------------------------------------------------------------
_DEFAULTS = {
    "knowledge_sources": {},
    "active_agent":    None,
    "histories":       {},   # {agent_id: [{role, content}]}
    "contexts":        {},   # {agent_id: [{question, answer}]}
    "pending_input":   None,
    "step_groups":     {},   # {agent_id: [{iteration, count, tools, text}]}
    "artifacts":       {},   # {agent_id: [{title, fields}]}
    "session_titles":  {},   # {agent_id: str}
    "last_query":      {},   # {agent_id: str}
    "ssl_verify":      {},   # {agent_id: bool}
    "tool_calls_log":  {},   # {agent_id: [{tool, input, result}]}  — survives rerun
    "last_error":      {},   # {agent_id: str | None}               — survives rerun
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# -------------------------------------------------------------------
# Left navigation sidebar
# -------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div class="observiq-brand"><span class="dot"></span> ObservIQ</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="nav-label">Navigation</div>', unsafe_allow_html=True)
        if st.button(
            "🏠  Home",
            key="nav_home",
            use_container_width=True,
            type="primary" if st.session_state.active_agent is None else "secondary",
        ):
            st.session_state.active_agent = None
            st.rerun()

        agents = registry.all_providers()
        if agents:
            st.markdown('<div class="nav-label">Agents</div>', unsafe_allow_html=True)
            for prov in agents:
                spec = prov.spec
                is_active = st.session_state.active_agent == spec.id
                if st.button(
                    f"{spec.icon}  {spec.name}",
                    key=f"nav_{spec.id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.active_agent = spec.id
                    st.rerun()

        st.divider()

        # Context for the active agent
        active = registry.get(st.session_state.active_agent)
        if active:
            spec = active.spec
            missing = active.missing_credentials()
            if missing:
                st.warning("⚠️ Missing: " + ", ".join(missing))
            else:
                st.success("Credentials configured")

            if spec.ssl_toggle:
                st.session_state["ssl_verify"][spec.id] = st.checkbox(
                    "Verify SSL",
                    value=st.session_state["ssl_verify"].get(spec.id, spec.ssl_default),
                    key=f"ssl_{spec.id}",
                )
            st.info(spec.connection_note)

            if st.button("🗑️ Clear conversation", use_container_width=True):
                st.session_state.knowledge_sources[spec.id] = []
                st.session_state.histories[spec.id]     = []
                st.session_state.contexts[spec.id]      = []
                st.session_state.step_groups[spec.id]   = []
                st.session_state.artifacts[spec.id]     = []
                st.session_state.tool_calls_log[spec.id] = []
                st.session_state.last_error.pop(spec.id, None)
                st.session_state.session_titles.pop(spec.id, None)
                st.session_state.last_query.pop(spec.id, None)
                st.rerun()


# -------------------------------------------------------------------
# Home — agent picker cards
# -------------------------------------------------------------------
def render_home():
    st.markdown("""
    <div class="observiq-breadcrumb">
        🏠 <span class="sep">›</span> <span class="curr">Home</span>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="hero-eyebrow">YOUR OPERATIONS WORKSPACE</div>', unsafe_allow_html=True)
    st.title("Clarity across your infrastructure.")
    st.markdown('<div class="hero-copy">Investigate issues, explore your monitoring data, and turn questions into actionable answers. Choose a platform to begin.</div>', unsafe_allow_html=True)
    available = registry.all_providers()
    ready_count = sum(cfg.has_anthropic() and not p.missing_credentials() for p in available)
    st.caption(f"{len(available)} platforms | {ready_count} ready to use | Powered by Claude")
    st.write("")

    agents = registry.all_providers()
    if not agents:
        st.info("No monitoring platforms are available yet.")
        return
    cols = st.columns(min(len(agents), 3))
    for index, prov in enumerate(agents):
        col = cols[index % len(cols)]
        spec = prov.spec
        with col:
            with st.container(border=True):
                st.markdown(f'<div class="agent-icon">{escape(spec.icon)}</div>', unsafe_allow_html=True)
                st.subheader(spec.name)
                st.markdown(f'<div class="agent-description">{escape(spec.tagline)}</div>', unsafe_allow_html=True)

                missing = prov.missing_credentials()
                ready = cfg.has_anthropic() and not missing
                if not cfg.has_anthropic():
                    st.warning("⚠️ ANTHROPIC_API_KEY not set in .env")
                elif missing:
                    st.warning("⚠️ Needs: " + ", ".join(missing))
                else:
                    st.success("✅ Ready")

                if st.button(
                    "Open workspace",
                    key=f"use_{spec.id}",
                    use_container_width=True,
                    type="primary",
                    disabled=not ready,
                ):
                    st.session_state.active_agent = spec.id
                    st.rerun()


# -------------------------------------------------------------------
# Artifact extraction — build cards from raw tool-call results
# -------------------------------------------------------------------
def _status_class(val: str) -> str:
    v = val.lower().strip()
    if v in ("warn", "warning", "degraded"):
        return "warn"
    if v in ("crit", "critical", "error", "down", "fail", "failed", "false"):
        return "crit"
    if v in ("ok", "up", "normal", "ready", "true", "active"):
        return "ok"
    return ""


def _result_tables(result, path="Result", depth=0):
    """Find record arrays in common API envelopes without guessing their meaning."""
    if depth > 4:
        return []
    if isinstance(result, list):
        if result and all(isinstance(row, dict) for row in result):
            return [(path, result)]
        return []
    tables = []
    if isinstance(result, dict):
        for key, value in result.items():
            if isinstance(value, (dict, list)):
                tables.extend(_result_tables(value, f"{path} / {key}", depth + 1))
    return tables


def _display_rows(rows):
    return [
        {str(k): json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
         for k, v in row.items()}
        for row in rows
    ]


def _csv_data(rows):
    rows = _display_rows(rows)
    columns = list(dict.fromkeys(k for row in rows for k in row))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        # Spreadsheet applications can interpret leading symbols as formulas.
        writer.writerow({k: "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v
                         for k, v in row.items()})
    return output.getvalue().encode("utf-8-sig")


def _extract_artifacts(tool_calls_log):
    cards = []
    for call in tool_calls_log:
        result = call["result"]
        fields = []
        if isinstance(result, dict):
            fields = [{"label": str(k), "value": str(v)} for k, v in result.items()
                      if isinstance(v, (str, int, float, bool))][:8]
        tables = _result_tables(result)
        cards.append({"title": call["tool"].replace("_", " ").title(),
                      "fields": fields, "tables": tables, "result": result})
    return cards


def render_artifacts_panel(agent_id: str, session_title: str):
    st.markdown('<div class="art-header">Investigation results</div>', unsafe_allow_html=True)
    st.caption(session_title)
    cards = st.session_state.artifacts.get(agent_id, [])
    if not cards:
        st.info("Tables, metrics, and evidence will appear after your first question.")
        return
    st.caption("Latest question | Values as returned by the platform")
    for index, card in enumerate(cards):
        with st.container(border=True):
            st.markdown(f"**{card['title']}**")
            fields = card.get("fields", [])
            metrics = [f for f in fields if isinstance(card.get("result", {}).get(f["label"]), (int, float))
                       and not isinstance(card.get("result", {}).get(f["label"]), bool)] if isinstance(card.get("result"), dict) else []
            for offset in range(0, min(len(metrics), 4), 2):
                cols = st.columns(2)
                for col, field in zip(cols, metrics[offset:offset + 2]):
                    col.metric(field["label"].replace("_", " ").title(), field["value"])
            for field in fields:
                if field not in metrics:
                    tone = _status_class(field["value"])
                    value = escape(field["value"])
                    st.markdown(f'<div class="art-fl">{escape(field["label"])}</div><div class="art-fv {tone}">{value}</div>', unsafe_allow_html=True)
            for table_index, (label, rows) in enumerate(card.get("tables", [])):
                st.caption(f"{label} | {len(rows):,} returned records")
                st.dataframe(_display_rows(rows[:500]), use_container_width=True, hide_index=True)
                if len(rows) > 500:
                    st.caption("Showing the first 500 records. Download includes all returned records.")
                st.download_button("Download CSV", _csv_data(rows),
                                   file_name=f"{agent_id}_{index + 1}_{table_index + 1}.csv", mime="text/csv",
                                   key=f"csv_{agent_id}_{index}_{table_index}")
            st.download_button("Download raw result", json.dumps(card.get("result"), indent=2, ensure_ascii=False, default=str),
                               file_name=f"{agent_id}_result_{index + 1}.json", mime="application/json",
                               key=f"json_{agent_id}_{index}")


# -------------------------------------------------------------------
# Render: tool-execution step checklist
# -------------------------------------------------------------------
def render_tool_steps(agent_id: str):
    steps = st.session_state.step_groups.get(agent_id, [])
    if not steps:
        return

    rows = ""
    for step in steps:
        count      = step["count"]
        badge_text = f"{count} TOOL{'S' if count != 1 else ''} QUERIED"
        text       = step.get("text", "")
        if len(text) > 160:
            text = text[:160] + "…"
        rows += f"""
        <div class="step-row">
            <span class="step-check">✓</span>
            <span class="step-badge">{badge_text}</span>
            <span class="step-text">{escape(text)}</span>
        </div>"""

    # Final "Answer ready" row once assistant has replied
    msgs = st.session_state.histories.get(agent_id, [])
    if msgs and msgs[-1]["role"] == "assistant" and not st.session_state.last_error.get(agent_id):
        rows += """
        <div class="step-row">
            <span class="step-check">✓</span>
            <span class="step-badge green">ANSWER READY</span>
            <span class="step-text">Analysis complete — summary and recommendations ready below.</span>
        </div>"""

    st.markdown(f'<div class="step-wrap">{rows}</div>', unsafe_allow_html=True)


# -------------------------------------------------------------------
# Agent turn handler
# -------------------------------------------------------------------
def handle_turn(provider, messages, context, user_input, verify_ssl):
    agent_id = provider.spec.id

    # Set session title from first question
    if agent_id not in st.session_state.session_titles:
        t = user_input[:65] + ("…" if len(user_input) > 65 else "")
        st.session_state.session_titles[agent_id] = t
    st.session_state.last_query[agent_id] = user_input
    st.session_state.last_error[agent_id] = None  # clear any previous error

    messages.append({"role": "user", "content": user_input})

    # Clear previous evidence so a failed new turn cannot show stale results.
    st.session_state.knowledge_sources[agent_id] = []
    st.session_state.step_groups[agent_id] = []
    st.session_state.tool_calls_log[agent_id] = []
    st.session_state.artifacts[agent_id] = []
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.status("Reviewing your question...", expanded=True) as progress:
        completed_calls = []
        partial = False

        def update_progress(event):
            nonlocal partial
            stage = event["stage"]
            if stage == "retrieving":
                progress.update(label="Searching local runbooks and documentation...")
            elif stage == "knowledge":
                st.session_state.knowledge_sources[agent_id] = event["sources"]
                st.write(f"Retrieved {len(event['sources'])} knowledge passages." if event["sources"] else "No matching local knowledge. Continuing with platform evidence.")
            elif stage == "reviewing":
                progress.update(label="Reviewing results and preparing the next step..." if completed_calls else "Reviewing your question...")
            elif stage == "tool_started":
                name = event["tool"].replace("_", " ")
                progress.update(label=f"Running {name}...")
                st.write(f"Running: {name}")
            elif stage == "tool_finished":
                completed_calls.append({"tool": event["tool"], "result": event["result"]})
                st.session_state.tool_calls_log[agent_id] = list(completed_calls)
                st.session_state.artifacts[agent_id] = _extract_artifacts(completed_calls)
                st.write(f"Returned: {event['tool'].replace('_', ' ')}")
            elif stage == "partial":
                partial = True
                st.warning(event["reason"])
            elif stage == "complete":
                progress.update(label="Answer ready", state="complete", expanded=False)
        try:
            agent = ObservabilityAgent(cfg.anthropic_key())
            answer_text, tool_calls_log, step_groups = agent.ask(
                provider, user_input, history=context, verify_ssl=verify_ssl,
                on_progress=update_progress
            )

            st.session_state.step_groups[agent_id]    = step_groups
            st.session_state.tool_calls_log[agent_id] = tool_calls_log
            st.session_state.artifacts[agent_id]      = _extract_artifacts(tool_calls_log)

            messages.append({"role": "assistant", "content": answer_text,
                             "sources": st.session_state.knowledge_sources.get(agent_id, [])})
            context.append({"question": user_input, "answer": answer_text})
            if partial:
                st.session_state.last_error[agent_id] = "Investigation incomplete. Review the available evidence before acting."
            progress.update(label="Investigation stopped with partial results" if partial else "Answer ready",
                            state="error" if partial else "complete", expanded=partial)

        except anthropic.AuthenticationError:
            progress.update(label="Authentication failed", state="error")
            messages.pop()
            st.session_state.last_error[agent_id] = (
                "Anthropic authentication failed — check ANTHROPIC_API_KEY in .env"
            )
        except Exception as exc:
            progress.update(label="Investigation interrupted", state="error")
            messages.pop()
            st.session_state.last_error[agent_id] = f"Something went wrong: {exc}"


# -------------------------------------------------------------------
# Chat view — 2-column main area
# -------------------------------------------------------------------
def render_chat(provider):
    spec     = provider.spec
    agent_id = spec.id

    verify_ssl = st.session_state["ssl_verify"].get(agent_id, spec.ssl_default)
    messages   = st.session_state.histories.setdefault(agent_id, [])
    context    = st.session_state.contexts.setdefault(agent_id, [])
    title      = st.session_state.session_titles.get(agent_id, f"{spec.name} Investigation")

    # ── Breadcrumb ──
    st.markdown(f"""
    <div class="observiq-breadcrumb">
        🏠 <span class="sep">›</span>
        Sessions <span class="sep">›</span>
        <span class="curr">{escape(spec.icon)} {escape(title)}</span>
    </div>""", unsafe_allow_html=True)

    # ── Two-column split: chat (left) | artifacts (right) ──
    col_chat, col_art = st.columns([7, 3], gap="large")

    with col_chat:
        # Persistent error banner (survives st.rerun)
        err = st.session_state.last_error.get(agent_id)
        if err:
            st.error(f"❌ {err}")

        # Active query description
        last_q = st.session_state.last_query.get(agent_id)
        if last_q:
            st.markdown(
                f'<div class="session-query"><strong>{escape(spec.icon)} {escape(spec.name)}:</strong> {escape(last_q)}</div>',
                unsafe_allow_html=True,
            )

        # Tool-execution step checklist
        render_tool_steps(agent_id)

        # Chat message history
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander("Knowledge sources for this answer"):
                        st.caption("Retrieved references; citations in the answer identify which were used.")
                        for source in msg["sources"]:
                            st.text(f"[{source['id']}] {source['source']} | lines {source['start_line']}-{source['end_line']}")
                            st.text(source["text"])

        # Debug expander — raw tool calls & responses
        tool_log = st.session_state.tool_calls_log.get(agent_id, [])
        if tool_log:
            with st.expander(f"Investigation details ({len(tool_log)} tool calls)"):
                for i, call in enumerate(tool_log, 1):
                    st.markdown(f"**Call {i}: `{call['tool']}`**")
                    st.caption("Input")
                    st.json(call.get("input", {}))
                    st.caption("Result")
                    st.json(call["result"])
                    if i < len(tool_log):
                        st.divider()

        # Sample-question chips (empty conversation only)
        if not messages and spec.samples:
            st.write("**Try asking:**")
            chip_cols = st.columns(min(len(spec.samples), 2))
            for index, sample in enumerate(spec.samples):
                c = chip_cols[index % len(chip_cols)]
                if c.button(sample, key=f"chip_{agent_id}_{sample}", use_container_width=True):
                    st.session_state.pending_input = sample
                    st.rerun()

    with col_art:
        render_artifacts_panel(agent_id, title)

    # ── Chat input (page-level — Streamlit anchors it at the bottom) ──
    typed      = st.chat_input(f"Ask {spec.name} anything about your infrastructure…")
    user_input = st.session_state.pending_input or typed
    st.session_state.pending_input = None

    if user_input:
        if not cfg.has_anthropic():
            st.error("Anthropic API key not found — set ANTHROPIC_API_KEY in .env")
            st.stop()
        missing = provider.missing_credentials()
        if missing:
            st.error(f"{spec.name} credentials not found — set in .env: " + ", ".join(missing))
            st.stop()

        handle_turn(provider, messages, context, user_input, verify_ssl)
        st.rerun()


# -------------------------------------------------------------------
# Router
# -------------------------------------------------------------------
render_sidebar()

_active = registry.get(st.session_state.active_agent)
if _active is None:
    render_home()
else:
    render_chat(_active)
