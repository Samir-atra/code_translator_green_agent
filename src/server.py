import argparse
import uvicorn
from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from src.agent import create_judge_agent
from src.tool_provider import ToolProvider
from src.common import translator_judge_agent_card

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Run the Green Agent Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=9009, help="Port to bind")
    parser.add_argument("--card-url", type=str, help="Agent Card URL")
    args = parser.parse_args()

    # Initialize the logic
    tool_provider = ToolProvider()
    agent = create_judge_agent(tool_provider)

    # Create the Agent Card
    card = translator_judge_agent_card(
        name="TranslatorJudgeADK",
        url=f"http://{args.host}:{args.port}/"
    )

    app = to_a2a(agent, agent_card=card)
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()