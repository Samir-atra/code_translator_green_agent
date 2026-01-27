import asyncio
import os
import signal
import subprocess
import sys
import time
import httpx
import json

# Configuration
GREEN_AGENT_DIR = os.path.abspath("code_translator_green_agent")
PURPLE_AGENT_DIR = os.path.abspath("code_translator_purple_agent")

GREEN_PORT = 9009
PURPLE_PORT = 9010

GREEN_URL = f"http://127.0.0.1:{GREEN_PORT}"
PURPLE_URL = f"http://127.0.0.1:{PURPLE_PORT}"

def start_process(command, cwd, name, log_file):
    print(f"Starting {name}...")
    # Open log file for writing
    f = open(log_file, "w")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=f,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid  # Creates a new session to easily kill process group
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

async def run_test():
    # 1. Start Agents
    green_proc, green_log = start_process(
        [sys.executable, "src/server.py", "--port", str(GREEN_PORT)], 
        GREEN_AGENT_DIR, 
        "Green Agent",
        "green_agent.log"
    )
    
    purple_proc, purple_log = start_process(
        [sys.executable, "src/server.py", "--port", str(PURPLE_PORT)], 
        PURPLE_AGENT_DIR, 
        "Purple Agent",
        "purple_agent.log"
    )

    try:
        # 2. Wait for health
        green_ready = await wait_for_agent(GREEN_URL, "Green Agent")
        purple_ready = await wait_for_agent(PURPLE_URL, "Purple Agent")

        if not (green_ready and purple_ready):
            print("One or more agents failed to start. Aborting.")
            return

        # 3. Send Test Request
        print("\n--- Sending Evaluation Request ---")
        
        # This payload matches what the Green Agent expects locally
        payload = {
            "participants": {
                "translator": PURPLE_URL
            },
            "config": {
                "code_to_translate": "def factorial(n):\n    if n == 0:\n        return 1\n    else:\n        return n * factorial(n-1)",
                "source_language": "python",
                "target_language": "javascript"
            }
        }
        
        from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
        from a2a.types import Message, Part, TextPart, Role
        from uuid import uuid4

        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
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
            async for event in client.send_message(msg):
                if isinstance(event, Message):
                    # Final response
                    print(f"[RESPONSE]: {event.parts[0].root.text if event.parts and event.parts[0].root.kind == 'text' else event.parts}")
                else:
                    # Task update tuple (task, task_update)
                    task, update = event
                    # We might get task updates or artifacts
                    status = task.status.state
                    status_text = ""
                    if hasattr(task.status, 'message') and task.status.message and task.status.message.parts:
                         # Check if part is TextPart (it might be wrapped in Part -> root -> text)
                         part = task.status.message.parts[0]
                         if hasattr(part, 'root') and hasattr(part.root, 'text'):
                             status_text = part.root.text
                         elif hasattr(part, 'text') and hasattr(part.text, 'text'):
                             status_text = part.text.text
                    
                    print(f"[UPDATE] Status: {status} | {status_text}")
                    if update:
                         # Ensure we print artifact if available
                         pass

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
    asyncio.run(run_test())
