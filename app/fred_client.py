"""FRED (Federal Reserve Economic Data) API Client.

Provides async access to economic indicators, series search, historical observations,
and metadata from the St. Louis Fed API with built-in fallback/demo datasets.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Curated popular economic indicators for quick discovery and offline demo mode
POPULAR_SERIES: Dict[str, Dict[str, Any]] = {
    "CPIAUCSL": {
        "id": "CPIAUCSL",
        "title": "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average (CPI Inflation)",
        "frequency": "Monthly",
        "units": "Index 1982-1984=100",
        "seasonal_adjustment": "Seasonally Adjusted",
        "category": "Inflation & Prices",
        "notes": "Measures the average monthly change in the price for goods and services paid by urban consumers."
    },
    "CPILFESL": {
        "id": "CPILFESL",
        "title": "Consumer Price Index: All Items Less Food and Energy (Core CPI)",
        "frequency": "Monthly",
        "units": "Index 1982-1984=100",
        "seasonal_adjustment": "Seasonally Adjusted",
        "category": "Inflation & Prices",
        "notes": "Core inflation metric excluding volatile food and energy components."
    },
    "PCEPILFE": {
        "id": "PCEPILFE",
        "title": "Personal Consumption Expenditures: Chain-type Price Index Less Food and Energy (Core PCE)",
        "frequency": "Monthly",
        "units": "Index 2017=100",
        "seasonal_adjustment": "Seasonally Adjusted",
        "category": "Inflation & Prices",
        "notes": "The Federal Reserve's primary target measure for headline inflation policy (2.0% annual target)."
    },
    "GDP": {
        "id": "GDP",
        "title": "Gross Domestic Product (Nominal)",
        "frequency": "Quarterly",
        "units": "Billions of Dollars",
        "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
        "category": "National Accounts",
        "notes": "The monetary value of all finished goods and services made within a country during a specific period."
    },
    "GDPC1": {
        "id": "GDPC1",
        "title": "Real Gross Domestic Product (Inflation-Adjusted)",
        "frequency": "Quarterly",
        "units": "Billions of Chained 2017 Dollars",
        "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
        "category": "National Accounts",
        "notes": "GDP adjusted for price changes/inflation."
    },
    "FEDFUNDS": {
        "id": "FEDFUNDS",
        "title": "Federal Funds Effective Rate",
        "frequency": "Monthly",
        "units": "Percent",
        "seasonal_adjustment": "Not Seasonally Adjusted",
        "category": "Interest Rates",
        "notes": "The interest rate at which depository institutions trade federal funds with each other overnight."
    },
    "UNRATE": {
        "id": "UNRATE",
        "title": "Civilian Unemployment Rate",
        "frequency": "Monthly",
        "units": "Percent",
        "seasonal_adjustment": "Seasonally Adjusted",
        "category": "Labor Market",
        "notes": "The number of unemployed as a percentage of the civilian labor force."
    },
    "PAYEMS": {
        "id": "PAYEMS",
        "title": "All Employees, Total Nonfarm (Nonfarm Payrolls)",
        "frequency": "Monthly",
        "units": "Thousands of Persons",
        "seasonal_adjustment": "Seasonally Adjusted",
        "category": "Labor Market",
        "notes": "A measure of the number of U.S. workers in the economy that excludes proprietors, private household employees, and farm employees."
    },
    "MORTGAGE30US": {
        "id": "MORTGAGE30US",
        "title": "30-Year Fixed Rate Mortgage Average in the United States",
        "frequency": "Weekly",
        "units": "Percent",
        "seasonal_adjustment": "Not Seasonally Adjusted",
        "category": "Housing & Credit",
        "notes": "National average contract interest rate on 30-year fixed-rate mortgages."
    },
    "DGS10": {
        "id": "DGS10",
        "title": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity",
        "frequency": "Daily",
        "units": "Percent",
        "seasonal_adjustment": "Not Seasonally Adjusted",
        "category": "Treasury & Yields",
        "notes": "Yield on 10-year US Treasury benchmark bonds."
    },
    "DGS2": {
        "id": "DGS2",
        "title": "Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity",
        "frequency": "Daily",
        "units": "Percent",
        "seasonal_adjustment": "Not Seasonally Adjusted",
        "category": "Treasury & Yields",
        "notes": "Yield on 2-year US Treasury notes, sensitive to Fed rate policy expectations."
    },
    "T10Y2Y": {
        "id": "T10Y2Y",
        "title": "10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity (Yield Curve Spread)",
        "frequency": "Daily",
        "units": "Percent",
        "seasonal_adjustment": "Not Seasonally Adjusted",
        "category": "Treasury & Yields",
        "notes": "Yield spread indicator; inverted yield curves (<0) have historically preceded US recessions."
    },
    "WALCL": {
        "id": "WALCL",
        "title": "Federal Reserve Total Assets (Balance Sheet)",
        "frequency": "Weekly",
        "units": "Millions of Dollars",
        "seasonal_adjustment": "Not Seasonally Adjusted",
        "category": "Monetary Policy",
        "notes": "Total assets held on the Federal Reserve balance sheet (Quantitative Easing / Tightening indicator)."
    },
    "M2SL": {
        "id": "M2SL",
        "title": "M2 Money Supply",
        "frequency": "Monthly",
        "units": "Billions of Dollars",
        "seasonal_adjustment": "Seasonally Adjusted",
        "category": "Monetary Policy",
        "notes": "Measure of currency, demand deposits, savings deposits, and money market funds."
    }
}

# Pre-packaged sample observations for demo mode and offline testing
SAMPLE_OBSERVATIONS: Dict[str, List[Dict[str, Any]]] = {
    "FEDFUNDS": [
        {"date": "2021-01-01", "value": 0.09},
        {"date": "2021-07-01", "value": 0.10},
        {"date": "2022-01-01", "value": 0.08},
        {"date": "2022-03-01", "value": 0.20},
        {"date": "2022-06-01", "value": 1.21},
        {"date": "2022-09-01", "value": 2.56},
        {"date": "2022-12-01", "value": 4.10},
        {"date": "2023-03-01", "value": 4.65},
        {"date": "2023-07-01", "value": 5.12},
        {"date": "2023-10-01", "value": 5.33},
        {"date": "2024-01-01", "value": 5.33},
        {"date": "2024-05-01", "value": 5.33},
        {"date": "2024-09-01", "value": 4.83},
        {"date": "2024-11-01", "value": 4.58},
        {"date": "2024-12-01", "value": 4.33},
    ],
    "UNRATE": [
        {"date": "2022-01-01", "value": 4.0},
        {"date": "2022-04-01", "value": 3.6},
        {"date": "2022-07-01", "value": 3.5},
        {"date": "2022-10-01", "value": 3.7},
        {"date": "2023-01-01", "value": 3.4},
        {"date": "2023-04-01", "value": 3.4},
        {"date": "2023-07-01", "value": 3.5},
        {"date": "2023-10-01", "value": 3.8},
        {"date": "2024-01-01", "value": 3.7},
        {"date": "2024-04-01", "value": 3.9},
        {"date": "2024-07-01", "value": 4.3},
        {"date": "2024-10-01", "value": 4.1},
        {"date": "2024-12-01", "value": 4.1},
    ],
    "CPIAUCSL": [
        {"date": "2022-01-01", "value": 281.933},
        {"date": "2022-06-01", "value": 295.328},
        {"date": "2022-12-01", "value": 298.990},
        {"date": "2023-06-01", "value": 304.003},
        {"date": "2023-12-01", "value": 308.742},
        {"date": "2024-03-01", "value": 312.230},
        {"date": "2024-06-01", "value": 314.069},
        {"date": "2024-09-01", "value": 315.301},
        {"date": "2024-12-01", "value": 316.580},
    ],
    "MORTGAGE30US": [
        {"date": "2022-01-06", "value": 3.22},
        {"date": "2022-06-23", "value": 5.81},
        {"date": "2022-10-27", "value": 7.08},
        {"date": "2023-03-09", "value": 6.73},
        {"date": "2023-07-06", "value": 6.81},
        {"date": "2023-10-26", "value": 7.79},
        {"date": "2024-01-11", "value": 6.66},
        {"date": "2024-05-02", "value": 7.22},
        {"date": "2024-09-26", "value": 6.08},
        {"date": "2024-12-19", "value": 6.72},
    ],
    "GDP": [
        {"date": "2022-01-01", "value": 25029.1},
        {"date": "2022-04-01", "value": 25544.3},
        {"date": "2022-07-01", "value": 25994.6},
        {"date": "2022-10-01", "value": 26408.4},
        {"date": "2023-01-01", "value": 26813.6},
        {"date": "2023-04-01", "value": 27063.0},
        {"date": "2023-07-01", "value": 27610.1},
        {"date": "2023-10-01", "value": 27956.9},
        {"date": "2024-01-01", "value": 28283.4},
        {"date": "2024-04-01", "value": 28629.2},
        {"date": "2024-07-01", "value": 29348.7},
    ],
    "DGS10": [
        {"date": "2023-01-03", "value": 3.79},
        {"date": "2023-07-03", "value": 3.86},
        {"date": "2023-10-19", "value": 4.98},
        {"date": "2024-01-02", "value": 3.94},
        {"date": "2024-04-25", "value": 4.70},
        {"date": "2024-09-16", "value": 3.63},
        {"date": "2024-12-31", "value": 4.57},
    ],
    "DGS2": [
        {"date": "2023-01-03", "value": 4.40},
        {"date": "2023-07-03", "value": 4.87},
        {"date": "2023-10-19", "value": 5.19},
        {"date": "2024-01-02", "value": 4.33},
        {"date": "2024-04-25", "value": 4.99},
        {"date": "2024-09-16", "value": 3.55},
        {"date": "2024-12-31", "value": 4.24},
    ],
    "T10Y2Y": [
        {"date": "2023-01-03", "value": -0.61},
        {"date": "2023-07-03", "value": -1.01},
        {"date": "2023-10-19", "value": -0.21},
        {"date": "2024-01-02", "value": -0.39},
        {"date": "2024-04-25", "value": -0.29},
        {"date": "2024-09-16", "value": 0.08},
        {"date": "2024-12-31", "value": 0.33},
    ]
}


class FredClient:
    """Async Client for Federal Reserve Economic Data (FRED) API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.FRED_API_KEY
        self.base_url = settings.FRED_BASE_URL

    @property
    def has_api_key(self) -> bool:
        """Check if an active API key is provided."""
        return bool(self.api_key and len(self.api_key.strip()) >= 20)

    async def validate_key(self) -> Dict[str, Any]:
        """Test whether the configured FRED API key is valid."""
        if not self.has_api_key:
            return {"valid": False, "message": "FRED API key is not configured"}

        url = f"{self.base_url}/series"
        params = {
            "series_id": "GDP",
            "api_key": self.api_key,
            "file_type": "json"
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    return {"valid": True, "message": "FRED API key verified successfully"}
                data = res.json()
                msg = data.get("error_message", f"HTTP {res.status_code}")
                return {"valid": False, "message": f"FRED API Error: {msg}"}
        except Exception as e:
            return {"valid": False, "message": f"Connection error: {str(e)}"}

    async def search_series(
        self,
        search_text: str,
        limit: int = 10,
        order_by: str = "search_rank",
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """Search FRED for series matching query text."""
        limit = max(1, min(limit, 50))

        if self.has_api_key:
            url = f"{self.base_url}/series/search"
            params = {
                "search_text": search_text,
                "api_key": self.api_key,
                "file_type": "json",
                "limit": limit,
                "order_by": order_by,
                "sort_order": sort_order
            }
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    res = await client.get(url, params=params)
                    if res.status_code == 200:
                        data = res.json()
                        seriess = data.get("seriess", [])
                        return [
                            {
                                "id": s.get("id"),
                                "title": s.get("title"),
                                "frequency": s.get("frequency"),
                                "units": s.get("units"),
                                "seasonal_adjustment": s.get("seasonal_adjustment"),
                                "observation_start": s.get("observation_start"),
                                "observation_end": s.get("observation_end"),
                                "popularity": s.get("popularity"),
                                "notes": (s.get("notes") or "")[:200]
                            }
                            for s in seriess
                        ]
                    logger.warning("FRED search API returned status %s: %s", res.status_code, res.text)
            except Exception as e:
                logger.warning("FRED live search failed, falling back to curated list: %s", e)

        # Fallback to searching curated local series
        q = search_text.lower().strip()
        matches = []
        for sid, info in POPULAR_SERIES.items():
            combined = f"{sid} {info['title']} {info['category']} {info['notes']}".lower()
            if any(term in combined for term in q.split()):
                matches.append({
                    "id": sid,
                    "title": info["title"],
                    "frequency": info["frequency"],
                    "units": info["units"],
                    "seasonal_adjustment": info["seasonal_adjustment"],
                    "observation_start": "2020-01-01",
                    "observation_end": "2024-12-31",
                    "popularity": 90,
                    "notes": info["notes"]
                })
        
        # If no specific match found, return top popular indicators
        if not matches:
            matches = [
                {
                    "id": sid,
                    "title": info["title"],
                    "frequency": info["frequency"],
                    "units": info["units"],
                    "seasonal_adjustment": info["seasonal_adjustment"],
                    "observation_start": "2020-01-01",
                    "observation_end": "2024-12-31",
                    "popularity": 85,
                    "notes": info["notes"]
                }
                for sid, info in list(POPULAR_SERIES.items())[:limit]
            ]
        return matches[:limit]

    async def get_series_observations(
        self,
        series_id: str,
        observation_start: Optional[str] = None,
        observation_end: Optional[str] = None,
        frequency: Optional[str] = None,
        units: Optional[str] = None,
        limit: int = 100,
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """Fetch historical observations for a specific series ID."""
        series_id_clean = series_id.upper().strip()
        limit = max(1, min(limit, 500))

        if self.has_api_key:
            url = f"{self.base_url}/series/observations"
            params: Dict[str, Any] = {
                "series_id": series_id_clean,
                "api_key": self.api_key,
                "file_type": "json",
                "limit": limit,
                "sort_order": sort_order
            }
            if observation_start:
                params["observation_start"] = observation_start
            if observation_end:
                params["observation_end"] = observation_end
            if frequency:
                params["frequency"] = frequency.lower()
            if units:
                params["units"] = units.lower()

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.get(url, params=params)
                    if res.status_code == 200:
                        data = res.json()
                        raw_obs = data.get("observations", [])
                        clean_obs = []
                        for item in raw_obs:
                            val = item.get("value")
                            # FRED uses '.' to denote missing observations
                            if val not in (None, ".", "", "NaN", "null"):
                                try:
                                    clean_obs.append({
                                        "date": item.get("date"),
                                        "value": float(val)
                                    })
                                except ValueError:
                                    continue
                        
                        meta = await self.get_series_metadata(series_id_clean)
                        return {
                            "series_id": series_id_clean,
                            "title": meta.get("title", series_id_clean),
                            "units": meta.get("units", ""),
                            "frequency": meta.get("frequency", ""),
                            "count": len(clean_obs),
                            "observations": clean_obs,
                            "is_demo": False
                        }
                    logger.warning("FRED observations returned status %s", res.status_code)
            except Exception as e:
                logger.warning("FRED live observations failed, falling back to demo: %s", e)

        # Demo / Offline fallback observations
        meta = POPULAR_SERIES.get(series_id_clean, {
            "title": f"Series {series_id_clean}",
            "units": "Index / Rate",
            "frequency": "Monthly"
        })
        sample = SAMPLE_OBSERVATIONS.get(series_id_clean)
        if not sample:
            # Generate plausible generic observations if not in sample dict
            sample = [
                {"date": "2023-01-01", "value": 100.0},
                {"date": "2023-04-01", "value": 101.5},
                {"date": "2023-07-01", "value": 102.8},
                {"date": "2023-10-01", "value": 103.4},
                {"date": "2024-01-01", "value": 104.1},
                {"date": "2024-04-01", "value": 105.2},
                {"date": "2024-07-01", "value": 106.0},
                {"date": "2024-10-01", "value": 106.8},
            ]

        # Apply date filters if supplied
        filtered = sample
        if observation_start:
            filtered = [o for o in filtered if o["date"] >= observation_start]
        if observation_end:
            filtered = [o for o in filtered if o["date"] <= observation_end]
        
        if sort_order == "desc":
            filtered = list(reversed(filtered))

        return {
            "series_id": series_id_clean,
            "title": meta.get("title", series_id_clean),
            "units": meta.get("units", ""),
            "frequency": meta.get("frequency", ""),
            "count": len(filtered[:limit]),
            "observations": filtered[:limit],
            "is_demo": True
        }

    async def get_series_metadata(self, series_id: str) -> Dict[str, Any]:
        """Fetch descriptive metadata for a specific series."""
        series_id_clean = series_id.upper().strip()

        if self.has_api_key:
            url = f"{self.base_url}/series"
            params = {
                "series_id": series_id_clean,
                "api_key": self.api_key,
                "file_type": "json"
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.get(url, params=params)
                    if res.status_code == 200:
                        data = res.json()
                        seriess = data.get("seriess", [])
                        if seriess:
                            s = seriess[0]
                            return {
                                "id": s.get("id"),
                                "title": s.get("title"),
                                "units": s.get("units"),
                                "frequency": s.get("frequency"),
                                "seasonal_adjustment": s.get("seasonal_adjustment"),
                                "last_updated": s.get("last_updated"),
                                "notes": s.get("notes", "")
                            }
            except Exception as e:
                logger.warning("FRED metadata live call failed: %s", e)

        # Curated fallback
        if series_id_clean in POPULAR_SERIES:
            p = POPULAR_SERIES[series_id_clean]
            return {
                "id": series_id_clean,
                "title": p["title"],
                "units": p["units"],
                "frequency": p["frequency"],
                "seasonal_adjustment": p["seasonal_adjustment"],
                "last_updated": "2024-12-01",
                "notes": p["notes"]
            }

        return {
            "id": series_id_clean,
            "title": f"Economic Series {series_id_clean}",
            "units": "Units",
            "frequency": "Monthly",
            "seasonal_adjustment": "Seasonally Adjusted",
            "last_updated": "2024-01-01",
            "notes": ""
        }
