"""Gemini AI Agent with Federal Reserve Economic Data (FRED) Function Calling Tools."""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from google import genai
from google.genai import types

from app.config import settings
from app.fred_client import FredClient, POPULAR_SERIES
from app.models import (
    ChatMessage,
    ChatResponse,
    ChartData,
    ChartSeries,
    ToolCallRecord,
)

logger = logging.getLogger(__name__)

# System instructions for Gemini
SYSTEM_INSTRUCTION = """You are an expert Macroeconomic and Financial Analyst powered by the Federal Reserve Bank of St. Louis Economic Data (FRED) API.

Your mission is to provide accurate, data-backed economic insights using real Federal Reserve statistics.

Guidelines:
1. Always utilize the available FRED tools (`search_economic_data`, `get_economic_series_data`, `get_series_metadata`, `generate_economic_chart`) to retrieve actual data rather than speculating on numbers.
2. Frequently used FRED Series IDs:
   - CPIAUCSL: Consumer Price Index (Headline CPI inflation)
   - CPILFESL: Core CPI (excludes food & energy)
   - PCEPILFE: Core PCE Price Index (Fed's primary inflation benchmark, 2% target)
   - GDP: Nominal Gross Domestic Product (Quarterly)
   - GDPC1: Real Gross Domestic Product (Inflation-adjusted)
   - FEDFUNDS: Federal Funds Effective Rate (Fed benchmark rate)
   - UNRATE: Civilian Unemployment Rate (%)
   - PAYEMS: Total Nonfarm Payroll Employment
   - MORTGAGE30US: 30-Year Fixed Rate Mortgage Average (%)
   - DGS10 / DGS2: 10-Year and 2-Year Treasury Yields (%)
   - T10Y2Y: 10-Year minus 2-Year Treasury Spread (Yield curve indicator)
3. When the user asks for a chart, visual comparison, historical trend, or graph, call `generate_economic_chart` with the relevant series IDs so an interactive chart is rendered for the user.
4. Always clarify units (e.g. %, billions of dollars, index level), observation frequency (monthly, quarterly, daily), and whether data is seasonally adjusted.
5. Provide clear, concise commentary synthesizing economic context, recent turning points, and macroeconomic implications.
"""

# Gemini Tool Declarations
FRED_TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="search_economic_data",
        description="Search the FRED database for economic series matching keywords (e.g., inflation, GDP, unemployment, interest rate, mortgage).",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "search_text": types.Schema(
                    type="STRING",
                    description="Keywords to search for economic indicators"
                ),
                "limit": types.Schema(
                    type="INTEGER",
                    description="Maximum number of series to return (default 5, max 20)"
                )
            },
            required=["search_text"]
        )
    ),
    types.FunctionDeclaration(
        name="get_economic_series_data",
        description="Retrieve historical numerical observation data for a specific FRED series ID (e.g., 'CPIAUCSL', 'GDP', 'FEDFUNDS', 'UNRATE').",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "series_id": types.Schema(
                    type="STRING",
                    description="The uppercase FRED series identifier (e.g. 'CPIAUCSL', 'GDP', 'UNRATE', 'FEDFUNDS')"
                ),
                "observation_start": types.Schema(
                    type="STRING",
                    description="Earliest date to retrieve in YYYY-MM-DD format (optional)"
                ),
                "observation_end": types.Schema(
                    type="STRING",
                    description="Latest date to retrieve in YYYY-MM-DD format (optional)"
                ),
                "units": types.Schema(
                    type="STRING",
                    description="Data transformation: 'lin' (levels), 'chg' (change), 'pch' (percent change), 'pc1' (percent change from 1 year ago)"
                ),
                "limit": types.Schema(
                    type="INTEGER",
                    description="Maximum number of observations to fetch (default 30, max 200)"
                )
            },
            required=["series_id"]
        )
    ),
    types.FunctionDeclaration(
        name="get_series_metadata",
        description="Fetch detailed metadata, description, publication frequency, and units for a FRED series ID.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "series_id": types.Schema(
                    type="STRING",
                    description="The uppercase FRED series ID"
                )
            },
            required=["series_id"]
        )
    ),
    types.FunctionDeclaration(
        name="generate_economic_chart",
        description="Create an interactive visual chart in the chat interface comparing one or more FRED economic series over time.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "series_ids": types.Schema(
                    type="ARRAY",
                    items=types.Schema(type="STRING"),
                    description="List of FRED series IDs to include in the chart (e.g. ['DGS10', 'DGS2'] or ['FEDFUNDS', 'MORTGAGE30US'])"
                ),
                "title": types.Schema(
                    type="STRING",
                    description="Descriptive chart title"
                ),
                "observation_start": types.Schema(
                    type="STRING",
                    description="Start date for chart observations in YYYY-MM-DD format (optional, e.g. '2021-01-01')"
                ),
                "chart_type": types.Schema(
                    type="STRING",
                    description="Visual representation: 'line' (default) or 'bar'"
                )
            },
            required=["series_ids", "title"]
        )
    )
]


