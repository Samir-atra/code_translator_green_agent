import asyncio
import os
import signal
import subprocess
import sys
import time
import httpx
import json
import uuid
from datetime import datetime

# Configuration
GREEN_AGENT_DIR = os.path.abspath("code_translator_green_agent")
PURPLE_AGENT_DIR = os.path.abspath("code_translator_purple_agent")
LEADERBOARD_DIR = os.path.abspath("code_translator_leaderboard")
RESULTS_DIR = os.path.join(LEADERBOARD_DIR, "results")

# Ensure results directory exists
os.makedirs(RESULTS_DIR, exist_ok=True)

GREEN_PORT = 9009
PURPLE_PORT = 9010

GREEN_URL = f"http://127.0.0.1:{GREEN_PORT}"
PURPLE_URL = f"http://127.0.0.1:{PURPLE_PORT}"

def start_process(command, cwd, name, log_file):
    print(f"Starting {name}...")
    f = open(log_file, "w")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=f,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid
    )
    return process, f

async def wait_for_agent(url, name, timeout=30):
    print(f"Waiting for {name} to be ready at {url}...")
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(f"{url}/.well-known/agent-card.json")
                if response.status_code == 200:
                    print(f"{name} is ready!")
                    return True
            except httpx.ConnectError:
                pass
            except Exception as e:
                print(f"Error checking {name}: {e}")
            await asyncio.sleep(1)
    print(f"{name} failed to start within {timeout} seconds.")
    return False

async def run_leaderboard_test():
    # 1. Start Agents
    green_proc, green_log = start_process(
        ["uv", "run", "src/server.py", "--port", str(GREEN_PORT)], 
        GREEN_AGENT_DIR, 
        "Green Agent",
        "green_agent_leaderboard.log"
    )
    
    purple_proc, purple_log = start_process(
        ["uv", "run", "src/server.py", "--port", str(PURPLE_PORT)], 
        PURPLE_AGENT_DIR, 
        "Purple Agent",
        "purple_agent_leaderboard.log"
    )

    try:
        # 2. Wait for health
        green_ready = await wait_for_agent(GREEN_URL, "Green Agent")
        purple_ready = await wait_for_agent(PURPLE_URL, "Purple Agent")

        if not (green_ready and purple_ready):
            print("One or more agents failed to start. Aborting.")
            return

        # 3. Send Evaluation Request
        print("\n--- Sending Evaluation Request for Leaderboard ---")
        
        participant_id = "019b8933-d5b6-76a3-8e0b-930c19c10e87" # Example ID from scenario
        participant_name = "translator"
        
        payload = {
            "participants": {
                participant_name: PURPLE_URL
            },
            "config": {
                "test_cases": [
    """
def process_data(items):
    \"\"\"
    Filters items with length > 3 and converts them to uppercase.
    Returns a list of formatted strings with their original indices.
    \"\"\"
    return [
        f"{idx}: {item.upper()}"
        for idx, item in enumerate(items)
        if len(item) > 3
    ]
""",
    """
class Fibonacci:
    def __init__(self):
        self.memo = {}

    def get_number(self, n):
        if n in self.memo:
            return self.memo[n]
        if n <= 1:
            return n
        self.memo[n] = self.get_number(n - 1) + self.get_number(n - 2)
        return self.memo[n]
""",
    """
import re

def parse_log_line(line):
    # Format: [TIMESTAMP] LEVEL: Message
    pattern = r"\[(.*?)\] (\w+): (.*)"
    match = re.match(pattern, line)
    if match:
        timestamp, level, message = match.groups()
        return {"time": timestamp, "level": level, "msg": message}
    return None
"""
                ],
                "source_language": "python",
                "target_language": "javascript"
            }
        }
        
        from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
        from a2a.types import Message, Part, TextPart, Role, DataPart
        from uuid import uuid4

        async with httpx.AsyncClient(timeout=120.0) as httpx_client:
            print(f"Resolving agent card from {GREEN_URL}...")
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=GREEN_URL)
            agent_card = await resolver.get_agent_card()
            
            config = ClientConfig(httpx_client=httpx_client, streaming=True)
            factory = ClientFactory(config)
            client = factory.create(agent_card)

            msg = Message(
                kind="message",
                role=Role.user,
                parts=[Part(TextPart(text=json.dumps(payload)))],
                message_id=uuid4().hex,
            )

            print(f"Messaging Green Agent at {GREEN_URL}...")
            
            evaluation_result = None
            
            async for event in client.send_message(msg):
                if isinstance(event, Message):
                    pass
                else:
                    task, update = event
                    # Check for artifacts where evaluation result is stored
                    if task.artifacts:
                         for artifact in task.artifacts:
                             if artifact.name == "Evaluation Result":
                                 # Assuming it's a DataPart
                                 if isinstance(artifact.parts[0].root, DataPart):
                                     evaluation_result = artifact.parts[0].root.data
                                     print(f"[ARTIFACT] Found evaluation result: {evaluation_result}")
            
            if evaluation_result:
                # 4. Generate Leaderboard JSON
                print("\n--- Generating Leaderboard Entry ---")
                
                # Extract scores directly from the new schema
                execution_correctness = evaluation_result.get("execution_correctness", 0)
                style_score = evaluation_result.get("style_score", 0)
                conciseness = evaluation_result.get("conciseness", 0)
                relevance = evaluation_result.get("relevance", 0)
                
                # Calculate overall score if needed, or use average
                overall_score = (execution_correctness + style_score + conciseness + relevance) / 4.0
                
                # Format matching AgentBeats tutorial (participants + results)
                result_entry = {
                    "participants": {
                        participant_name: participant_id
                    },
                    "results": [
                        {
                            "winner": evaluation_result.get("winner", participant_name),
                            "execution_correctness": execution_correctness,
                            "style_score": style_score,
                            "conciseness": conciseness,
                            "relevance": relevance,
                            "overall_score": overall_score,
                            "reasoning": evaluation_result.get("reasoning", "")
                        }
                    ]
                }
                
                filename = f"result_{participant_name}_{int(time.time())}.json"
                filepath = os.path.join(RESULTS_DIR, filename)
                
                with open(filepath, "w") as f:
                    json.dump(result_entry, f, indent=2)
                
                print(f"Leaderboard result saved to: {filepath}")
                print(json.dumps(result_entry, indent=2))
                
            else:
                print("Failed to retrieve evaluation result artifact.")

    except Exception as e:
        print(f"An error occurred during testing: {e}")

    finally:
        print("\n--- Shutting down agents ---")
        os.killpg(os.getpgid(green_proc.pid), signal.SIGTERM)
        os.killpg(os.getpgid(purple_proc.pid), signal.SIGTERM)
        green_log.close()
        purple_log.close()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(run_leaderboard_test())
