import httpx
from uuid import uuid4
from a2a.client import (
    A2ACardResolver,
    ClientConfig,
    ClientFactory,
    Consumer,
)
from a2a.types import (
    Message,
    Part,
    Role,
    TextPart,
    DataPart,
    Task,
)

DEFAULT_TIMEOUT = 300

def create_message(*, role: Role = Role.user, text: str, context_id: str | None = None) -> Message:
    return Message(
        kind="message",
        role=role,
        parts=[Part(TextPart(kind="text", text=text))],
        message_id=uuid4().hex,
        context_id=context_id
    )

def merge_parts(parts: list[Part]) -> str:
    chunks = []
    for part in parts:
        if isinstance(part.root, TextPart):
            chunks.append(part.root.text)
        elif isinstance(part.root, DataPart):
            chunks.append(str(part.root.data))
    return "\n".join(chunks)

async def send_message(message: str, base_url: str, context_id: str | None = None, streaming=False, consumer: Consumer | None = None):
    """Returns dict with context_id, response and status (if exists)"""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        config = ClientConfig(
            httpx_client=httpx_client,
            streaming=streaming,
        )
        factory = ClientFactory(config)
        client = factory.create(agent_card)
        if consumer:
            await client.add_event_consumer(consumer)

        outbound_msg = create_message(text=message, context_id=context_id)
        outputs = {
            "response": "",
            "context_id": None
        }
        
        last_task = None
        async for event in client.send_message(outbound_msg):
            print(f"[CLIENT] Event type: {type(event).__name__}", flush=True)
            # A2A SDK returns tuples of (Task, Event) or just Message
            if isinstance(event, tuple):
                task, status_event = event
                last_task = task
                print(f"[CLIENT] Tuple - Task: {type(task).__name__}, Event: {type(status_event).__name__}", flush=True)
                # Check if the status event has the completed state
                if hasattr(status_event, 'status'):
                    status = status_event.status
                    print(f"[CLIENT] Status state: {status.state if status else 'None'}", flush=True)
                    if status and status.state:
                        if status.state.value == 'completed':
                            if status.message and status.message.parts:
                                outputs["response"] = merge_parts(status.message.parts)
                                outputs["context_id"] = task.context_id
                                print(f"[CLIENT] Extracted completed response: {outputs['response'][:100]}...", flush=True)
                        elif status.state.value == 'failed':
                             if status.message and status.message.parts:
                                outputs["response"] = f"ERROR: Task failed: {merge_parts(status.message.parts)}"
                                outputs["context_id"] = task.context_id
                                print(f"[CLIENT] Task failed: {outputs['response']}", flush=True)
                elif status_event is None:
                    print(f"[CLIENT] Got (Task, None). Task status: {task.status}", flush=True)
                    if task.status:
                        print(f"[CLIENT] Task state: {task.status.state}", flush=True)
                        if task.status.message:
                             print(f"[CLIENT] Task message parts: {len(task.status.message.parts)}", flush=True)

                    # Check if task itself has the completed status
                    if task.status and task.status.state and task.status.state.value == 'completed':
                        if task.status.message and task.status.message.parts:
                            outputs["response"] = merge_parts(task.status.message.parts)
                            outputs["context_id"] = task.context_id
                            print(f"[CLIENT] Extracted from task: {outputs['response'][:100]}...", flush=True)
            elif isinstance(event, Message):
                outputs["context_id"] = event.context_id
                outputs["response"] = merge_parts(event.parts)
                print(f"[CLIENT] Message response: {outputs['response'][:100]}...", flush=True)
            elif isinstance(event, Task):
                last_task = event
                print(f"[CLIENT] Task status: {event.status.state if event.status else 'None'}", flush=True)
                if event.status and event.status.state:
                    if event.status.state.value == 'completed':
                        if event.status.message and event.status.message.parts:
                            outputs["response"] = merge_parts(event.status.message.parts)
                            outputs["context_id"] = event.context_id
                    elif event.status.state.value == 'failed':
                        if event.status.message and event.status.message.parts:
                            outputs["response"] = f"ERROR: Task failed: {merge_parts(event.status.message.parts)}"
                            outputs["context_id"] = event.context_id
                            print(f"[CLIENT] Task failed: {outputs['response']}", flush=True)
        
        print(f"[CLIENT] Final response length: {len(outputs['response'])}", flush=True)
        return outputs