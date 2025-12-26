from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from dotenv import load_dotenv
import sqlite3
import requests 
load_dotenv()

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')

# Tools functions
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}




@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
    r = requests.get(url)
    return r.json()



tools = [search_tool, get_stock_price, calculator]
llm_with_tools = llm.bind_tools(tools)
 
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    """LLM node that may answer or request a tool call."""
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools) #tools node

#DB creation
conn=sqlite3.connect(database='chatbot.db',check_same_thread=False) #false as we are going to same db for multiple threads ...db will be created if not exist in folder dir
# Checkpointer
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")

graph.add_conditional_edges("chat_node",tools_condition)
graph.add_edge('tools', 'chat_node')

chatbot = graph.compile(checkpointer=checkpointer)

def retrieve_all_threads():
    thread_first_seen = {}

    for checkpoint in checkpointer.list(None):  #.list command will extract all checkpoints in db if instead of none thread id is provided then it will give all checkpoint of that thread_id 
        thread_id = checkpoint.config['configurable']['thread_id']
        ts = checkpoint.checkpoint.get("ts")

        # fallback if ts missing (older versions)
        if ts is None:
            ts = checkpoint.checkpoint.get("timestamp", 0)

        # store earliest timestamp per thread
        if thread_id not in thread_first_seen:
            thread_first_seen[thread_id] = ts
        else:
            thread_first_seen[thread_id] = min(thread_first_seen[thread_id], ts)

    # sort threads by creation time
    sorted_threads = sorted(
        thread_first_seen.items(),
        key=lambda x: x[1]
    )

    # return only thread_ids, ordered
    return [thread_id for thread_id, _ in sorted_threads]