class FredGeminiAgent:
    """Agent that handles multi-turn conversation with Gemini and executes FRED tools."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        fred_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2
    ):
        self.gemini_api_key = (gemini_api_key or settings.GEMINI_API_KEY).strip()
        self.fred_api_key = (fred_api_key or settings.FRED_API_KEY).strip()
        self.model_name = (model_name or settings.DEFAULT_GEMINI_MODEL).strip()
        self.temperature = temperature
        self.fred_client = FredClient(api_key=self.fred_api_key)

    @property
    def has_gemini_key(self) -> bool:
        """Check if a Gemini API key is configured."""
        return bool(self.gemini_api_key and len(self.gemini_api_key) >= 15)

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        collected_charts: List[ChartData]
    ) -> Tuple[Dict[str, Any], ToolCallRecord]:
        """Execute a single FRED tool requested by the model and record trace."""
        start_time = time.perf_counter()
        result: Dict[str, Any] = {}
        summary = ""

        try:
            if tool_name == "search_economic_data":
                search_text = arguments.get("search_text", "")
                limit = int(arguments.get("limit", 5))
                seriess = await self.fred_client.search_series(search_text=search_text, limit=limit)
                result = {"series": seriess, "total_found": len(seriess)}
                summary = f"Found {len(seriess)} series matching '{search_text}'"

            elif tool_name == "get_economic_series_data":
                series_id = arguments.get("series_id", "")
                start = arguments.get("observation_start")
                end = arguments.get("observation_end")
                units = arguments.get("units")
                limit = int(arguments.get("limit", 30))
                obs_data = await self.fred_client.get_series_observations(
                    series_id=series_id,
                    observation_start=start,
                    observation_end=end,
                    units=units,
                    limit=limit
                )
                result = obs_data
                cnt = obs_data.get("count", 0)
                summary = f"Retrieved {cnt} observations for {series_id} ({obs_data.get('units', '')})"

            elif tool_name == "get_series_metadata":
                series_id = arguments.get("series_id", "")
                meta = await self.fred_client.get_series_metadata(series_id)
                result = meta
                summary = f"Retrieved metadata for {series_id}: {meta.get('title', '')}"

            elif tool_name == "generate_economic_chart":
                series_ids = arguments.get("series_ids", [])
                title = arguments.get("title", "Economic Data Chart")
                obs_start = arguments.get("observation_start")
                chart_type = arguments.get("chart_type", "line")

                series_list = []
                for sid in series_ids:
                    data = await self.fred_client.get_series_observations(
                        series_id=sid,
                        observation_start=obs_start,
                        limit=100
                    )
                    obs = data.get("observations", [])
                    dates = [o["date"] for o in obs]
                    vals = [o["value"] for o in obs]
                    series_list.append(
                        ChartSeries(
                            id=sid,
                            name=data.get("title", sid),
                            units=data.get("units", ""),
                            dates=dates,
                            values=vals
                        )
                    )

                chart = ChartData(
                    chart_id=f"chart_{int(time.time() * 1000)}",
                    title=title,
                    series_list=series_list,
                    chart_type=chart_type,
                    y_axis_label=series_list[0].units if series_list else ""
                )
                collected_charts.append(chart)
                result = {
                    "chart_created": True,
                    "title": title,
                    "series_count": len(series_list),
                    "data_points": sum(len(s.dates) for s in series_list)
                }
                summary = f"Generated interactive chart '{title}' with {len(series_list)} series"

            else:
                result = {"error": f"Unknown tool: {tool_name}"}
                summary = f"Error: unknown tool '{tool_name}'"

        except Exception as e:
            logger.exception("Error executing tool %s: %s", tool_name, e)
            result = {"error": str(e)}
            summary = f"Execution failed: {str(e)}"

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        record = ToolCallRecord(
            tool_name=tool_name,
            arguments=arguments,
            result_summary=summary,
            execution_time_ms=elapsed_ms
        )
        return result, record

    async def chat(
        self,
        message: str,
        history: Optional[List[ChatMessage]] = None
    ) -> ChatResponse:
        """Run chat turn, calling FRED tools when prompted by Gemini."""
        history = history or []
        collected_tool_records: List[ToolCallRecord] = []
        collected_charts: List[ChartData] = []

        # If Gemini key is not configured, run demo intelligence pipeline
        if not self.has_gemini_key:
            return await self._run_demo_response(message, history, collected_tool_records, collected_charts)

        client = genai.Client(api_key=self.gemini_api_key)
        tools = [types.Tool(function_declarations=FRED_TOOL_DECLARATIONS)]
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=tools,
            temperature=self.temperature
        )

        # Build message history for Gemini
        contents: List[types.Content] = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.content)]))
        
        # Add current user prompt
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

        max_turns = 6
        final_text = ""

        for turn in range(max_turns):
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )

            # Check if Gemini wants to call tools
            function_calls = response.function_calls
            if function_calls:
                # Add model's tool calls to contents
                model_parts = []
                for fc in function_calls:
                    model_parts.append(types.Part.from_function_call(name=fc.name, args=fc.args))
                contents.append(types.Content(role="model", parts=model_parts))

                # Execute each tool call and return response
                tool_response_parts = []
                for fc in function_calls:
                    tool_result, record = await self.execute_tool(
                        tool_name=fc.name,
                        arguments=fc.args,
                        collected_charts=collected_charts
                    )
                    collected_tool_records.append(record)
                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response=tool_result
                        )
                    )

                # Send tool responses back to model
                contents.append(types.Content(role="user", parts=tool_response_parts))
            else:
                # Model provided final textual answer
                final_text = response.text or ""
                break

        if not final_text and not collected_tool_records:
            final_text = "I was unable to retrieve a response. Please check your query or API configuration."

        updated_history = list(history)
        updated_history.append(ChatMessage(role="user", content=message))
        updated_history.append(
            ChatMessage(
                role="model",
                content=final_text,
                tool_calls=collected_tool_records,
                charts=collected_charts
            )
        )

        return ChatResponse(
            reply=final_text,
            tool_calls=collected_tool_records,
            charts=collected_charts,
            model_used=self.model_name,
            demo_mode=False,
            history=updated_history
        )

    async def _run_demo_response(
        self,
        message: str,
        history: List[ChatMessage],
        collected_tool_records: List[ToolCallRecord],
        collected_charts: List[ChartData]
    ) -> ChatResponse:
        """Provide intelligent demo responses with actual FRED data when Gemini key is not yet set."""
        q = message.lower()
        target_series_id = "CPIAUCSL"
        topic_title = "Consumer Price Index (CPI)"
        series_ids = ["CPIAUCSL"]

        if any(term in q for term in ["inflation", "cpi", "pce", "price index", "cost of living"]):
            target_series_id = "CPIAUCSL"
            topic_title = "Consumer Price Index (CPI)"
            series_ids = ["CPIAUCSL", "CPILFESL"]
        elif any(term in q for term in ["mortgage", "housing", "house"]):
            target_series_id = "MORTGAGE30US"
            topic_title = "30-Year Fixed Mortgage Rate"
            series_ids = ["MORTGAGE30US", "FEDFUNDS"]
        elif any(term in q for term in ["fed funds", "federal funds", "interest rate", "fed rate", "powell", "fomc"]):
            target_series_id = "FEDFUNDS"
            topic_title = "Federal Funds Effective Rate"
            series_ids = ["FEDFUNDS"]
        elif any(term in q for term in ["unemployment", "job", "payroll", "labor", "work"]):
            target_series_id = "UNRATE"
            topic_title = "Civilian Unemployment Rate"
            series_ids = ["UNRATE"]
        elif any(term in q for term in ["gdp", "growth", "economy", "output"]):
            target_series_id = "GDP"
            topic_title = "Gross Domestic Product"
            series_ids = ["GDP"]
        elif any(term in q for term in ["yield", "curve", "treasury", "bond", "10-year", "2-year"]):
            target_series_id = "T10Y2Y"
            topic_title = "10-Year vs 2-Year Treasury Yield Spread"
            series_ids = ["DGS10", "DGS2", "T10Y2Y"]

        # Run search tool
        _, rec1 = await self.execute_tool(
            "search_economic_data",
            {"search_text": target_series_id, "limit": 3},
            collected_charts
        )
        collected_tool_records.append(rec1)

        # Run observations tool
        obs_res, rec2 = await self.execute_tool(
            "get_economic_series_data",
            {"series_id": target_series_id, "limit": 10},
            collected_charts
        )
        collected_tool_records.append(rec2)

        # Generate chart
        _, rec3 = await self.execute_tool(
            "generate_economic_chart",
            {"series_ids": series_ids, "title": f"U.S. {topic_title} Trend"},
            collected_charts
        )
        collected_tool_records.append(rec3)

        observations = obs_res.get("observations", [])
        latest_val = observations[-1]["value"] if observations else "N/A"
        latest_date = observations[-1]["date"] if observations else "recent"
        units = obs_res.get("units", "")

        reply = (
            f"### 📊 Macroeconomic Analysis: {topic_title}\n\n"
            f"Based on data retrieved directly from the **Federal Reserve Economic Data (FRED)** database:\n\n"
            f"- **Series ID**: `{target_series_id}`\n"
            f"- **Latest Reading**: **{latest_val} {units}** (as of {latest_date})\n"
            f"- **Frequency**: {obs_res.get('frequency', 'Monthly')}\n\n"
            f"#### Summary & Economic Context\n"
            f"The data shows significant macroeconomic shifts over recent cycles. As shown in the generated interactive chart below, "
            f"policymakers and markets closely watch **{target_series_id}** to gauge economic momentum and Federal Reserve monetary policy direction.\n\n"
            f"> [!NOTE]\n"
            f"> **Demo Mode Active**: You are interacting with FRED tools in demo mode. Enter your **Gemini API Key** in the settings panel to activate open-ended autonomous agent reasoning with live Gemini models!"
        )

        updated_history = list(history)
        updated_history.append(ChatMessage(role="user", content=message))
        updated_history.append(
            ChatMessage(
                role="model",
                content=reply,
                tool_calls=collected_tool_records,
                charts=collected_charts
            )
        )

        return ChatResponse(
            reply=reply,
            tool_calls=collected_tool_records,
            charts=collected_charts,
            model_used="demo-mode",
            demo_mode=True,
            history=updated_history
        )
