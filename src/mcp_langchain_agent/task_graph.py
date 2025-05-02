import streamlit as st
import asyncio
import dotenv
import json
import ast
import logging
from langgraph.graph import StateGraph, END, add_messages
from langchain_core.runnables import RunnableLambda
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from pathlib import Path
from mcp_pack.list_db import QdrantLister
from typing_extensions import TypedDict
from typing import Annotated

logger = logging.getLogger(__name__)
logging.basicConfig(filename='app.log', encoding='utf-8', level=logging.INFO)

dotenv.load_dotenv()
qdrant_url = 'http://localhost:6333'  

class State(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    input: str
    tool_executor: object  # the mcp agent
    result: str | dict     # response from the agent


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
        return content  # Return as-is 
    

# MCP fetch function
async def fetch_mcp_node(state: State):
    # Print the state for debugging purposes
    logger.info(f"State at fetch_mcp: {state['input']}")
    current_path = Path(__file__).resolve().parent.parent / "mcp_pack"
    
    # Health check to ensure MCP server is running
    try:
        async with MultiServerMCPClient(
            {
                "sciris": {
                    "command": "uv",
                    "args": ["run", str(Path(current_path, "server.py"))],
                    "transport": "stdio",
                }
            }
        ) as client:
            logger.info("MCP server is up and running.")
            agent = create_react_agent(
            "gpt-4o",
            client.get_tools()
        )
        system_message = {"role": "system", 
                        "content": "You are a professional tutor specializing in teaching how to run Python code. Your goal is to create a detailed tutorial for users based on their queries. Provide runnable Python code, including setup and data generation, so the user can follow step by step."}
        try:
            result = await agent.ainvoke(
                {"messages": [system_message, {"role": "user", "content": state["input"]}]}, 
                config={"timeout": 120}  # Set a timeout for the agent invocation
            )
        except asyncio.TimeoutError:
            logger.error("Timeout error while invoking the agent.")
            result = {"error": "Timeout error while invoking the agent."}  
    except Exception as e:
        logger.error("MCP server is not reachable:", e)
        raise
    return {"result": result, **state}    
     

async def display_result(state: State):
     # Ensure response is parsed correctly and is a list of dictionaries
    logger.info(f"State at display_result: {state['result']}")
    if state["result"]:
        try:
            response = state["result"]['messages'] # Parse steps if it's a JSON string
            logger.info(f"Total Response: {len(response)}")
            for msg in response:
                logger.info(f"Message: {msg}")
                msg_type = getattr(msg, "type", "unknown")
                logger.info(f"Message Type: {msg_type}")
                if msg_type == "human":
                    st.markdown(f"**🧑 Human:** {msg.content}")

                elif msg_type == "ai":
                    st.markdown(f"**🤖 AI:** {msg.content if msg.content else '*[Working on it...]*'}")
                    # Call the function to save the Quarto tutorial
                    if msg.content:
                        # Convert the message content to markdown text
                        markdown_content = f"""---
        title: "Tutorial"
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
        except Exception:
            st.error("Failed to parse steps. Invalid JSON format returned.")
    else:
        logger.error("Invalid response.")
    return state
    

def build_async_graph():
    builder = StateGraph(State)
    
    builder.add_node("fetch_mcp", RunnableLambda(fetch_mcp_node))
    builder.add_node("display_result", RunnableLambda(display_result))
    builder.set_entry_point("fetch_mcp")
    builder.add_edge("fetch_mcp", "display_result")
    builder.add_edge("display_result", END)
    
    # Debugging: Print the graph structure to verify edges
    print("Nodes:", builder.nodes)
    print("Edges:", builder.edges)
    
    return builder.compile()

if __name__ == "__main__":
    # Initialize the graph
    graph = build_async_graph()

    # Debugging: Output the Mermaid syntax to verify edge definitions
    # mermaid_syntax = graph.get_graph().draw_mermaid()
    # graph.get_graph().print_ascii()
    # Display the graph in the Streamlit sidebar using IPython's Image
    from IPython.display import Image
    graph_image = graph.get_graph().draw_mermaid_png()
    st.sidebar.image(graph_image, caption="MPC Workflow", use_container_width=True)

    try:
        qdrant_obj = QdrantLister(qdrant_url=qdrant_url)
        collections = qdrant_obj.list_collections()
        if collections:
            selected_lib = st.selectbox(
                "Select a python library to use for the tutorial:",
                collections
            )
            st.write(f"You selected: {selected_lib}")
        else:
            st.warning("No collections found in Qdrant, please check your Qdrant server.")
    except Exception as e:
        st.error(f"Error connecting to Qdrant: {e}")
        logger.error(f"Error connecting to Qdrant: {e}")
    finally:
        qdrant_obj.client.close()    

    # Create a Streamlit app
    st.title("Teach yourself! Tutorial Generator")
    st.write("Ask a question or give a scenario, and the AI will generate a tutorial for you.")

    # Text area for user query
    user_input = st.text_area("Ask a question:", height=100)

    # Submit button
    if st.button("Submit") and user_input.strip():
        # Show a waiting symbol while processing
        with st.spinner("Processing your request..."):
            response = asyncio.run(graph.ainvoke(State(messages=[], input=f"Use {selected_lib} tool: {user_input}")))