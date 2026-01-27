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
        if "code_to_translate" not in request.config:
            return False, "Missing 'code_to_translate' in config."
        if "source_language" not in request.config:
            return False, "Missing 'source_language' in config."
        if "target_language" not in request.config:
            return False, "Missing 'target_language' in config."
        return True, ""

    async def run_eval(self, request: EvalRequest, updater: TaskUpdater) -> None:
        # Extract the single participant
        role, endpoint = next(iter(request.participants.items()))
        code_to_translate = request.config["code_to_translate"]
        source_language = request.config["source_language"]
        target_language = request.config["target_language"]

        # Step 1: Request translation from the participant agent
        await updater.update_status(
            "working",
            new_agent_text_message(f"Requesting translation from participant '{role}'...")
        )
        try:
            # Send the code to translate to the participant agent
            print(f"[DEBUG] Sending message to Purple Agent at {endpoint}", flush=True)
            response = await self._tool_provider.talk_to_agent(
                url=endpoint,
                message=json.dumps({
                    "code_to_translate": code_to_translate,
                    "source_language": source_language,
                    "target_language": target_language
                })
            )
            print(f"[DEBUG] Received response from Purple Agent: '{response}'", flush=True)
            # The response is expected to be a JSON string with the translated code
            translated_code_data = json.loads(response)
            translated_code = translated_code_data.get("translated_code", "")

            if not translated_code:
                await updater.failed(new_agent_text_message("Participant did not return translated code."))
                return

        except Exception as e:
            print(f"[DEBUG] Exception communicating with participant: {e}", flush=True)
            await updater.failed(new_agent_text_message(f"Error communicating with participant: {e}"))
            return

        await updater.update_status(
            "working",
            new_agent_text_message("Received translated code. Evaluating...")
        )

        # Step 2: Use the judge agent to evaluate the translated code
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

Provide your evaluation in the TranslatorEval schema, including reasoning, winner (the participant's role if it's a good translation, or 'N/A' otherwise), and scores.
"""
        models_to_try = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-flash-latest",
            "gemini-pro-latest",
            "gemini-2.5-pro"
        ]
        
        last_error = None
        for model in models_to_try:
            try:
                print(f"[DEBUG] Trying evaluation with model: {model}")
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        response_schema=TranslatorEval
                    )
                )
                eval_result: TranslatorEval = response.parsed
                
                # If parsed is None (should not happen with structured output)
                if not eval_result:
                     raise ValueError("Model failed to return structured output")
    
                await updater.update_status(
                    "completed",
                    new_agent_text_message(f"Evaluation complete. Winner: {eval_result.winner}, Scores: {eval_result.scores}")
                )
                # You might want to store the full eval_result or just the scores in the task result
                await updater.update_result(eval_result.model_dump())
                return # Assessment successful, exit function

            except Exception as e:
                print(f"[DEBUG] Model {model} failed: {e}")
                last_error = e
                # Check for resource exhausted and wait if needed
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print("[DEBUG] Quota exhausted. Waiting 30 seconds before trying next model...", flush=True)
                    import asyncio
                    await asyncio.sleep(30)
                # Continue to next model
        
        # If all models failed
        await updater.failed(new_agent_text_message(f"All evaluation models failed. Last error: {last_error}"))