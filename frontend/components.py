import streamlit as st
import plotly.graph_objects as go
from frontend.utils import (
    RECOMMENDATION_COLORS, 
    RECOMMENDATION_ICONS, 
    format_number, 
    format_pct
)


def render_degraded_alert(confidence_score: float, errors: list):
    """Render degraded state alert banner when confidence < 1.0."""
    if confidence_score >= 1.0:
        return
    
    severity = "error" if confidence_score < 0.5 else "warning"
    
    if severity == "error":
        st.error(
            f"⚠️ **Degraded State Detected** — Confidence Score: {confidence_score:.2f}/1.0\n\n"
            f"The pipeline encountered issues that may affect result reliability. "
            f"Review the error log below for details.",
            icon="🚨"
        )
    else:
        st.warning(
            f"⚠️ **Partial Data** — Confidence Score: {confidence_score:.2f}/1.0\n\n"
            f"Some data sources were unavailable or degraded. Results may be incomplete.",
            icon="⚠️"
        )
    
    # Show error summary
    if errors:
        with st.expander(f"🔍 Error Details ({len(errors)} issues)", expanded=False):
            for i, err in enumerate(errors, 1):
                st.text(f"{i}. {err}")


def render_metrics_row(financial_data: dict):
    """Render the 4 core financial metrics in a row."""
    col1, col2, col3, col4 = st.columns(4)
    
    metrics = [
        ("P/E Ratio", financial_data.get("pe_ratio"), None, 2, ""),
        ("YoY Revenue Growth", financial_data.get("yoy_revenue_growth"), "%", 2, ""),
        ("Debt-to-Equity", financial_data.get("debt_to_equity"), None, 2, ""),
        ("Current Ratio", financial_data.get("current_ratio"), None, 2, ""),
    ]
    
    for col, (label, value, suffix, decimals, prefix) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.metric(
                label=label,
                value=format_number(value, prefix=prefix, suffix=suffix, decimals=decimals),
                delta=None,
                delta_color="off"
            )


def render_extended_metrics(financial_data: dict):
    """Render additional financial metrics."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Market Cap",
            format_number(financial_data.get("market_cap"), prefix="$"),
        )
    with col2:
        st.metric(
            "Revenue",
            format_number(financial_data.get("revenue"), prefix="$"),
        )
    with col3:
        st.metric(
            "Cash Position",
            format_number(financial_data.get("cash_position"), prefix="$"),
        )


def render_risk_gauge(risk_score: float):
    """Render a gauge chart for risk score (0-100)."""
    # Determine color based on score
    if risk_score <= 20:
        color = "#00C851"  # Green
        level = "Low"
    elif risk_score <= 45:
        color = "#33B5E5"  # Blue
        level = "Moderate"
    elif risk_score <= 70:
        color = "#FFBB33"  # Amber
        level = "Elevated"
    else:
        color = "#FF4444"  # Red
        level = "High"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=risk_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Risk Score", 'font': {'size': 20}},
        delta={'reference': 50, 'increasing': {'color': "#FF4444"}, 'decreasing': {'color': "#00C851"}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkgray"},
            'bar': {'color': color, 'thickness': 0.3},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 20], 'color': 'rgba(0, 200, 81, 0.2)'},
                {'range': [20, 45], 'color': 'rgba(51, 181, 229, 0.2)'},
                {'range': [45, 70], 'color': 'rgba(255, 187, 51, 0.2)'},
                {'range': [70, 100], 'color': 'rgba(255, 68, 68, 0.2)'},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        font={'color': "black", 'family': "Arial"}
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Risk level label
    st.markdown(
        f"<div style='text-align: center; font-size: 1.2rem; font-weight: bold; "
        f"color: {color};'>{level} Risk</div>",
        unsafe_allow_html=True
    )


def render_recommendation_badge(recommendation: str):
    """Render the analyst recommendation as a styled badge."""
    color = RECOMMENDATION_COLORS.get(recommendation, "#888888")
    icon = RECOMMENDATION_ICONS.get(recommendation, "⚪")
    
    st.markdown(
        f"""
        <div style='
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background-color: {color};
            color: white;
            border-radius: 8px;
            font-size: 1.25rem;
            font-weight: 600;
            text-align: center;
            width: 100%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        '>
            {icon} {recommendation}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_synthesis_sections(synthesis_report: dict):
    """Render the 6-section synthesis brief."""
    sections = [
        ("📊 Company Snapshot", "company_snapshot"),
        ("💰 Financial Health", "financial_health"),
        ("📰 Market Sentiment", "market_sentiment"),
        ("⚠️ Risk Assessment", "risk_assessment"),
        ("🔑 Key Concerns", "key_concerns"),
    ]
    
    for title, key in sections:
        with st.expander(title, expanded=True):
            content = synthesis_report.get(key, "")
            if isinstance(content, list):
                for item in content:
                    st.markdown(f"• {item}")
            else:
                st.write(content)
    
    # Recommendation is rendered separately with badge
    st.markdown("---")
    st.subheader("🎯 Analyst Recommendation")
    render_recommendation_badge(synthesis_report.get("analyst_recommendation", "Neutral"))


def render_error_log(errors: list):
    """Render the full error log."""
    if not errors:
        st.success("✅ No errors recorded")
        return
    
    st.error(f"❌ {len(errors)} Error(s) Recorded")
    for i, err in enumerate(errors, 1):
        st.text(f"{i}. {err}")


def render_confidence_indicator(confidence_score: float):
    """Render a confidence score indicator."""
    if confidence_score >= 0.9:
        color = "#00C851"
        label = "High Confidence"
    elif confidence_score >= 0.7:
        color = "#33B5E5"
        label = "Good Confidence"
    elif confidence_score >= 0.5:
        color = "#FFBB33"
        label = "Moderate Confidence"
    else:
        color = "#FF4444"
        label = "Low Confidence"
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress(confidence_score)
    with col2:
        st.markdown(
            f"<div style='text-align: right; color: {color}; font-weight: bold;'>"
            f"{confidence_score:.0%}</div>",
            unsafe_allow_html=True
        )
    st.caption(f"{label} ({confidence_score:.2f}/1.0)")


def render_pipeline_status(data: dict):
    """Render a compact pipeline status overview."""
    st.subheader("📈 Pipeline Status")
    
    cols = st.columns(4)
    
    # Financial data status
    with cols[0]:
        fd = data.get("financial_data", {})
        available = fd.get("data_available", False)
        st.metric(
            "Financial Data",
            "✅ Available" if available else "❌ Unavailable",
            delta=None
        )
    
    # News data status
    with cols[1]:
        nd = data.get("news_data", {})
        available = nd.get("news_available", False)
        st.metric(
            "News Data",
            "✅ Available" if available else "❌ Unavailable",
            delta=None
        )
    
    # Risk data status
    with cols[2]:
        rd = data.get("risk_data", {})
        has_score = "risk_score" in rd
        st.metric(
            "Risk Analysis",
            "✅ Complete" if has_score else "❌ Missing",
            delta=None
        )
    
    # Synthesis status
    with cols[3]:
        sr = data.get("synthesis_report", {})
        has_rec = "analyst_recommendation" in sr
        st.metric(
            "Synthesis",
            "✅ Complete" if has_rec else "❌ Missing",
            delta=None
        )