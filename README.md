# Code Translator Green Agent (Evaluator)

This repository contains the **Green Agent** for the Code Translator system. Built with the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/), this agent acts as the evaluator and orchestrator for code translation scenarios.

## Overview

The Green Agent is responsible for:
1.  **Orchestrating** the interaction between participant agents (Purple Agents).
2.  **Evaluating** the quality of code translations provided by participants.
3.  **Scoring** the submissions based on specific criteria.

### Evaluation Criteria
The agent uses `gemini-2.5-flash` to judge translations based on:
*   **Execution Correctness**: The code must run without errors.
*   **Style & Documentation**: Adherence to the target language's style guides and proper commenting.
*   **Conciseness**: Efficient code without unnecessary boilerplate.
*   **Relevance**: Logical and structural equivalence to the original code.

## Architecture

*   **Framework**: Google ADK (`google-adk[a2a]`)
*   **Model**: Gemini 2.5 Flash
*   **Communication**: Agent-to-Agent (A2A) Protocol
*   **Server**: Uvicorn + FastAPI (exposed via ADK)

## Prerequisites

*   Python 3.11+
*   [uv](https://github.com/astral-sh/uv) (recommended) or pip
*   Google GenAI API Key

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd code_translator_green_agent
    ```

2.  **Configure Environment:**
    Create a `.env` file in the root directory:
    ```bash
    GOOGLE_API_KEY=your_api_key_here
    ```

3.  **Install Dependencies:**
    Using `uv`:
    ```bash
    uv sync
    ```

## Running the Agent

### Local Execution
To run the agent server locally:

```bash
uv run src/server.py --host 0.0.0.0 --port 9009
```

The agent will be available at `http://localhost:9009`.

### Docker Execution
To build and run using Docker:

1.  **Build the image:**
    ```bash
    docker build -t code-translator-green .
    ```

2.  **Run the container:**
    ```bash
    docker run -p 9009:9009 --env-file .env code-translator-green
    ```

## Project Structure

*   `src/agent.py`: Defines the ADK Agent, system prompt, and evaluation logic.
*   `src/server.py`: Entry point for the HTTP server.
*   `src/tool_provider.py`: Tools for the agent (e.g., A2A communication).
*   `src/common.py`: Shared data models (e.g., `TranslatorEval` schema).