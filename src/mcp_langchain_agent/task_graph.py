import streamlit as st
import asyncio
import dotenv
import json
from langgraph.graph import StateGraph, END, add_messages
from langchain_core.runnables import RunnableLambda
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from pathlib import Path

from typing_extensions import TypedDict
from typing import Annotated

class State(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    input: str
    tool_executor: object  # the mcp agent
    result: str | dict     # response from the agent


dotenv.load_dotenv()

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
    print("State at fetch_mcp:", state)
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
            print("[DEBUG] MCP server is up and running.")
    except Exception as e:
        print("[ERROR] MCP server is not reachable:", e)
        raise

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
    # Return the tool_executor and ensure it is part of the state
    return {"tool_executor": agent, **state}

# Run the agent with the input
async def run_agent_node(state: State):
    # Print the state for debugging purposes
    print("State at run_mcp:", state)
    executor = state["tool_executor"]
    system_message = {"role": "system", "content": "You are a professional tutor specializing in teaching Sciris. Your goal is to create a detailed tutorial for users based on their queries. Assume the topic is always related to Sciris unless specified otherwise."}
    result = await executor.ainvoke(
        {"messages": [system_message, {"role": "user", "content": state["input"]}]}
    )
    return {"result": result, **state}

async def display_result(state: State):
     # Ensure response is parsed correctly and is a list of dictionaries
    if isinstance(state["result"], str):
        try:
            response = json.loads(state["result"])  # Parse steps if it's a JSON string
            for msg in response:
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

                else:
                    st.markdown(f"**❓ Unknown Message ({msg_type}):** {msg.content}")
        except json.JSONDecodeError:
            st.error("Failed to parse steps. Invalid JSON format returned.")
    return state
    

def build_async_graph():
    builder = StateGraph(State)
    
    builder.add_node("fetch_mcp", RunnableLambda(fetch_mcp_node))
    builder.add_node("run_mcp", RunnableLambda(run_agent_node))
    builder.add_node("display_result", RunnableLambda(display_result))
    builder.set_entry_point("fetch_mcp")
    builder.add_edge("fetch_mcp", "run_mcp")
    builder.add_edge("run_mcp", "display_result")
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

    # Create a Streamlit app
    st.title("Sciris Tutorial Generator")
    st.write("Ask a question about Sciris, and the AI will generate a tutorial for you.")

    # Text area for user query
    user_input = st.text_area("Ask a question:", height=100)

    # Submit button
    if st.button("Submit") and user_input.strip():
        # Show a waiting symbol while processing
        with st.spinner("Processing your request..."):
            response = asyncio.run(graph.ainvoke(State(messages=[], input=user_input)))