"""Retrieves web and RAG document contexts based on routing analysis."""

import time
from typing import Tuple, List, Dict, Any
from ai_infra.search_engine import search_web, format_web_context
from ai_infra.rag_engine import format_rag_context
from intelligence.schemas import ConversationAnalysis, ResponsePlan

def retrieve_contexts(
    analyzer, planner, rag, user_prompt: str, chat_history: list, use_web: bool, use_rag: bool
) -> Tuple[ConversationAnalysis, ResponsePlan, List[Dict], float, List[Dict], float, float, List[str], float]:
    t_start = time.time()
    t_a = time.time()
    analysis = analyzer.analyze_sync(user_prompt, history=chat_history)
    analyzer_time = round(time.time() - t_a, 3)
    plan = planner.create_plan(analysis)

    route_web = bool(use_web and analysis.needs_web_search)
    route_rag = bool(use_rag and (analysis.needs_rag or len(rag.index) > 0))

    web_results, search_time, rag_chunks, rag_time, contexts = [], 0.0, [], 0.0, []
    if route_rag:
        t_r = time.time()
        score = 0.40 if analysis.needs_rag else 0.48
        rag_chunks = rag.search(user_prompt, top_k=3, min_score=score)
        rag_time = round(time.time() - t_r, 3)
        rc = format_rag_context(rag_chunks)
        if rc: contexts.append(rc)

    if route_web:
        web_results, search_time = search_web(user_prompt, max_results=3)
        wc = format_web_context(web_results)
        if wc: contexts.append(wc)

    return analysis, plan, web_results, search_time, rag_chunks, rag_time, analyzer_time, contexts, t_start

