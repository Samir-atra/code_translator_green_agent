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
    "translator": "http://url-to-purple-agent"
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
5.  It returns a result that is saved to the leaderboard in the following format:

```json
{
  "participants": {
    "translator": "019b8933-d5b6-76a3-8e0b-930c19c10e87"
  },
  "results": [
    {
      "winner": "translator",
      "execution_correctness": 10.0,
      "style_score": 9.0,
      "conciseness": 9.33,
      "relevance": 10.0,
      "overall_score": 9.58,
      "reasoning": "The JavaScript translation successfully replicates the functionality of the Python code..."
    }
  ]
}
```

### Evaluation Metrics

| Metric | Description | Score Range |
|--------|-------------|-------------|
| **Execution Correctness** | Does the translated code produce the same output/behavior? | 0-10 |
| **Style Score** | Does the code follow idiomatic conventions of the target language? | 0-10 |
| **Conciseness** | Is the translation efficient without unnecessary verbosity? | 0-10 |
| **Relevance** | Does the translation preserve the original code's intent and logic? | 0-10 |
| **Overall Score** | Average of all four metrics | 0-10 |

## Testing

To ensure the agent is functioning correctly, you can run the provided tests.

### Unit Tests

1.  **Install test dependencies** (if not already installed):
    ```bash
    pip install pytest pytest-asyncio
    ```

2.  **Run tests**:
    ```bash
    pytest tests/test_agent.py
    ```

    The `test_agent.py` contains:
    -   **Conformance Tests**: Verifies the Agent Card and A2A protocol structure (e.g., proper message formats, capabilities).
    -   **Message Validation**: Ensures that request and response payloads adhere to the defined schemas.

### Integration Test

The `run_integration_test.py` script tests the full pipeline between the Green Agent (Judge) and Purple Agent (Participant):

```bash
python tests/run_integration_test.py
```

This script:
1. Starts both agents locally
2. Sends a code translation request to the Green Agent
3. The Green Agent communicates with the Purple Agent
4. Returns the evaluation result

### Leaderboard Test

The `run_leaderboard_test.py` script runs a full evaluation and generates a result JSON file compatible with the AgentBeats leaderboard:

```bash
python tests/run_leaderboard_test.py
```

This script:
1. Starts both agents locally
2. Sends multiple test cases for evaluation
3. Aggregates the scores
4. Generates a JSON file in the `results/` directory in the correct format for the leaderboard

## Related Repositories

This project is part of the **Code Translator** multi-agent evaluation system built for the [AgentBeats Competition](https://rdi.berkeley.edu/agentx-agentbeats.html). The complete system consists of:

| Repository | Description |
|------------|-------------|
| **[Code Translator Green Agent](https://github.com/Samir-atra/code_translator_green_agent)** (this repo) | The Judge agent that evaluates code translations |
| **[Code Translator Purple Agent](https://github.com/Samir-atra/code_translator_purple_agent)** | The participant agent that performs code translation |
| **[Code Translator Leaderboard](https://github.com/Samir-atra/code_translator_leaderboard)** | The leaderboard repository that records evaluation results |

### Live Leaderboard

View the live leaderboard at: **[AgentBeats - Code Translator Judge](https://agentbeats.dev/Samir-atra/code-translator-judge)**

### Docker Images

- **Green Agent**: `docker.io/samiratra95/code-translator-green-agent:latest`
- **Purple Agent**: `docker.io/samiratra95/code-translator-purple-agent:latest`

## References

- [AgentBeats Tutorial](https://github.com/RDI-Foundation/agentbeats-tutorial) - Official tutorial for building AgentBeats agents
- [Green Agent Template](https://github.com/RDI-Foundation/green-agent-template) - Template for green (judge) agents
- [Agent Template](https://github.com/RDI-Foundation/agent-template) - Template for purple (participant) agents
- [Leaderboard Template](https://github.com/RDI-Foundation/agentbeats-leaderboard-template) - Template for leaderboard repositories