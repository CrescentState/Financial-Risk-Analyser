import streamlit as st
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.utils import (
    analyze_ticker, 
    check_health, 
    format_number, 
    format_pct,
    API_BASE_URL
)
from frontend.components import (
    render_degraded_alert,
    render_metrics_row,
    render_extended_metrics,
    render_risk_gauge,
    render_recommendation_badge,
    render_synthesis_sections,
    render_error_log,
    render_confidence_indicator,
    render_pipeline_status,
)


# Page configuration
st.set_page_config(
    page_title="Chrimatos Financial Risk Analyser",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6B7280;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1F2937;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #E5E7EB;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stAlert > div {
        padding: 1rem;
    }
    .stExpander > div > div > div > div {
        padding: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Sidebar
    with st.sidebar:
        st.markdown("### 📊 Chrimatos")
        st.caption("Financial Risk Analyser")
        st.markdown("---")
        
        # Health check
        if check_health():
            st.success("🟢 Backend Connected")
        else:
            st.error("🔴 Backend Disconnected")
            st.caption(f"API: {API_BASE_URL}")
        
        st.markdown("---")
        
        # Input form
        st.markdown("### Analyze Ticker")
        ticker = st.text_input(
            "Enter ticker symbol",
            value="AAPL",
            placeholder="e.g., AAPL, TSLA, MSFT",
            help="US-listed equity ticker symbol"
        ).strip().upper()
        
        analyze_btn = st.button(
            "🔍 Analyze",
            type="primary",
            use_container_width=True,
            disabled=not ticker
        )
        
        st.markdown("---")
        st.caption("Built with LangGraph + FastAPI + Streamlit")
        st.caption("v0.1.0")
    
    # Main content
    st.markdown('<div class="main-header">Chrimatos Financial Risk Analyser</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Autonomous multi-agent due-diligence pipeline for US equities</div>', unsafe_allow_html=True)
    
    # Session state for results
    if "results" not in st.session_state:
        st.session_state.results = None
    if "last_ticker" not in st.session_state:
        st.session_state.last_ticker = ""
    
    # Run analysis
    if analyze_btn and ticker:
        with st.spinner(f"Running 4-agent pipeline for {ticker}..."):
            result = analyze_ticker(ticker)
            if result:
                st.session_state.results = result
                st.session_state.last_ticker = ticker
                st.success(f"Analysis complete for {ticker}")
            else:
                st.session_state.results = None
    
    # Display results
    if st.session_state.results:
        data = st.session_state.results
        
        # Degraded state alert
        render_degraded_alert(data.get("confidence_score", 1.0), data.get("errors", []))
        
        # Header row: Ticker + Confidence + Recommendation
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            st.markdown(f"### {data.get('ticker', 'N/A')} — {data.get('company_name', 'Unknown')}")
        with col2:
            render_confidence_indicator(data.get("confidence_score", 1.0))
        with col3:
            render_recommendation_badge(data.get("synthesis_report", {}).get("analyst_recommendation", "Neutral"))
        
        st.markdown("---")
        
        # Pipeline status
        render_pipeline_status(data)
        st.markdown("---")
        
        # Main content tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Financial Metrics",
            "⚠️ Risk Analysis", 
            "📰 News & Sentiment",
            "📋 Synthesis Brief",
            "🔍 Debug / Raw Data"
        ])
        
        with tab1:
            st.markdown('<div class="section-header">Core Financial Metrics</div>', unsafe_allow_html=True)
            render_metrics_row(data.get("financial_data", {}))
            st.markdown("")
            render_extended_metrics(data.get("financial_data", {}))
            
            # Data availability
            fd = data.get("financial_data", {})
            if not fd.get("data_available", False):
                st.warning("⚠️ Financial data incomplete — some fields unavailable")
            
            # Show raw financial data
            with st.expander("🔍 Raw Financial Data"):
                st.json(fd)
        
        with tab2:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown('<div class="section-header">Risk Score</div>', unsafe_allow_html=True)
                render_risk_gauge(data.get("risk_data", {}).get("risk_score", 0))
            
            with col2:
                st.markdown('<div class="section-header">Risk Factors</div>', unsafe_allow_html=True)
                risk_factors = data.get("risk_data", {}).get("risk_factors", [])
                if risk_factors:
                    for factor in risk_factors:
                        st.markdown(f"• {factor}")
                else:
                    st.info("No risk factors triggered")
            
            st.markdown('<div class="section-header">Risk Narrative</div>', unsafe_allow_html=True)
            narrative = data.get("risk_data", {}).get("risk_narrative", "No narrative available")
            st.write(narrative)
            
            with st.expander("🔍 Raw Risk Data"):
                st.json(data.get("risk_data", {}))
        
        with tab3:
            nd = data.get("news_data", {})
            
            if nd.get("news_available"):
                st.metric("Sentiment Score", f"{nd.get('sentiment_score', 0):.2f}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown('<div class="section-header">Key Events</div>', unsafe_allow_html=True)
                    for event in nd.get("key_events", []):
                        st.markdown(f"• {event}")
                
                with col2:
                    st.markdown('<div class="section-header">Red Flags</div>', unsafe_allow_html=True)
                    for flag in nd.get("red_flags", []):
                        st.markdown(f"🚩 {flag}")
                
                st.markdown('<div class="section-header">Summary</div>', unsafe_allow_html=True)
                st.write(nd.get("summary", "No summary available"))
            else:
                st.warning("⚠️ News data unavailable")
                if nd.get("sentiment_score") is not None:
                    st.metric("Sentiment Score", f"{nd.get('sentiment_score', 0):.2f} (fallback)")
            
            with st.expander("🔍 Raw News Data"):
                st.json(nd)
        
        with tab4:
            st.markdown('<div class="section-header">Investment Brief</div>', unsafe_allow_html=True)
            render_synthesis_sections(data.get("synthesis_report", {}))
        
        with tab5:
            st.markdown('<div class="section-header">Full Pipeline State</div>', unsafe_allow_html=True)
            st.json(data)
            
            st.markdown('<div class="section-header">Error Log</div>', unsafe_allow_html=True)
            render_error_log(data.get("errors", []))
    
    else:
        # Landing state
        st.info("👈 Enter a ticker symbol in the sidebar and click **Analyze** to begin")
        
        # Show example output
        with st.expander("📖 Example Output (AAPL)"):
            st.markdown("""
            **Financial Metrics:** P/E Ratio, YoY Revenue Growth, Debt-to-Equity, Current Ratio, Market Cap, Revenue, Cash Position
            
            **Risk Analysis:** Deterministic risk score (0-100) with factor breakdown and narrative
            
            **News Sentiment:** Structured extraction with sentiment score (-1 to 1), key events, red flags
            
            **Synthesis Brief:** 6-section investment brief with programmatic recommendation:
            - Strong Buy Signal
            - Cautious Positive  
            - Neutral
            - Flag for Review
            """)


if __name__ == "__main__":
    main()