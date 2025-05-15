import sys
import asyncio
import anyio
import ast
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import json
import streamlit as st
import logging
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(filename='simple_app.log', encoding='utf-8', level=logging.INFO)
async def use_tool(query: str):
    # Explicitly set the current_path to the workspace root
    logger.info("Current working directory: %s", Path(__file__).parent.parent )
    # Calculate the path to the mcp_pack folder relative to the current file
    current_path = Path(__file__).resolve().parents[2] / "src/mcp_pack"
    logger.info("Current server directory: %s", current_path )
    async with MultiServerMCPClient(
        {
            "sciris": {
                "command": "uv",
                "args": ["run", str(Path(current_path, "server.py"))],
                "transport": "stdio",
            }
        }
    ) as client:
        agent = create_react_agent(
            "gpt-4o",
            client.get_tools()
        )
        # Add a system message to instruct the AI to act as a professional tutor
        system_message = {"role": "system", "content": "You are a professional tutor specializing in teaching Sciris. Your goal is to create a detailed tutorial for users based on their queries. Assume the topic is always related to Sciris unless specified otherwise."}

        response = await agent.ainvoke(
            {"messages": [system_message, {"role": "user", "content": query}]}
        )

    return response

def save_quarto_tutorial(final_response):
    """
    Save the final response content as a Quarto file and provide a download button.

    Args:
        final_response (str): The final response content to save.
    """
    # Use the provided Quarto template
    tutorial_content = final_response

    # Save the Quarto file
    quarto_file_path = Path("sciris_tutorial.qmd")
    with open(quarto_file_path, "w") as f:
        f.write(tutorial_content)

    # Provide a download button for the Quarto file
    # Generate a unique key for the download button to avoid duplicate element IDs
    with open(quarto_file_path, "rb") as f:
        st.download_button(
            label="Download Tutorial as Quarto File",
            data=f,
            file_name=quarto_file_path.name,
            mime="text/markdown",
            key=f"download-{quarto_file_path.name}"
        )

def clean_tool_content(content):
    """
    Tries to convert stringified lists (or other Python-like structures)
    into nicely formatted strings.
    """
    try:
        parsed = ast.literal_eval(content)
        if isinstance(parsed, list):
            # Join list items with line breaks
            return "\n\n".join(str(item) for item in parsed)
        return str(parsed)
    except Exception:
        return content  # Return as-is if it can't be parsed
    
def display_messages(messages):
    for msg in messages:
        msg_type = getattr(msg, "type", "unknown")

        if msg_type == "human":
            st.markdown(f"**🧑 Human:** {msg.content}")

        elif msg_type == "ai":
            st.markdown(f"**🤖 AI:** {msg.content if msg.content else '*[Working on it...]*'}")
            # Call the function to save the Quarto tutorial
            if msg.content:
                # Convert the message content to markdown text
                markdown_content = f"""---
title: "Sciris Tutorial"
author: "AI Tutor"
date: "April 30, 2025"
format: html
---

{msg.content}
"""
                save_quarto_tutorial(markdown_content)

            # Tool calls inside AIMessage
            tool_calls = msg.additional_kwargs.get("tool_calls", [])
            for call in tool_calls:
                name = call.get("function", {}).get("name", "unknown_function")
                args = call.get("function", {}).get("arguments", "{}")
                st.markdown(f"🔧 **Tool Call:** `{name}`")
                st.code(args, language="json")

        elif msg_type == "tool":
            st.markdown("**🛠️ Tool Response:**")
            st.code(clean_tool_content(msg.content), language="python")

        elif msg_type == "system":
            st.markdown(f"**🛠️ System Message:** {msg.content}")
        else:
            st.markdown(f"**❓ Unknown Message ({msg_type}):** {msg.content}")


async def main():
    # Initialize chat history in session state
    if "history" not in st.session_state:
        st.session_state.history = []

    st.title("Sciris Tutorial Generator")
    st.write("Ask a question about Sciris, and the AI will generate a tutorial for you.")

    # Text area for user query
    user_input = st.text_area("Ask a question:", height=100)

    # Submit button
    if st.button("Submit") and user_input.strip():
        # Run the conversation and collect steps
        response = await use_tool(user_input)

        # Ensure response is parsed correctly and is a list of dictionaries
        if isinstance(response, str):
            try:
                response = json.loads(response)  # Parse steps if it's a JSON string
            except json.JSONDecodeError:
                st.error("Failed to parse steps. Invalid JSON format returned.")
                return

        # Save user input and steps to session history, including tool responses
        st.session_state.history.extend(response["messages"])

    history_copy = list(st.session_state.history)
    logger.debug("History: %s", history_copy)
    
    display_messages(st.session_state.history)

if __name__ == '__main__':
    asyncio.run(main())
    # anyio.run(main, backend="asyncio")
