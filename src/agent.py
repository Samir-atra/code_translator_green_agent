from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from src.common import TranslatorEval, EvalRequest
from src.tool_provider import ToolProvider
from src.executor import GreenAgent
from a2a.utils import new_agent_text_message
from a2a.server.tasks import TaskUpdater
from a2a.server.tasks import TaskUpdater
import json
import os
from google import genai
from google.genai import types
from a2a.types import Part, DataPart

SYSTEM_PROMPT = '''
you are an expert evaluation agent specialized in evaluating code and programming languages translation and
how efficient it is to run without errors, and judging a successful translation requires the following
considerations:

    - it does not produce error when it runs.
    - it is styled and commented in the new language method.
    - it is concise and does not have extra non relevant code.
    - it is clear and relevant to the topic.

the format of the output translation is as follows, containing at least two points of them with requirement for the first one:

    1 - the translation: the translation of the code in the new language.
    2 - it keeps the same functionality of the original code.
    3 - it have the same structure and logic of the original code.

the translation needs to start with a note about the current language and the new language.

in general the translation needs to be clear, clean and error free.
'''

class TranslationGreenAgent(GreenAgent):
    def __init__(self, tool_provider: ToolProvider):
        self._tool_provider = tool_provider
        # Initialize Gemini Client
        self.client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

    # Removed _create_judge_agent as we use genai.Client directly

    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        if not request.participants:
            return False, "No participants provided in the evaluation request."
        if len(request.participants) > 1:
            return False, "Only one participant is supported per evaluation."
        if "code_to_translate" not in request.config and "test_cases" not in request.config:
            return False, "Missing 'code_to_translate' or 'test_cases' in config."
        if "source_language" not in request.config:
            return False, "Missing 'source_language' in config."
        if "target_language" not in request.config:
            return False, "Missing 'target_language' in config."
        return True, ""

    async def run_eval(self, request: EvalRequest, updater: TaskUpdater) -> None:
        # Extract the single participant
        role, endpoint = next(iter(request.participants.items()))
        
        # Determine inputs: support both single 'code_to_translate' and list 'test_cases'
        code_inputs = []
        if "test_cases" in request.config and isinstance(request.config["test_cases"], list):
             code_inputs = request.config["test_cases"]
        elif "code_to_translate" in request.config:
             code_inputs = [request.config["code_to_translate"]]
        
        source_language = request.config["source_language"]
        target_language = request.config["target_language"]
        
        evaluations = []
        
        for i, code_to_translate in enumerate(code_inputs):
            case_label = f"Case {i+1}/{len(code_inputs)}"
            await updater.update_status(
                "working", 
                new_agent_text_message(f"Processing {case_label} with participant '{role}'...")
            )
            
            # --- TRANSLATION STEP ---
            try:
                print(f"[DEBUG] Sending {case_label} to Purple Agent at {endpoint}", flush=True)
                response = await self._tool_provider.talk_to_agent(
                    url=endpoint,
                    message=json.dumps({
                        "code_to_translate": code_to_translate,
                        "source_language": source_language,
                        "target_language": target_language
                    })
                )
                print(f"[DEBUG] Received response for {case_label}: '{response}'", flush=True)

                translated_code = None
                # Attempt 1: JSON
                try:
                    data = json.loads(response)
                    if isinstance(data, dict):
                        translated_code = data.get("translated_code") or data.get("code") or data.get("content") or data.get("message")
                    elif isinstance(data, str):
                        translated_code = data
                except json.JSONDecodeError:
                    pass

                # Attempt 2: Markdown
                if not translated_code:
                    import re
                    matches = re.findall(r"```(?:\w+)?\n(.*?)```", response, re.DOTALL)
                    if matches:
                        translated_code = max(matches, key=len).strip()
                
                # Attempt 3: Raw
                if not translated_code:
                    translated_code = response.strip()

                if not translated_code:
                     print(f"[WARN] Empty response for {case_label}")
                     translated_code = "// Error: No Code Translated"
                
            except Exception as e:
                print(f"[ERROR] Communication failed for {case_label}: {e}")
                translated_code = f"// Error: Communication failed: {e}"

            # --- EVALUATION STEP ---
            await updater.update_status(
                "working",
                new_agent_text_message(f"Evaluating {case_label}...")
            )

            prompt = f"""
{SYSTEM_PROMPT}

Please evaluate the following code translation based on the criteria:
- Execution Correctness
- Style & Documentation
- Conciseness
- Relevance

Original {source_language} code:
```
{code_to_translate}
```

Translated {target_language} code (from participant '{role}'):
```
{translated_code}
```

Provide your evaluation in the TranslatorEval schema, including reasoning, winner (participant's role or 'N/A'), execution_correctness, style_score, conciseness, and relevance.
"""
            # Models that support JSON mode with schema (ordered by preference)
            json_supported_models = [
                "gemini-2.5-flash-lite",
                "gemini-2.0-flash-lite",
                "gemini-2.0-flash",
                "gemini-2.5-flash",
                "gemini-2.0-flash-001",
                "gemini-2.0-flash-lite-001",
                "gemini-flash-latest",
                "gemini-flash-lite-latest",
                "gemini-pro-latest",
                "gemini-2.5-pro",
                "gemini-exp-1206",
                "gemini-3-flash-preview",
                "gemini-3-pro-preview"
            ]
            
            # Text-only models (Gemma and experimental) - use text mode and parse manually
            text_only_models = [
                "gemma-3-1b-it",
                "gemma-3-4b-it",
                "gemma-3-12b-it",
                "gemma-3-27b-it",
                "gemma-3n-e2b-it",
                "gemma-3n-e4b-it"
            ]
            
            models_to_try = json_supported_models + text_only_models
            
            case_eval = None
            for model in models_to_try:
                try:
                    use_json_mode = model in json_supported_models
                    
                    if use_json_mode:
                        response = await self.client.aio.models.generate_content(
                            model=model,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type='application/json',
                                response_schema=TranslatorEval
                            )
                        )
                        case_eval = response.parsed
                    else:
                        # For Gemma models - use text mode and parse manually
                        response = await self.client.aio.models.generate_content(
                            model=model,
                            contents=prompt
                        )
                        response_text = response.text
                        
                        # Try to parse JSON from response
                        import re
                        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group(0))
                            case_eval = TranslatorEval(
                                reasoning=data.get("reasoning", "Evaluated by Gemma model"),
                                winner=data.get("winner", role),
                                execution_correctness=float(data.get("execution_correctness", 5)),
                                style_score=float(data.get("style_score", 5)),
                                conciseness=float(data.get("conciseness", 5)),
                                relevance=float(data.get("relevance", 5))
                            )
                    
                    if case_eval:
                        break
                except Exception as e:
                    print(f"[DEBUG] Model {model} failed for {case_label}: {e}")
                    if "429" in str(e):
                        import asyncio
                        await asyncio.sleep(5)
            
            if not case_eval:
                # Fallback if evaluation fails
                case_eval = TranslatorEval(
                    reasoning=f"Evaluation failed for {case_label}",
                    winner="N/A",
                    execution_correctness=0,
                    style_score=0,
                    conciseness=0,
                    relevance=0
                )
            
            evaluations.append(case_eval)

        # --- AGGREGATION STEP ---
        count = len(evaluations)
        if count == 0:
             await updater.failed(new_agent_text_message("No evaluations occurred."))
             return

        avg_exec = sum(e.execution_correctness for e in evaluations) / count
        avg_style = sum(e.style_score for e in evaluations) / count
        avg_conciseness = sum(e.conciseness for e in evaluations) / count
        avg_relevance = sum(e.relevance for e in evaluations) / count
        
        combined_reasoning = "\n\n".join([f"[{i+1}/{count}] Winner: {e.winner}. {e.reasoning}" for i, e in enumerate(evaluations)])
        
        # Determine overall winner (majority wins or high score?)
        # For simplicity, if we have a winner in >50% cases, we propagate that, else N/A
        winners = [e.winner for e in evaluations if e.winner != "N/A"]
        overall_winner = max(set(winners), key=winners.count) if winners else "N/A"

        final_result = TranslatorEval(
            reasoning=f"Aggregated Score across {count} test cases.\n\nDetails:\n{combined_reasoning}",
            winner=overall_winner,
            execution_correctness=round(avg_exec, 2),
            style_score=round(avg_style, 2),
            conciseness=round(avg_conciseness, 2),
            relevance=round(avg_relevance, 2)
        )

        await updater.add_artifact(
           parts=[Part(root=DataPart(data=final_result.model_dump()))],
           name="Evaluation Result"
        )
        
        await updater.update_status(
            "completed",
            new_agent_text_message(f"Evaluation complete. Winner: {final_result.winner}, Execution: {final_result.execution_correctness}, Style: {final_result.style_score}, Conciseness: {final_result.conciseness}, Relevance: {final_result.relevance}")
        )