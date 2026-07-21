import operator
from typing import Annotated, Any, Sequence, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, AIMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import os
from app.tools.employee_lookup import query_employee_data
from app.tools.policy_search import policy_search

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    employee_id: str
_LLM_CLIENT: ChatGroq | None = None

def get_llm_client() -> ChatGroq:
    global _LLM_CLIENT
    if _LLM_CLIENT is None:
        _LLM_CLIENT = ChatGroq(model='openai/gpt-oss-20b')
    return _LLM_CLIENT
