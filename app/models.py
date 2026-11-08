"""Data models for FRED + Gemini Chat application."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    """Record of a tool call executed by the agent."""
    tool_name: str
    arguments: Dict[str, Any]
    result_summary: str
    execution_time_ms: float = 0.0


class ChartSeries(BaseModel):
    """A single data series in a chart."""
    id: str
    name: str
    units: str = ""
    dates: List[str] = Field(default_factory=list)
    values: List[float] = Field(default_factory=list)


class ChartData(BaseModel):
    """Structured data for frontend interactive charting."""
    chart_id: str
    title: str
    series_list: List[ChartSeries] = Field(default_factory=list)
    chart_type: str = "line"  # "line" or "bar"
    y_axis_label: str = ""


class ChatMessage(BaseModel):
    """Individual message in conversation history."""
    role: str  # "user", "model", or "system"
    content: str
    timestamp: Optional[str] = None
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    charts: List[ChartData] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """User request sent from chat client."""
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    model: Optional[str] = None
    fred_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    temperature: float = 0.2


class ChatResponse(BaseModel):
    """Response returned to chat client."""
    reply: str
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    charts: List[ChartData] = Field(default_factory=list)
    model_used: str
    demo_mode: bool = False
    history: List[ChatMessage] = Field(default_factory=list)


class TestKeysRequest(BaseModel):
    """Request to validate API keys."""
    gemini_api_key: Optional[str] = None
    fred_api_key: Optional[str] = None


class TestKeysResponse(BaseModel):
    """Validation response for API keys."""
    gemini_valid: bool
    gemini_message: str
    fred_valid: bool
    fred_message: str
