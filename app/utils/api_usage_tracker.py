"""
API Usage Tracker

Tracks API calls, costs, and usage patterns for:
- Replicate (centralized AI hub - all models)
- Including text generation, image generation, video, and more

Features:
- Real-time cost tracking
- Usage history with charts
- Budget alerts
- Cost optimization suggestions
"""

import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import threading
import logging

logger = logging.getLogger(__name__)

# Cost estimates per API (as of Dec 2024)
API_COSTS = {
    "replicate": {
        # Image models (per image)
        "black-forest-labs/flux-schnell": 0.003,
        "black-forest-labs/flux-dev": 0.025,
        "black-forest-labs/flux-1.1-pro": 0.04,
        "black-forest-labs/flux-kontext-pro": 0.04,
        "stability-ai/sdxl": 0.01,
        "stability-ai/stable-diffusion-3": 0.035,
        "playgroundai/playground-v2.5-1024px-aesthetic": 0.01,
        
        # Video models (per second of video)
        "minimax/video-01": 0.25,
        "luma/ray": 0.20,
        "stability-ai/stable-video-diffusion": 0.15,
        "fofr/kling-v1.6-pro": 0.30,
        "openai/sora-2": 0.50,  # Via Replicate
        
        # Text generation (via Replicate - all models)
        "openai/gpt-4.1": 0.01,  # Via Replicate
        "openai/gpt-4.1-nano": 0.005,  # Via Replicate
        "meta/llama-2-70b": 0.01,  # Via Replicate
        "mistralai/mistral-7b-instruct": 0.005,  # Via Replicate
        
        # Editing models
        "nightmareai/real-esrgan": 0.005,
        "philz1337x/clarity-upscaler": 0.02,
        "cjwbw/rembg": 0.002,
        "timothybrooks/instruct-pix2pix": 0.01,
        
        # Audio models
        "meta/musicgen": 0.02,
        "lucataco/xtts-v2": 0.01,
        "suno/bark": 0.015,
        
        # Default for unknown models
        "_default": 0.01,
    },
}


@dataclass
class APICall:
    """Record of a single API call"""
    timestamp: str
    provider: str
    model: str
    endpoint: str = ""
    cost: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0
    success: bool = True
    error: str = ""
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'APICall':
        return cls(**data)


@dataclass
class UsageSummary:
    """Summary of API usage"""
    total_calls: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    avg_latency_ms: float = 0.0
    calls_by_provider: Dict[str, int] = field(default_factory=dict)
    cost_by_provider: Dict[str, float] = field(default_factory=dict)
    calls_by_model: Dict[str, int] = field(default_factory=dict)
    cost_by_model: Dict[str, float] = field(default_factory=dict)


