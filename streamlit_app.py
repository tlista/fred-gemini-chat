"""Streamlit Cloud application for FRED + Gemini Economic Assistant."""

import asyncio
import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from app.gemini_agent import FredGeminiAgent
from app.fred_client import POPULAR_SERIES
from app.models import ChatMessage

# Page setup
st.set_page_config(
    page_title="FRED + Gemini Economic Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished look
st.markdown("""
<style>
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #8b949e;
        margin-bottom: 1.5rem;
    }
    .tool-box {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 8px;
        font-family: monospace;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


def get_secret(key: str, default: str = "") -> str:
    """Retrieve secret from Streamlit secrets, environment, or default."""
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)


# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# Sidebar Configuration
with st.sidebar:
    st.title("📈 FRED + Gemini")
    st.caption("Autonomous Macroeconomic Intelligence")

    st.subheader("⚙️ API Configuration")
    default_gemini = get_secret("GEMINI_API_KEY", "")
    default_fred = get_secret("FRED_API_KEY", "")

    gemini_key = st.text_input(
        "Google Gemini API Key",
        value=default_gemini,
        type="password",
        help="Get a free key from https://aistudio.google.com/"
    )

    fred_key = st.text_input(
        "St. Louis Fed (FRED) API Key",
        value=default_fred,
        type="password",
        help="Get a free 32-character key from https://fred.stlouisfed.org/docs/api/api_key.html"
    )

    model_name = st.selectbox(
        "Gemini Model",
        options=["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro", "gemini-1.5-pro"],
        index=0,
        help="gemini-2.5-flash is fast and recommended for tool orchestration."
    )

    # Status indicators
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if gemini_key:
            st.success("Gemini: Live", icon="✨")
        else:
            st.warning("Gemini: Demo", icon="💡")
    with col2:
        if fred_key:
            st.success("FRED: Live", icon="🏛️")
        else:
            st.warning("FRED: Demo", icon="📊")

    # Quick Prompts
    st.divider()
    st.subheader("💡 Popular Economic Prompts")
    quick_prompts = [
        ("📊 CPI Inflation", "What is the current US inflation rate and how has it changed over the past year?"),
        ("📉 Yield Curve Inversion", "Compare 10-Year vs 2-Year Treasury Yields and chart the yield spread."),
        ("🏠 Mortgage vs Fed Funds", "Chart the 30-Year Fixed Mortgage Rate vs the Federal Funds Rate over the last 3 years."),
        ("💼 Jobs & Unemployment", "What is the current US unemployment rate and nonfarm payroll trajectory?"),
        ("📈 Real GDP Growth", "How has Real GDP (GDPC1) evolved over the last 3 years?"),
    ]

    for label, query in quick_prompts:
        if st.button(label, use_container_width=True):
            st.session_state.pending_prompt = query

    st.divider()
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        st.rerun()


# Main Chat Interface
st.markdown('<div class="main-title">🏛️ Macroeconomic Chat Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Powered by Google Gemini & the St. Louis Federal Reserve Economic Data (FRED) API</div>', unsafe_allow_html=True)


def render_chart(chart_data):
    """Render interactive multi-series Plotly chart from ChartData."""
    fig = go.Figure()

    colors = ["#58a6ff", "#d29922", "#3fb950", "#bc8cff", "#f85149"]

    for i, s in enumerate(chart_data.series_list):
        if not s.dates or not s.values:
            continue
        c = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=s.dates,
            y=s.values,
            mode="lines+markers",
            name=f"{s.name} ({s.units})" if s.units else s.name,
            line=dict(color=c, width=2.5),
            marker=dict(size=4)
        ))

    fig.update_layout(
        title=dict(text=chart_data.title, font=dict(size=16)),
        xaxis_title="Date",
        yaxis_title=chart_data.y_axis_label or "Value",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)


# Render conversation history
for msg in st.session_state.messages:
    role = msg.get("role", "assistant")
    avatar = "👤" if role == "user" else "🏛️"
    with st.chat_message(role, avatar=avatar):
        # Render tools executed if present
        tool_calls = msg.get("tool_calls", [])
        if tool_calls:
            with st.expander(f"🛠️ FRED Tools Executed ({len(tool_calls)})", expanded=False):
                for tc in tool_calls:
                    st.markdown(f"**`{tc.get('tool_name')}`** ({tc.get('execution_time_ms', 0)}ms)")
                    st.json(tc.get("arguments", {}))
                    st.caption(f"Result: {tc.get('result_summary', '')}")
                    st.divider()

        # Render message text
        st.markdown(msg.get("content", ""))

        # Render charts if present
        for chart in msg.get("charts", []):
            render_chart(chart)


# Handle incoming message (either from chat input or quick prompt button)
user_query = st.chat_input("Ask about inflation, interest rates, GDP, housing, or any FRED series...")

if st.session_state.pending_prompt:
    user_query = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_query:
    # 1. Display user query
    st.session_state.messages.append({
        "role": "user",
        "content": user_query,
        "tool_calls": [],
        "charts": []
    })
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_query)

    # 2. Convert session messages to ChatMessage models for agent
    history_models = []
    for m in st.session_state.messages[:-1]:
        history_models.append(
            ChatMessage(
                role="user" if m["role"] == "user" else "model",
                content=m["content"]
            )
        )

    # 3. Call Agent
    with st.chat_message("assistant", avatar="🏛️"):
        with st.spinner("Gemini is analyzing query and querying FRED API..."):
            agent = FredGeminiAgent(
                gemini_api_key=gemini_key,
                fred_api_key=fred_key,
                model_name=model_name
            )
            response = asyncio.run(agent.chat(user_query, history_models))

        # Show tool trace
        if response.tool_calls:
            with st.expander(f"🛠️ FRED Tools Executed ({len(response.tool_calls)})", expanded=False):
                for tc in response.tool_calls:
                    st.markdown(f"**`{tc.tool_name}`** ({tc.execution_time_ms}ms)")
                    st.json(tc.arguments)
                    st.caption(f"Result: {tc.result_summary}")
                    st.divider()

        # Show text reply
        st.markdown(response.reply)

        # Show charts
        for chart in response.charts:
            render_chart(chart)

    # 4. Save assistant response to state
    st.session_state.messages.append({
        "role": "assistant",
        "content": response.reply,
        "tool_calls": [tc.model_dump() for tc in response.tool_calls],
        "charts": response.charts
    })
