import argparse
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from google.adk.a2a.utils.agent_to_a2a import (
    A2AStarletteApplication,
    DefaultRequestHandler,
    InMemoryTaskStore,
)

from src.agent import TranslationGreenAgent
from src.tool_provider import ToolProvider
from src.common import translator_judge_agent_card
from src.executor import GreenExecutor

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Run the Green Agent Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=9009, help="Port to bind")
    parser.add_argument("--card-url", type=str, help="Agent Card URL")
    args = parser.parse_args()

    # Initialize the logic
    tool_provider = ToolProvider()
    
    # Create the TranslationGreenAgent, which internally creates the judge agent
    translation_green_agent = TranslationGreenAgent(tool_provider)
    
    # Wrap the TranslationGreenAgent with GreenExecutor
    executor = GreenExecutor(translation_green_agent)

    # Create the Agent Card (this refers to the overall green agent, not just the judge)
    card_url = args.card_url if args.card_url else f"http://{args.host}:{args.port}/"
    card = translator_judge_agent_card(
        name="TranslatorGreenAgent", # Updated name to reflect the overall agent
        url=card_url
    )

    # Manually create the A2A components
    task_store = InMemoryTaskStore()
    handler = DefaultRequestHandler(executor, task_store)
    
    # Create the A2A Application helper
    a2a_app = A2AStarletteApplication(agent_card=card, http_handler=handler)
    
    # Create the actual Starlette application
    app = Starlette()
    
    # Add A2A routes to the Starlette app
    a2a_app.add_routes_to_app(app)
    
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()