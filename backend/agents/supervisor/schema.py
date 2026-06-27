from typing import List, Dict
from pydantic import BaseModel, Field


class Context(BaseModel):
    reference_date: str
    reference_day: str
    reference_time: str


class Payload(BaseModel):
    query: str
    context: Context

    # Focused input per agent, keyed by agent name. The supervisor extracts a
    # clean, minimal input for each routed agent, e.g.
    # {"temporal": "tomorrow", "location": "Doha"}.
    agent_inputs: Dict[str, str] = Field(default_factory=dict)


class SuperVisorResponse(BaseModel):

    next_steps: List[str]

    reason: str

    payload: Payload