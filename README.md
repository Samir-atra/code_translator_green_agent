# Code Translator Green Agent (Judge)

This repository contains the implementation of the **Green Agent**, a judge agent designed for the Code Translator competition. Its primary role is to evaluate code translations performed by other agents (specifically the **Purple Agent**).

## Overview

The Green Agent acts as an orchestrator and evaluator. When it receives a request to evaluate a code translation task:
1.  **Orchestration**: It requests the **Purple Agent** (Participant) to translate a given snippet of code from a source language to a target language.
2.  **Evaluation**: Upon receiving the translation, it uses **Google GenAI (Gemini)** to act as a judge. The judge evaluates the translation based on executing correctness, style, conciseness, and relevance.
3.  **Reporting**: It returns a structured evaluation containing scores, reasoning, and a winner determination.

## Repository Structure

-   **`src/`**: Source code for the agent.
    -   **`agent.py`**: Contains `TranslationGreenAgent`. This is the core logic that handles the evaluation workflow: validating requests, communicating with the participant agent, and invoking the Gemini model for judging.
    -   **`server.py`**: The entry point for the application. It initializes the `TranslationGreenAgent`, wraps it in a `GreenExecutor`, and sets up the **A2A (Agent-to-Agent)** Starlette server.
    -   **`common.py`**: Defines shared data structures and Pydantic models (e.g., `EvalRequest`, `TranslatorEval`) and the Agent Card configuration.
    -   **`executor.py`**: Handles the execution context for the agent, providing the sandbox or environment for running the agent logic.
    -   **`tool_provider.py`**: Provides utilities for the agent to interact with external services or other agents (e.g., `talk_to_agent` implementation).
    -   **`client.py`**: Client-side utilities or helpers for interacting with the agent.
-   **`tests/`**: Test suite.
    -   **`test_agent.py`**: Contains integration tests and A2A conformance tests to ensure the agent behaves correctly, validates schemas, and adheres to the protocol.
    -   **`conftest.py`**: Pytest configuration and fixtures.
-   **`Dockerfile`**: Configuration to containerize the application for deployment.
-   **`pyproject.toml`**: Project configuration and dependencies.

## Setup & Setup

### Prerequisites

-   Python 3.11+
-   A **Google GenAI API Key** (Gemini)
-   (Optional) Docker

### Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd code_translator_green_agent
    ```

2.  **Create a virtual environment** (optional but recommended):
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install .
    # Or install specific requirements
    pip install python-dotenv uvicorn httpx google-genai pydantic "google-adk[a2a]"
    ```
    
4.  **Environment Variables**:
    Create a `.env` file in the root directory (or ensure relevant environment variables are set) containing your Google API key:
    ```env
    GOOGLE_API_KEY=your_google_api_key_here
    ```

## Running the Agent

### Locally

To start the agent server:

```bash
python src/server.py
```

By default, the server runs on `http://127.0.0.1:9009`.
You can customize the host and port using arguments:

```bash
python src/server.py --host 0.0.0.0 --port 8080
```

### Using Docker

1.  **Build the image**:
    ```bash
    docker build -t green-agent .
    ```

2.  **Run the container**:
    ```bash
    docker run -p 9009:9009 --env GOOGLE_API_KEY=your_api_key green-agent
    ```

## Usage as a Judge

The agent is designed to be called by an orchestration layer or directly via A2A protocol. It expects a JSON payload (Evaluator Request) with the following structure:

```json
{
  "participants": {
    "researcher_translator": "http://url-to-purple-agent"
  },
  "config": {
    "code_to_translate": "print('Hello World')",
    "source_language": "python",
    "target_language": "javascript"
  }
}
```

**The Workflow:**
1.  The Green Agent contacts the participant agent at the provided URL (`http://url-to-purple-agent`).
2.  It sends the `code_to_translate`, `source_language`, and `target_language` to the participant.
3.  It waits for the participant to return the translated code.
4.  Once received, the Green Agent constructs a prompt for the Gemini model (Judge), instructing it to evaluate the translation.
5.  It returns a result resembling:

```json
{
  "winner": "researcher_translator",
  "scores": [
    {
      "participant": "researcher_translator",
      "score": 9
    }
  ],
  "reasoning": "The translation is syntactically correct and preserves functionality..."
}
```

## Testing

To ensure the agent is functioning correctly, you can run the provided tests.

1.  **Install test dependencies** (if not already installed):
    ```bash
    pip install pytest pytest-asyncio
    ```

2.  **Run tests**:
    ```bash
    pytest tests/
    ```

    The `test_agent.py` contains:
    -   **Conformance Tests**: Verifies the Agent Card and A2A protocol structure (e.g., proper message formats, capabilities).
    -   **Message Validation**: Ensures that request and response payloads adhere to the defined schemas.