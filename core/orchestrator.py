from langgraph.graph import StateGraph, END
from core.state import SystemState, init_state
from agents.financial_agent import financial_agent
from agents.news_agent import news_agent_sync as news_agent
from agents.risk_agent import risk_agent_sync as risk_agent
from agents.synthesis_agent import synthesis_agent_sync as synthesis_agent


def create_pipeline():
    """Create the LangGraph StateGraph for the 4-agent pipeline.
    
    Execution order (sequential to avoid concurrent state writes):
    1. financial_agent - fetches financial data, sets company_name
    2. news_agent - fetches news sentiment using company_name
    3. risk_agent - computes risk score using financial + news data
    4. synthesis_agent - generates final brief
    """
    
    workflow = StateGraph(SystemState)
    
    # Add nodes for each agent
    workflow.add_node("financial_agent", financial_agent)
    workflow.add_node("news_agent", news_agent)
    workflow.add_node("risk_agent", risk_agent)
    workflow.add_node("synthesis_agent", synthesis_agent)
    
    # Sequential execution: each agent depends on previous agent's output
    workflow.set_entry_point("financial_agent")
    workflow.add_edge("financial_agent", "news_agent")
    workflow.add_edge("news_agent", "risk_agent")
    workflow.add_edge("risk_agent", "synthesis_agent")
    workflow.add_edge("synthesis_agent", END)
    
    return workflow.compile()


def run_pipeline(ticker: str) -> SystemState:
    """Execute the full pipeline for a given ticker."""
    pipeline = create_pipeline()
    initial_state = init_state(ticker)
    final_state = pipeline.invoke(initial_state)
    return final_state


def run_pipeline_async(ticker: str):
    """Execute the full pipeline asynchronously."""
    pipeline = create_pipeline()
    initial_state = init_state(ticker)
    return pipeline.ainvoke(initial_state)


def get_orchestrator():
    """Get the compiled pipeline graph."""
    return create_pipeline()