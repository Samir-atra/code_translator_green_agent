from pydantic import BaseModel, Field
from typing import List, Dict, Any
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

class Participant(BaseModel):
    role: str
    endpoint: str

class EvalRequest(BaseModel):
    participants: List[Participant]
    config: Dict[str, Any]

class TranslatorEval(BaseModel):
    reasoning: str = Field(description="The reasoning behind the evaluation.")
    winner: str = Field(description="The role of the winning agent (e.g., 'researcher_translator').")
    scores: Dict[str, int] = Field(description="Scores for each participant (0-10).")

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