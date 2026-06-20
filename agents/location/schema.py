from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LocationAgentResponse(BaseModel):
    status: Literal["ok", "error"]
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

