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

def create_model() -> ChatGroq:

    def query_employee_data_tool(employee_id: str | None=None, fields: list[str] | None=None, filters: dict[str, Any] | None=None, aggregate: str | None=None, aggregate_field: str | None=None) -> str:
        pass

    def policy_search_tool(query: str, k: int=4) -> str:
        pass
    return get_llm_client().bind_tools([query_employee_data_tool, policy_search_tool])

def call_model(state: AgentState) -> dict[str, Any]:
    emp_id = state.get('employee_id', 'Unknown')
    system_prompt = f"You are an internal HR AI assistant. You answer employee questions from two sources: 1) Company policy documents, and 2) A structured employee database.\n\nThe user asking the question is logged in as Employee ID: {emp_id}.\nIf the user asks about their own data, use their Employee ID to query the structured database.\n\nRouting rules:\n- If the question is purely about personal or aggregate data (leave balance, team size, highest balance, rating >= 4, etc.), use the `query_employee_data_tool`.\n- If the question is purely about general processes or policy, use the `policy_search_tool`.\n- HYBRID QUESTIONS: If the user asks 'can I take...', 'am I allowed...', 'should I...', or 'can I request...' this is a hybrid question. You MUST trigger BOTH the `policy_search_tool` (to check the rules) AND the `query_employee_data_tool` (to check their balance/status).\n- If the policy documents don't explicitly answer the entire question, do NOT just say 'I don't know'. Instead, provide a partial answer: 'The policy doesn't explicitly cover X, but it does say Y.'\n- If neither tool returns any relevant grounding, and you have no partial answer, you MUST respond exactly: 'I don't know.' Do not invent answers."
    history = list(state['messages'])[-10:]
    messages = [SystemMessage(content=system_prompt)] + history
    model = create_model()
    response = model.invoke(messages)
    return {'messages': [response]}
