from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
import asyncio
import dotenv
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import config

app = FastAPI()

model = ChatOpenAI(model="gpt-4o")

dotenv.load_dotenv()
current_path = Path(__file__).resolve().parent.parent / "mcp_pack"

logger = logging.getLogger(__name__)
logging.basicConfig(filename='app.log', encoding='utf-8', level=logging.INFO)
logger.info("============Starting FastAPI app...===============")

# Mount static files for serving Mermaid.js
# app.mount("/static", StaticFiles(directory="static"), name="static")

class QueryRequest(BaseModel):
    query: str
    selected_lib: str

@app.post("/get-response")
async def get_response(request: QueryRequest):
    async with MultiServerMCPClient(
      config.MCP_SERVERS
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
            tutorial_content = tutorial_content.replace("```python", "```{python}")
            markdown_content = f"""---\ntitle: "Tutorial"\nauthor: "AI Tutor"\ndate: "April 30, 2025"\nformat: html\n---\n{tutorial_content}
            """
            markdown_content = HumanMessage(content=markdown_content, role="quarto")
            return {"messages": markdown_content}

        def route_formatting(state: MessagesState):
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
        # builder.add_edge("generate_quarto", END)
        graph = builder.compile()

        # workaround for the dynamic tool in conditional edge, since it cannot be drawn
        # TODO: Investigate why the dynamic tool cannot be drawn
        def custom_mermaid(builder):
            edges = list(builder.edges)  # only static ones
            logger.info(f" edges: {builder.branches}")
            mermaid = ["graph TD"]
            for source, target in edges:
                logger.info(f" edges source: {source}, target: {target}")
                mermaid.append(f"    {source} --> {target}")
            # Add conditional branches manually
            mermaid.append("    call_model -.->|if need tools| tools")
            mermaid.append("    call_model -.->|else| generate_quarto")
            return "\n".join(mermaid)
        
        system_message = {"role": "system", 
                        "content": f"""You are a professional tutor specializing in teaching how to run Python code. 
                        Your goal is to create a detailed tutorial for users based on their queries. 
                        Provide runnable Python code, including setup (use magic %pip install inside python code block) and data generation, so the user can follow step by step.
                        you should use {request.selected_lib} python library to accomplish this task"""}
        input_messages=[ 
            system_message,
            {"role": "user", "content": request.query}
        ]
        response = await graph.ainvoke({"messages": input_messages})
        # mermaid_syntax = graph.get_graph().draw_mermaid()
        mermaid_syntax = custom_mermaid(builder)
        return {"response": response, "mermaid_syntax": mermaid_syntax}

