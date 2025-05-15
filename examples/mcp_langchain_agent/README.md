# LangChain MCP Client Example

This folder contains examples and utilities for using the MCP (Model Context Protocol) client with LangChain adapters. The MCP client enables seamless integration with LangChain tools, allowing for orchestrating AI-driven workflows and state management.

## Overview

The MCP LangChain adapter provides a way to connect LangChain tools to MCP servers. It facilitates communication between AI models and external tools, enabling dynamic workflows and stateful interactions.

[LangChain MCP Adapters GitHub Repository](https://github.com/langchain-ai/langchain-mcp-adapters)

## Folder Structure

- `app.py`: The main application file demonstrating how to use the MCP client with LangGraph tools using FastAPI.
- `ui.py`: A simple streamlit UI example for interacting with the MCP client impleneted in app.py.
- `config.py`: Configuration file for setting up MCP servers and other application settings.
- `basic_example.py`: A basic example demonstrating the usage of the MCP client without UI, you can start by running this to test if your environment is setting up correctly.
- `simple_mcp_client_example.py`: A minimal example for connecting to an local MCP server using stdio transport.


## Setting Up the Application

 The `.devcontainer/mcp_client_example` folder includes configuration files for setting up the environment. You should be able to start a codespace with all the components running. 

## Architecture

![Design Graph](graphs/design.png)

## Usage

See [postStartCommand.sh](.devcontainer/mcp_client_example/postStartCommand.sh) for details.

### Customizing Configurations
Edit the `config.py` file to update MCP  server configurations and other settings.
