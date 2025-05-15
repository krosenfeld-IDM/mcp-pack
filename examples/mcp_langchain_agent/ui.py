import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import logging
import ast
from pathlib import Path
from mcp_pack.list_db import QdrantLister
logger = logging.getLogger(__name__)
logging.basicConfig(filename='ui.log', encoding='utf-8', level=logging.INFO)
logger.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.info("============Starting Streamlit app...===============")

server_endpoint = "http://localhost:8081/get-response"
qdrant_url = 'http://localhost:6333'  


def mermaid(code: str) -> None:
    """
    Render the Mermaid diagram in the Streamlit sidebar.
    """
    with st.sidebar:
        components.html(
            f"""
            <pre class="mermaid">
                {code}
            </pre>
            <script type="module">
                import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                mermaid.initialize({{ startOnLoad: true }});
            </script>
            """,
            height=600  # Adjust height as needed
        )

def display_result(response):
    """
    Display the response messages in a structured format.
    """

    # Ensure response is parsed correctly and is a list of dictionaries
    try:
        valid_json = json.dumps(response["messages"])
        messages = json.loads(valid_json)                  
        st.warning(f"Total Response: {len(messages)}")
    except json.JSONDecodeError:
        st.error("Failed to parse steps.")
        raise
    for msg in messages:
        logger.info(f"Message: {msg}")
        msg_type = msg.get( "type", "unknown")
        msg_content = msg.get("content", None)
        msg_additional_kwargs = msg.get("additional_kwargs", {})
        if msg_type == "human":
            if msg.get("role") == "quarto":
                # generate a download button for the msg content as tutorial.qmd
                # Save the Quarto file
                quarto_file_path = Path("my_tutorial.qmd")
                with open(quarto_file_path, "w") as f:
                    f.write(msg_content)

                with open(quarto_file_path, "rb") as f:
                    file_data = f.read()

                    st.download_button(
                        label="Download Tutorial as Quarto File",
                        data=file_data,
                        file_name=quarto_file_path.name,
                        mime="text/markdown",
                        key=f"download-{quarto_file_path.name}"
                    )
            else:    
                st.markdown(f"**🧑 Human:** {msg_content}")

        elif msg_type == "ai":
            st.markdown(f"**🤖 AI:** {msg_content if msg_content else '*[Working on it...]*'}")

            tool_calls = msg_additional_kwargs.get("tool_calls", [])
            for call in tool_calls:
                name = call.get("function", {}).get("name", "unknown_function")
                args = call.get("function", {}).get("arguments", "{}")
                st.markdown(f"🔧 **Tool Call:** `{name}`")
                st.code(args, language="json")

        elif msg_type == "tool":
            st.markdown("**🛠️ Tool Response:**")
            st.code(msg_content, language="python")

        elif msg_type == "system":
            st.markdown(f"**🛠️ System Message:** {msg_content}")
        else:
            st.markdown(f"**❓ Message ({msg_type}):** {msg_content}")

st.markdown("<h1 style='color:red;'>AITODIDACT!!!</h1>", unsafe_allow_html=True)
st.title("Teach yourself! Tutorial Generator")
st.write("Ask a question or give a scenario, and the AI will generate a tutorial for you.")

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


# Text area for user query in the sidebar
user_query = st.text_area("Ask a question:", height=100)

# Submit button remains in the main area
if st.button("Submit"):
    if user_query.strip():
        with st.spinner("Processing your request..."):
            try:
                # Send the query to the FastAPI endpoint
                response = requests.post(server_endpoint, json={"query": user_query, "selected_lib": selected_lib})
                if response.status_code == 200:
                    data = response.json()
                    # st.subheader("Raw Json Response:")
                    # st.json(data.get("response", {}))
                    st.subheader("LLM Workflow Response:")
                    display_result(data.get("response", []))
                    # Move the Mermaid graph rendering to the sidebar
                    mermaid_syntax = data.get("mermaid_syntax", "")
                    st.sidebar.subheader("Langgraph structure:")
                    mermaid(mermaid_syntax)
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to the API: {e}")
    else:
        st.warning("Please enter a question describe what you want to learn before submitting.")
