"""Tests for the Gemini Agent and FRED Tool Calling."""

import asyncio
from app.gemini_agent import FredGeminiAgent, FRED_TOOL_DECLARATIONS
from app.models import ChartData


def test_tool_declarations_validity():
    """Verify tool declarations contain expected functions and schemas."""
    tool_names = [t.name for t in FRED_TOOL_DECLARATIONS]
    assert "search_economic_data" in tool_names
    assert "get_economic_series_data" in tool_names
    assert "get_series_metadata" in tool_names
    assert "generate_economic_chart" in tool_names


def test_tool_execution_search():
    """Verify executing search_economic_data returns series."""
    async def _run():
        agent = FredGeminiAgent()
        charts = []
        result, record = await agent.execute_tool(
            "search_economic_data",
            {"search_text": "inflation", "limit": 3},
            charts
        )
        assert record.tool_name == "search_economic_data"
        assert "series" in result
        assert len(result["series"]) > 0

    asyncio.run(_run())


def test_tool_execution_chart():
    """Verify executing generate_economic_chart returns structured chart data."""
    async def _run():
        agent = FredGeminiAgent()
        charts = []
        result, record = await agent.execute_tool(
            "generate_economic_chart",
            {
                "series_ids": ["FEDFUNDS", "UNRATE"],
                "title": "Fed Funds Rate vs Unemployment",
                "chart_type": "line"
            },
            charts
        )
        assert record.tool_name == "generate_economic_chart"
        assert result["chart_created"] is True
        assert len(charts) == 1
        chart = charts[0]
        assert isinstance(chart, ChartData)
        assert chart.title == "Fed Funds Rate vs Unemployment"
        assert len(chart.series_list) == 2
        assert chart.series_list[0].id == "FEDFUNDS"
        assert len(chart.series_list[0].dates) > 0

    asyncio.run(_run())


def test_demo_chat_flow():
    """Verify demo mode chat returns structured reply, tool calls, and charts."""
    async def _run():
        agent = FredGeminiAgent()  # without keys -> runs demo pipeline
        response = await agent.chat("What is the current US inflation rate?")

        assert response.demo_mode is True
        assert len(response.tool_calls) >= 2
        assert len(response.charts) >= 1
        assert "Consumer Price Index" in response.reply
        assert len(response.history) == 2

    asyncio.run(_run())
