# Prompts Directory

This directory contains all prompt templates used by the RAG Customer Support System.

## Files

### `agent_system_prompt.txt`
The main system prompt for the AI agent that processes customer emails. This defines the agent's behavior, tone, and constraints.

**Usage**: Loaded by `AgentService` to configure the LLM's behavior.

### `retriever_tool_description.txt`
Description for the retriever tool that the agent uses to search the knowledge base.

**Usage**: Loaded by `AgentService` when creating the retriever tool.

### `email_classification_prompt.txt`
Prompt used to classify incoming emails and determine if they should be processed by the agent or ignored.

**Usage**: Loaded by `AgentService` to filter emails before processing. The agent will only respond to emails classified as customer support inquiries.

## Experimenting with Prompts

You can freely edit these files to experiment with different prompts without modifying the code. Changes will take effect the next time the agent is started.

### Tips for Prompt Engineering:
- Be specific about the agent's role and constraints
- Define the expected tone (professional, friendly, etc.)
- Specify what to do when information is not available
- Include examples if needed for complex behaviors

## Configuration

The paths to these prompt files are configured in `app/config/__init__.py` and can be overridden via environment variables:
- `AGENT_SYSTEM_PROMPT_FILE`
- `RETRIEVER_TOOL_DESC_FILE`
