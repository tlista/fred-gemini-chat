# 🏛️ FRED + Gemini Economic Assistant & Chat Tool

An intelligent conversational macroeconomic analysis tool connecting **Google Gemini** models to the **Federal Reserve Economic Data (FRED)** API via real-time tool use (Function Calling).

Users can query real-time macroeconomic indicators, track inflation trends, compare Treasury yields, analyze GDP, and render interactive multi-series charts directly in conversation.

---

## 🌟 Highlights

- **Gemini Autonomous Tool Calling**: Equipped with custom FRED tools (`search_economic_data`, `get_economic_series_data`, `get_series_metadata`, `generate_economic_chart`) enabling Gemini models (`gemini-2.5-flash`, `gemini-1.5-pro`, etc.) to self-direct and fetch actual data before generating analysis.
- **Interactive Visual Charts**: Gemini automatically generates multi-series time-series charts (rendered via Chart.js) with tooltips, legend toggling, and date alignment.
- **Full Tool Call Transparency**: Every tool invocation shows an expandable accordion card displaying the query arguments, response summary, and execution duration in milliseconds.
- **Dual Mode (Live & Demo)**:
  - **Live Mode**: Uses your own St. Louis Fed API key and Google AI Studio Gemini key.
  - **Demo Mode**: Includes pre-packaged historical datasets for popular series (CPI, GDP, Fed Funds Rate, Mortgage Rates, Treasury Yields) so you can test immediately offline.
- **Dual Delivery**:
  - **Modern Responsive Web UI**: Single-page application with dark theme, indicator quick-pills, and settings drawer.
  - **Headless REST API (`POST /api/chat`)**: Ready to plug directly into any mobile app, web app, or backend service.

---

## 📐 Architecture

```
┌────────────────────────────────────────────────────────┐
│                   User Chat Client                     │
│          (Web UI / Mobile App / External API)          │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/chat
                            ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Backend (`app/main.py`)          │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│          Gemini Agent (`app/gemini_agent.py`)          │
│            Model: Gemini 2.5 Flash / Pro               │
└──────────────┬───────────────────────────▲─────────────┘
               │ Function Calls            │ Observation Data
               │ (e.g. search, obs, chart) │ & Metadata
               ▼                           │
┌────────────────────────────────────────────────────────┐
│            FRED Client (`app/fred_client.py`)          │
│     Endpoint: https://api.stlouisfed.org/fred/...      │
│         (Fallback to Demo dataset if offline)          │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- (Optional) [Google Gemini API Key](https://aistudio.google.com/)
- (Optional) [St. Louis Fed FRED API Key](https://fred.stlouisfed.org/docs/api/api_key.html)

### 2. Run the Server
Launch the server using the provided start script:

```bash
./run.sh
```

Or manually:
```bash
# Set up venv and install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser to:
**`http://localhost:8000`**

---

## 🔑 Configuration & API Keys

You can configure API keys in either of two ways:

1. **Environment Variables / `.env` file**:
   ```bash
   cp .env.example .env
   # Edit .env:
   GEMINI_API_KEY=your_gemini_api_key_here
   FRED_API_KEY=your_32_character_fred_api_key
   ```
2. **In the Web UI Settings**:
   Click **⚙️ API Keys & Settings** in the UI. Keys are stored in browser `localStorage` and sent with requests.

---

## 🛠️ Gemini Tools Specification

Gemini is configured with 4 tools defined in [`app/gemini_agent.py`](file:///storage/emulated/10/Documents/Antigravity/FRED%20Chat/app/gemini_agent.py):

| Tool Name | Arguments | Description |
|---|---|---|
| `search_economic_data` | `search_text` (str), `limit` (int) | Searches FRED for matching series IDs and descriptions. |
| `get_economic_series_data` | `series_id` (str), `observation_start`, `observation_end`, `units`, `limit` | Fetches historical date and numerical data points. |
| `get_series_metadata` | `series_id` (str) | Fetches frequency, units, seasonal adjustment, and full series notes. |
| `generate_economic_chart` | `series_ids` (list[str]), `title` (str), `observation_start`, `chart_type` | Prepares structured time-series data for frontend interactive chart widgets. |

---

## 📊 Curated Series Quick Reference

| Series ID | Name | Frequency | Typical Units |
|---|---|---|---|
| `CPIAUCSL` | Consumer Price Index (Headline CPI) | Monthly | Index 1982-1984=100 |
| `CPILFESL` | Core CPI (Excluding Food & Energy) | Monthly | Index 1982-1984=100 |
| `PCEPILFE` | Core PCE Price Index (Fed Target Measure) | Monthly | Index 2017=100 |
| `FEDFUNDS` | Federal Funds Effective Rate | Monthly | Percent (%) |
| `UNRATE` | Civilian Unemployment Rate | Monthly | Percent (%) |
| `PAYEMS` | Total Nonfarm Payrolls | Monthly | Thousands of Persons |
| `GDP` / `GDPC1` | Nominal / Real Gross Domestic Product | Quarterly | Billions of Dollars |
| `MORTGAGE30US` | 30-Year Fixed Rate Mortgage Average | Weekly | Percent (%) |
| `DGS10` / `DGS2` | 10-Year and 2-Year Treasury Yields | Daily | Percent (%) |
| `T10Y2Y` | 10Y minus 2Y Yield Spread (Inversion) | Daily | Percent (%) |

---

## 🔌 Integrating into Another Application

### Python Client Example:
```python
import requests

url = "http://localhost:8000/api/chat"
payload = {
    "message": "Chart the 10-Year Treasury yield vs 2-Year Treasury yield over the last 2 years",
    "gemini_api_key": "YOUR_GEMINI_KEY",
    "fred_api_key": "YOUR_FRED_KEY"
}

response = requests.post(url, json=payload).json()
print("Gemini Reply:\n", response["reply"])
print("Tools Executed:\n", response["tool_calls"])
print("Chart Data:\n", response["charts"])
```

### Direct Python Module Import:
```python
import asyncio
from app.gemini_agent import FredGeminiAgent

async def main():
    agent = FredGeminiAgent(
        gemini_api_key="YOUR_GEMINI_KEY",
        fred_api_key="YOUR_FRED_KEY",
        model_name="gemini-2.5-flash"
    )
    result = await agent.chat("What is the current US inflation rate?")
    print(result.reply)

asyncio.run(main())
```

### JavaScript / React Example:
```javascript
const response = await fetch("http://localhost:8000/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message: "What is the Fed Funds Rate?",
    model: "gemini-2.5-flash"
  })
});

const data = await response.json();
console.log(data.reply, data.charts);
```

---

## 🧪 Running Automated Tests

Run the test suite using pytest:

```bash
PYTHONPATH=. pytest tests/
```
Output:
```
tests/test_api.py .....                                 [ 38%]
tests/test_fred_client.py ....                          [ 69%]
tests/test_gemini_agent.py ....                         [100%]
====================== 13 passed in 0.41s ======================
```