class APIUsageTracker:
    """
    Tracks and persists API usage across sessions.
    Thread-safe for concurrent access.
    """
    
    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path or os.path.expanduser("~/.printify_api_usage"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.calls: List[APICall] = []
        self.session_start = datetime.now()
        self._lock = threading.Lock()
        
        # Budget settings
        self.daily_budget = float(os.getenv("API_DAILY_BUDGET", "10.0"))
        self.monthly_budget = float(os.getenv("API_MONTHLY_BUDGET", "100.0"))
        self.alert_threshold = 0.8  # Alert at 80% of budget
        
        # Load historical data
        self._load_history()
    
    def _get_history_file(self, date: datetime = None) -> Path:
        """Get the history file for a specific date"""
        date = date or datetime.now()
        return self.storage_path / f"usage_{date.strftime('%Y_%m')}.json"
    
    def _load_history(self):
        """Load historical usage data"""
        try:
            history_file = self._get_history_file()
            if history_file.exists():
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self.calls = [APICall.from_dict(c) for c in data.get('calls', [])]
        except Exception as e:
            logger.warning(f"Could not load usage history: {e}")
            self.calls = []
    
    def _save_history(self):
        """Save usage data to disk"""
        try:
            history_file = self._get_history_file()
            with open(history_file, 'w') as f:
                json.dump({
                    'calls': [c.to_dict() for c in self.calls],
                    'last_updated': datetime.now().isoformat(),
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save usage history: {e}")
    
    def track_call(
        self,
        provider: str,
        model: str,
        endpoint: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        duration_ms: int = 0,
        success: bool = True,
        error: str = "",
        metadata: Dict = None
    ) -> APICall:
        """
        Track an API call.
        
        Args:
            provider: API provider (replicate, openai, anthropic, etc.)
            model: Model used
            endpoint: API endpoint called
            tokens_in: Input tokens (for LLMs)
            tokens_out: Output tokens (for LLMs)
            duration_ms: Call duration in milliseconds
            success: Whether the call succeeded
            error: Error message if failed
            metadata: Additional metadata
        
        Returns:
            The tracked APICall object
        """
        cost = self._estimate_cost(provider, model, tokens_in, tokens_out)
        
        call = APICall(
            timestamp=datetime.now().isoformat(),
            provider=provider,
            model=model,
            endpoint=endpoint,
            cost=cost,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=metadata or {}
        )
        
        with self._lock:
            self.calls.append(call)
            # Save every 10 calls
            if len(self.calls) % 10 == 0:
                self._save_history()
        
        return call
    
    def _estimate_cost(self, provider: str, model: str, tokens_in: int, tokens_out: int) -> float:
        """Estimate the cost of an API call"""
        provider_costs = API_COSTS.get(provider, {})
        
        # Try exact model match
        model_cost = provider_costs.get(model)
        
        # Try partial match
        if model_cost is None:
            for known_model, cost in provider_costs.items():
                if known_model in model or model in known_model:
                    model_cost = cost
                    break
        
        # Use default
        if model_cost is None:
            model_cost = provider_costs.get("_default", 0.01)
        
        # Calculate based on type
        if isinstance(model_cost, dict):
            # Token-based pricing (LLMs)
            input_cost = (tokens_in / 1000) * model_cost.get("input", 0)
            output_cost = (tokens_out / 1000) * model_cost.get("output", 0)
            return input_cost + output_cost
        else:
            # Flat rate (image/video models)
            return model_cost
    
    def get_summary(self, period: str = "day") -> UsageSummary:
        """
        Get usage summary for a time period.
        
        Args:
            period: "hour", "day", "week", "month", "all"
        """
        now = datetime.now()
        
        if period == "hour":
            cutoff = now - timedelta(hours=1)
        elif period == "day":
            cutoff = now - timedelta(days=1)
        elif period == "week":
            cutoff = now - timedelta(weeks=1)
        elif period == "month":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = datetime.min
        
        with self._lock:
            filtered_calls = [
                c for c in self.calls 
                if datetime.fromisoformat(c.timestamp) > cutoff
            ]
        
        summary = UsageSummary()
        summary.total_calls = len(filtered_calls)
        
        total_latency = 0
        
        for call in filtered_calls:
            summary.total_cost += call.cost
            summary.total_tokens += call.tokens_in + call.tokens_out
            
            if call.success:
                summary.successful_calls += 1
            else:
                summary.failed_calls += 1
            
            total_latency += call.duration_ms
            
            # By provider
            summary.calls_by_provider[call.provider] = \
                summary.calls_by_provider.get(call.provider, 0) + 1
            summary.cost_by_provider[call.provider] = \
                summary.cost_by_provider.get(call.provider, 0) + call.cost
            
            # By model
            summary.calls_by_model[call.model] = \
                summary.calls_by_model.get(call.model, 0) + 1
            summary.cost_by_model[call.model] = \
                summary.cost_by_model.get(call.model, 0) + call.cost
        
        if summary.total_calls > 0:
            summary.avg_latency_ms = total_latency / summary.total_calls
        
        return summary
    
    def get_recent_calls(self, limit: int = 50) -> List[APICall]:
        """Get the most recent API calls"""
        with self._lock:
            return list(reversed(self.calls[-limit:]))
    
    def get_cost_today(self) -> float:
        """Get total cost for today"""
        summary = self.get_summary("day")
        return summary.total_cost
    
    def get_cost_this_month(self) -> float:
        """Get total cost for this month"""
        summary = self.get_summary("month")
        return summary.total_cost
    
    def check_budget(self) -> Dict[str, Any]:
        """Check current budget status"""
        daily_cost = self.get_cost_today()
        monthly_cost = self.get_cost_this_month()
        
        return {
            "daily": {
                "spent": daily_cost,
                "budget": self.daily_budget,
                "remaining": max(0, self.daily_budget - daily_cost),
                "percent_used": (daily_cost / self.daily_budget * 100) if self.daily_budget > 0 else 0,
                "over_budget": daily_cost > self.daily_budget,
                "near_limit": daily_cost > self.daily_budget * self.alert_threshold,
            },
            "monthly": {
                "spent": monthly_cost,
                "budget": self.monthly_budget,
                "remaining": max(0, self.monthly_budget - monthly_cost),
                "percent_used": (monthly_cost / self.monthly_budget * 100) if self.monthly_budget > 0 else 0,
                "over_budget": monthly_cost > self.monthly_budget,
                "near_limit": monthly_cost > self.monthly_budget * self.alert_threshold,
            }
        }
    
    def get_hourly_usage(self, hours: int = 24) -> List[Dict]:
        """Get usage broken down by hour"""
        now = datetime.now()
        hourly = defaultdict(lambda: {"calls": 0, "cost": 0.0})
        
        with self._lock:
            for call in self.calls:
                call_time = datetime.fromisoformat(call.timestamp)
                if call_time > now - timedelta(hours=hours):
                    hour_key = call_time.strftime("%Y-%m-%d %H:00")
                    hourly[hour_key]["calls"] += 1
                    hourly[hour_key]["cost"] += call.cost
        
        # Fill in missing hours
        result = []
        for i in range(hours):
            hour = now - timedelta(hours=hours - 1 - i)
            hour_key = hour.strftime("%Y-%m-%d %H:00")
            result.append({
                "hour": hour_key,
                "display": hour.strftime("%H:%M"),
                "calls": hourly[hour_key]["calls"],
                "cost": hourly[hour_key]["cost"]
            })
        
        return result
    
    def get_model_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get most used models"""
        summary = self.get_summary("month")
        
        models = []
        for model, calls in summary.calls_by_model.items():
            models.append({
                "model": model.split("/")[-1] if "/" in model else model,
                "full_model": model,
                "calls": calls,
                "cost": summary.cost_by_model.get(model, 0)
            })
        
        models.sort(key=lambda x: x["cost"], reverse=True)
        return models[:limit]
    
    def get_optimization_suggestions(self) -> List[str]:
        """Generate cost optimization suggestions"""
        suggestions = []
        summary = self.get_summary("week")
        
        # Check for expensive model usage
        for model, cost in summary.cost_by_model.items():
            if cost > 5.0:  # More than $5/week on one model
                model_name = model.split("/")[-1] if "/" in model else model
                if "flux-1.1-pro" in model or "flux-pro" in model:
                    suggestions.append(f"💡 You spent ${cost:.2f} on {model_name}. Consider flux-schnell for drafts (90% cheaper).")
                if "gpt-4o" in model and "mini" not in model:
                    suggestions.append(f"💡 You spent ${cost:.2f} on GPT-4o. Try GPT-4o-mini for simple tasks (97% cheaper).")
                if "claude-3-opus" in model:
                    suggestions.append(f"💡 You spent ${cost:.2f} on Claude Opus. Sonnet handles most tasks at 80% lower cost.")
        
        # Check for high failure rate
        if summary.total_calls > 10:
            failure_rate = summary.failed_calls / summary.total_calls
            if failure_rate > 0.1:
                suggestions.append(f"⚠️ {failure_rate*100:.0f}% of API calls failed. Check your prompts and error logs.")
        
        # Check for inefficient patterns
        if summary.total_tokens > 100000:
            suggestions.append("📊 High token usage detected. Consider summarizing inputs before API calls.")
        
        if not suggestions:
            suggestions.append("✅ Your API usage looks efficient! No optimization suggestions.")
        
        return suggestions
    
    def export_usage(self, format: str = "json") -> str:
        """Export usage data"""
        if format == "json":
            return json.dumps({
                "calls": [c.to_dict() for c in self.calls],
                "summary": asdict(self.get_summary("all")),
                "exported_at": datetime.now().isoformat()
            }, indent=2)
        elif format == "csv":
            lines = ["timestamp,provider,model,cost,tokens_in,tokens_out,duration_ms,success"]
            for call in self.calls:
                lines.append(f"{call.timestamp},{call.provider},{call.model},{call.cost},{call.tokens_in},{call.tokens_out},{call.duration_ms},{call.success}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def clear_history(self, before_date: datetime = None):
        """Clear usage history"""
        with self._lock:
            if before_date:
                self.calls = [
                    c for c in self.calls 
                    if datetime.fromisoformat(c.timestamp) > before_date
                ]
            else:
                self.calls = []
            self._save_history()


# Global tracker instance
_tracker: Optional[APIUsageTracker] = None


def get_tracker() -> APIUsageTracker:
    """Get the global tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = APIUsageTracker()
    return _tracker


def track_api_call(provider: str, model: str, **kwargs) -> APICall:
    """Convenience function to track an API call"""
    return get_tracker().track_call(provider, model, **kwargs)


# Decorator for automatic tracking
def track_replicate(model: str):
    """Decorator to automatically track Replicate API calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            success = True
            error = ""
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = int((time.time() - start) * 1000)
                track_api_call(
                    provider="replicate",
                    model=model,
                    duration_ms=duration_ms,
                    success=success,
                    error=error
                )
        return wrapper
    return decorator


# All text generation now routes through Replicate
# Use track_replicate decorator instead


# Streamlit UI components
def render_usage_dashboard():
    """Render the API usage dashboard in Streamlit"""
    import streamlit as st
    
    tracker = get_tracker()
    budget = tracker.check_budget()
    
    st.markdown("### 📊 API Usage Dashboard")
    
    # Budget overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        daily = budget["daily"]
        color = "🔴" if daily["over_budget"] else "🟡" if daily["near_limit"] else "🟢"
        st.metric(
            f"{color} Today",
            f"${daily['spent']:.2f}",
            f"${daily['remaining']:.2f} left"
        )
    
    with col2:
        monthly = budget["monthly"]
        color = "🔴" if monthly["over_budget"] else "🟡" if monthly["near_limit"] else "🟢"
        st.metric(
            f"{color} This Month",
            f"${monthly['spent']:.2f}",
            f"${monthly['remaining']:.2f} left"
        )
    
    with col3:
        summary = tracker.get_summary("day")
        st.metric(
            "📞 Calls Today",
            summary.total_calls,
            f"{summary.successful_calls} succeeded"
        )
    
    with col4:
        if summary.total_calls > 0:
            st.metric(
                "⚡ Avg Latency",
                f"{summary.avg_latency_ms:.0f}ms",
                None
            )
        else:
            st.metric("⚡ Avg Latency", "N/A", None)
    
    # Progress bars for budgets
    st.markdown("#### 💰 Budget Status")
    
    col_d, col_m = st.columns(2)
    with col_d:
        st.caption("Daily Budget")
        st.progress(min(budget["daily"]["percent_used"] / 100, 1.0))
        st.caption(f"${budget['daily']['spent']:.2f} / ${budget['daily']['budget']:.2f}")
    
    with col_m:
        st.caption("Monthly Budget")
        st.progress(min(budget["monthly"]["percent_used"] / 100, 1.0))
        st.caption(f"${budget['monthly']['spent']:.2f} / ${budget['monthly']['budget']:.2f}")
    
    # Usage by provider
    st.markdown("#### 📈 Usage by Provider")
    summary_week = tracker.get_summary("week")
    
    if summary_week.cost_by_provider:
        provider_cols = st.columns(len(summary_week.cost_by_provider))
        for idx, (provider, cost) in enumerate(sorted(summary_week.cost_by_provider.items(), key=lambda x: -x[1])):
            with provider_cols[idx % len(provider_cols)]:
                calls = summary_week.calls_by_provider.get(provider, 0)
                st.metric(
                    provider.title(),
                    f"${cost:.2f}",
                    f"{calls} calls"
                )
    else:
        st.info("No API calls recorded yet this week")
    
    # Top models
    st.markdown("#### 🏆 Top Models (by cost)")
    leaderboard = tracker.get_model_leaderboard(5)
    
    if leaderboard:
        for i, model in enumerate(leaderboard, 1):
            col_rank, col_name, col_stats = st.columns([1, 4, 2])
            with col_rank:
                st.markdown(f"**#{i}**")
            with col_name:
                st.markdown(f"`{model['model']}`")
            with col_stats:
                st.markdown(f"${model['cost']:.2f} ({model['calls']} calls)")
    else:
        st.info("No model usage recorded yet")
    
    # Optimization suggestions
    st.markdown("#### 💡 Optimization Suggestions")
    suggestions = tracker.get_optimization_suggestions()
    for suggestion in suggestions:
        st.markdown(suggestion)
    
    # Hourly chart
    with st.expander("📊 Hourly Usage (Last 24h)"):
        hourly = tracker.get_hourly_usage(24)
        
        if any(h["calls"] > 0 for h in hourly):
            import pandas as pd
            df = pd.DataFrame(hourly)
            
            tab_calls, tab_cost = st.tabs(["Calls", "Cost"])
            with tab_calls:
                st.bar_chart(df.set_index("display")["calls"])
            with tab_cost:
                st.bar_chart(df.set_index("display")["cost"])
        else:
            st.info("No usage data in the last 24 hours")
    
    # Recent calls
    with st.expander("📜 Recent API Calls"):
        recent = tracker.get_recent_calls(20)
        
        if recent:
            for call in recent:
                status = "✅" if call.success else "❌"
                time_str = datetime.fromisoformat(call.timestamp).strftime("%H:%M:%S")
                model_short = call.model.split("/")[-1] if "/" in call.model else call.model
                
                st.markdown(
                    f"{status} `{time_str}` **{call.provider}**/{model_short} "
                    f"- ${call.cost:.4f} ({call.duration_ms}ms)"
                )
        else:
            st.info("No recent API calls")
    
    # Settings
    with st.expander("⚙️ Budget Settings"):
        col_daily, col_monthly = st.columns(2)
        
        with col_daily:
            new_daily = st.number_input(
                "Daily Budget ($)",
                min_value=0.0,
                value=tracker.daily_budget,
                step=1.0,
                key="budget_daily_input"
            )
            if new_daily != tracker.daily_budget:
                tracker.daily_budget = new_daily
        
        with col_monthly:
            new_monthly = st.number_input(
                "Monthly Budget ($)",
                min_value=0.0,
                value=tracker.monthly_budget,
                step=10.0,
                key="budget_monthly_input"
            )
            if new_monthly != tracker.monthly_budget:
                tracker.monthly_budget = new_monthly
        
        col_export, col_clear = st.columns(2)
        
        with col_export:
            if st.button("📥 Export Usage Data", key="export_usage_btn"):
                csv_data = tracker.export_usage("csv")
                st.download_button(
                    "Download CSV",
                    csv_data,
                    "api_usage.csv",
                    "text/csv",
                    key="download_usage_csv"
                )
        
        with col_clear:
            if st.button("🗑️ Clear History", key="clear_usage_btn"):
                if st.checkbox("Confirm clear all history", key="confirm_clear_usage"):
                    tracker.clear_history()
                    st.success("History cleared!")
                    st.rerun()


def render_usage_badge():
    """Render a compact usage badge for the sidebar"""
    import streamlit as st
    
    tracker = get_tracker()
    budget = tracker.check_budget()
    daily = budget["daily"]
    
    color = "🔴" if daily["over_budget"] else "🟡" if daily["near_limit"] else "🟢"
    
    st.markdown(f"""
    <div style="padding: 8px; background: rgba(0,0,0,0.1); border-radius: 8px; margin: 8px 0;">
        <div style="font-size: 12px; color: #888;">API Usage Today</div>
        <div style="font-size: 18px; font-weight: bold;">{color} ${daily['spent']:.2f}</div>
        <div style="font-size: 11px; color: #666;">${daily['remaining']:.2f} remaining</div>
    </div>
    """, unsafe_allow_html=True)
