from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from src.common import TranslatorEval
from src.tool_provider import ToolProvider

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

def create_judge_agent(tool_provider: ToolProvider) -> Agent:
    return Agent(
        name="translator_judge_adk",
        model="gemini-2.5-flash",
        description=(
            "assess the quality of the programming language translation given and which one is better meeting the criteria"
        ),
        instruction=SYSTEM_PROMPT,
        tools=[FunctionTool(func=tool_provider.talk_to_agent)],
        output_schema=TranslatorEval,
        after_agent_callback=lambda callback_context: tool_provider.reset()
    )