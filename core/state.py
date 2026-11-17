from typing import List, Dict, Any
from typing_extensions import TypedDict

class AgentState(TypedDict):
    query: str
    intent: str
    documents: List[Any]
    is_relevant: bool
    summary_mode: bool
    response: str
    citations: List[Dict[str, Any]]