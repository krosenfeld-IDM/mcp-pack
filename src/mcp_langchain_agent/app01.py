from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
import asyncio
import dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

model = ChatOpenAI(model="gpt-4o")
sciris_url = "http://localhost:8001/sse" 
starsim_url = "http://localhost:8002/sse"

dotenv.load_dotenv()
current_path = Path(__file__).resolve().parent.parent / "mcp_pack"

# Mount static files for serving Mermaid.js
# app.mount("/static", StaticFiles(directory="static"), name="static")

class QueryRequest(BaseModel):
    query: str
    selected_lib: str

@app.post("/get-response")
async def get_response(request: QueryRequest):
    async with MultiServerMCPClient(
        {
            # "git-help-quicj": {
            #     "command": "uv",
            #     "args": ["run", str(Path(current_path, "server.py"))],
            #     "transport": "stdio",
            # }

            "sciris": {
                "url": sciris_url,
                "transport": "sse",
            },
            "starsim": {
                "url": starsim_url,
                "transport": "sse",
            }
        }
    ) as client:
        tools = client.get_tools()

        def call_model(state: MessagesState):
            response = model.bind_tools(tools).invoke(state["messages"])
            return {"messages": response}

        def generate_quarto(state: MessagesState):
            """
            Save the final response content as a Quarto file and provide a download button.
            """
            # Use the provided Quarto template
            tutorial_content = state["messages"][-1].content
            markdown_content = f"""---\ntitle: "Tutorial"\nauthor: "AI Tutor"\ndate: "April 30, 2025"\nformat: html\n---\n{tutorial_content}
            """
            markdown_content = HumanMessage(content=markdown_content, role="quarto")
            return {"messages": markdown_content}

        def route_formatting(state):
            last_message = state["messages"][-1]
            if getattr(last_message, "tool_calls", None):
                return "tools"
            return "generate_quarto"

        builder = StateGraph(MessagesState)
        builder.add_node(call_model)
        builder.add_node(ToolNode(tools))
        builder.add_node(generate_quarto)
        builder.add_edge(START, "call_model")
        builder.add_conditional_edges(
            "call_model",
            route_formatting,
        )
        builder.add_edge("tools", "call_model")
        # builder.add_edge("call_model", "generate_quarto")
        graph = builder.compile()

        # workaround for the dynamic conditional edge, since it cannot be drawn
        def custom_mermaid(builder):
            edges = list(builder.edges)  # only static ones
            mermaid = ["graph TD"]
            for source, target in edges:
                mermaid.append(f"    {source} --> {target}")
            
            # Add conditional branches manually
            mermaid.append("    call_model -.->|if need tools| tools")
            mermaid.append("    call_model -.->|else| generate_quarto")
            return "\n".join(mermaid)
        
        system_message = {"role": "system", 
                        "content": f"""You are a professional tutor specializing in teaching how to run Python code. 
                        Your goal is to create a detailed tutorial for users based on their queries. 
                        Provide runnable Python code, including setup and data generation, so the user can follow step by step.
                        you should use git-help-quicj tool to look for {request.selected_lib} python library to accomplish this task"""}
        input_messages=[ 
            system_message,
            {"role": "user", "content": request.query}
        ]
        response = await graph.ainvoke({"messages": input_messages})
        # mermaid_syntax = graph.get_graph().draw_mermaid()
        mermaid_syntax = custom_mermaid(builder)
        return {"response": response, "mermaid_syntax": mermaid_syntax}

