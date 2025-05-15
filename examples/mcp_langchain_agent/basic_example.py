from pathlib import Path
import asyncio
import dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_openai import ChatOpenAI
model = ChatOpenAI(model="gpt-4o")

dotenv.load_dotenv()
current_path = Path(__file__).resolve().parents[2]/ "src/mcp_pack"
async def main():
    async with MultiServerMCPClient(
        {
            "codebase": {
                            "command": "uv",
                            "args": ["run", str(Path(current_path, "server.py"))],
                            "transport": "stdio",
                        }
        }
    ) as client:
        tools = client.get_tools()
        def call_model(state: MessagesState):
            response = model.bind_tools(tools).invoke(state["messages"])
            return {"messages": response}

        builder = StateGraph(MessagesState)
        builder.add_node(call_model)
        builder.add_node(ToolNode(tools))
        builder.add_edge(START, "call_model")
        builder.add_conditional_edges(
            "call_model",
            tools_condition,
        )
        builder.add_edge("tools", "call_model")
        graph = builder.compile()
        # graph.get_graph().print_ascii()
        response = await graph.ainvoke({"messages": """use starsim to simulate the covid 19 transmission in a 
        population of 1000 people with 10% infected and 10% vaccinated. Use the default parameters for the simulation.
                                             """
                                             })
        print(response)
        
if __name__ == "__main__":
    asyncio.run(main())
