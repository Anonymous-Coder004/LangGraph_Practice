from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
import sqlite3 
load_dotenv()

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)
    return {"messages": [response]}
#DB creation
conn=sqlite3.connect(database='chatbot.db',check_same_thread=False) #false as we are going to same db for multiple threads ...db will be created if not exist in folder dir
# Checkpointer
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

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
