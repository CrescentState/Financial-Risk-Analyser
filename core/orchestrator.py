import asyncio
import time
from langgraph.graph import StateGraph, END
from core.state import SystemState, init_state
from agents.financial_agent import financial_agent_async
from agents.news_agent import news_agent_async
from agents.risk_agent import risk_agent_async
from agents.synthesis_agent import synthesis_agent_async


def _merge_timing(state: SystemState, result: dict, name: str, elapsed: float) -> dict:
    """Attach this node's wall-clock seconds to the timings channel."""
    timings = dict(state.get("timings", {}))
    timings[name] = round(elapsed, 2)
    return {**result, "timings": timings}


def _timed_sync(name: str, fn):
    """Wrap a sync node so its duration is recorded under `name`."""
    def wrapper(state: SystemState) -> dict:
        start = time.perf_counter()
        result = fn(state)
        return _merge_timing(state, result, name, time.perf_counter() - start)
    wrapper.__name__ = f"timed_{name}"
    return wrapper


def _timed_async(name: str, fn):
    """Wrap an async node so its duration is recorded under `name`."""
    async def wrapper(state: SystemState) -> dict:
        start = time.perf_counter()
        result = await fn(state)
        return _merge_timing(state, result, name, time.perf_counter() - start)
    wrapper.__name__ = f"timed_{name}"
    return wrapper


def _sync_financial_agent(state: SystemState) -> dict:
    return asyncio.run(financial_agent_async(state))


def _sync_news_agent(state: SystemState) -> dict:
    return asyncio.run(news_agent_async(state))


def _sync_risk_agent(state: SystemState) -> dict:
    return asyncio.run(risk_agent_async(state))


def _sync_synthesis_agent(state: SystemState) -> dict:
    return asyncio.run(synthesis_agent_async(state))


def _sync_financial_news_parallel_node(state: SystemState) -> dict:
    return asyncio.run(_run_financial_and_news_parallel(state))


async def _run_financial_and_news_parallel(state: SystemState) -> dict:
    """Run financial_agent and news_agent concurrently."""
    # Time each inner agent so parallel and sequential modes expose
    # the same timing keys (financial, news, risk, synthesis).
    durations: dict[str, float] = {}

    async def _run_timed(name: str, coro):
        start = time.perf_counter()
        try:
            return await coro
        finally:
            durations[name] = round(time.perf_counter() - start, 2)

    # Run both agents concurrently using their native async implementations
    financial_task = asyncio.create_task(_run_timed("financial", financial_agent_async(state)))
    news_task = asyncio.create_task(_run_timed("news", news_agent_async(state)))

    financial_result, news_result = await asyncio.gather(financial_task, news_task)
    
    # Merge results carefully:
    # - financial_result has company_name, financial_data, errors, confidence_score
    # - news_result has news_data, errors, confidence_score, (company_name='')
    # We want to preserve financial_result's company_name and financial_data
    # and merge errors and confidence_score
    merged = {**state}
    merged.update(financial_result)
    
    # Merge news_result but don't overwrite company_name or financial_data
    for key, value in news_result.items():
        if key in ("company_name", "financial_data"):
            continue  # Skip - keep financial_agent's version
        elif key == "errors":
            # Merge error lists
            merged_errors = list(merged.get("errors", []))
            merged_errors.extend(value)
            merged["errors"] = merged_errors
        elif key == "confidence_score":
            # Use minimum confidence (most conservative)
            merged["confidence_score"] = min(merged.get("confidence_score", 1.0), value)
        else:
            merged[key] = value

    merged_timings = dict(merged.get("timings", {}))
    merged_timings.update(durations)
    merged["timings"] = merged_timings

    return merged


async def _financial_news_parallel_node(state: SystemState) -> dict:
    """Async wrapper for parallel financial + news execution."""
    return await _run_financial_and_news_parallel(state)


