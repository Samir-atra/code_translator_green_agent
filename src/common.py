from pydantic import BaseModel, Field
from typing import List, Dict, Any
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

class EvalRequest(BaseModel):
    participants: Dict[str, str]
    config: Dict[str, Any]

class ParticipantScore(BaseModel):
    participant: str
    score: int

class TranslatorEval(BaseModel):
    reasoning: str = Field(description="The reasoning behind the evaluation.")
    execution_correctness: float = Field(description="Score for execution correctness (0-10).")
    style_score: float = Field(description="Score for style and documentation (0-10).")
    conciseness: float = Field(description="Score for conciseness (0-10).")
    relevance: float = Field(description="Score for relevance (0-10).")
    winner: str = Field(description="The role of the winning agent (e.g., 'researcher_translator') or 'N/A'.")

def translator_judge_agent_card(name: str, url: str):
    return AgentCard(
        name=name,
        url=url,
        version="1.0.0",
        description="An agent that evaluates code translations.",
        capabilities=AgentCapabilities(),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="evaluate_translation",
                name="Evaluate Translation",
                description="Evaluates the quality of code translation between programming languages.",
                tags=["code", "translation", "evaluation"]
            )
        ]
    )