def create_pipeline(parallel: bool = True):
    """Create the LangGraph StateGraph for the 4-agent pipeline (sync version).
    
    Args:
        parallel: If True, run financial_agent and news_agent in parallel using
                  a combined node. If False, run sequentially.
    """
    workflow = StateGraph(SystemState)
    
    # Add nodes for each agent (sync wrappers for sync pipeline)
    workflow.add_node("financial_agent", _timed_sync("financial", _sync_financial_agent))
    workflow.add_node("news_agent", _timed_sync("news", _sync_news_agent))
    workflow.add_node("risk_agent", _timed_sync("risk", _sync_risk_agent))
    workflow.add_node("synthesis_agent", _timed_sync("synthesis", _sync_synthesis_agent))
    
    if parallel:
        # PARALLEL: combined financial+news node runs both concurrently
        workflow.add_node("financial_news_parallel", _sync_financial_news_parallel_node)
        
        workflow.set_entry_point("financial_news_parallel")
        workflow.add_edge("financial_news_parallel", "risk_agent")
        workflow.add_edge("risk_agent", "synthesis_agent")
        workflow.add_edge("synthesis_agent", END)
    else:
        # SEQUENTIAL: financial -> news -> risk -> synthesis
        workflow.set_entry_point("financial_agent")
        workflow.add_edge("financial_agent", "news_agent")
        workflow.add_edge("news_agent", "risk_agent")
        workflow.add_edge("risk_agent", "synthesis_agent")
        workflow.add_edge("synthesis_agent", END)
    
    return workflow.compile()


def create_pipeline_async(parallel: bool = True):
    """Create the LangGraph StateGraph for the 4-agent pipeline (async version).
    
    Args:
        parallel: If True, run financial_agent and news_agent in parallel using
                  a combined node. If False, run sequentially.
    """
    workflow = StateGraph(SystemState)
    
    # Add nodes for each agent (async versions)
    workflow.add_node("financial_agent", _timed_async("financial", financial_agent_async))
    workflow.add_node("news_agent", _timed_async("news", news_agent_async))
    workflow.add_node("risk_agent", _timed_async("risk", risk_agent_async))
    workflow.add_node("synthesis_agent", _timed_async("synthesis", synthesis_agent_async))
    
    if parallel:
        # PARALLEL: combined financial+news node runs both concurrently
        workflow.add_node("financial_news_parallel", _financial_news_parallel_node)
        
        workflow.set_entry_point("financial_news_parallel")
        workflow.add_edge("financial_news_parallel", "risk_agent")
        workflow.add_edge("risk_agent", "synthesis_agent")
        workflow.add_edge("synthesis_agent", END)
    else:
        # SEQUENTIAL: financial -> news -> risk -> synthesis
        workflow.set_entry_point("financial_agent")
        workflow.add_edge("financial_agent", "news_agent")
        workflow.add_edge("news_agent", "risk_agent")
        workflow.add_edge("risk_agent", "synthesis_agent")
        workflow.add_edge("synthesis_agent", END)
    
    return workflow.compile()


def run_pipeline(ticker: str, parallel: bool = True) -> SystemState:
    """Execute the full pipeline for a given ticker."""
    pipeline = create_pipeline(parallel=parallel)
    initial_state = init_state(ticker)
    final_state = pipeline.invoke(initial_state)
    return final_state


def run_pipeline_async(ticker: str, parallel: bool = True):
    """Execute the full pipeline asynchronously."""
    pipeline = create_pipeline_async(parallel=parallel)
    initial_state = init_state(ticker)
    return pipeline.ainvoke(initial_state)


def get_orchestrator(parallel: bool = True):
    """Get the compiled pipeline graph (sync version)."""
    return create_pipeline(parallel=parallel)


def get_orchestrator_async(parallel: bool = True):
    """Get the compiled pipeline graph (async version)."""
    return create_pipeline_async(parallel=parallel)