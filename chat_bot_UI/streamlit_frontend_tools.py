import streamlit as st
from langgraph_tool_backend import chatbot,retrieve_all_threads
from langchain_core.messages import HumanMessage,AIMessage,ToolMessage
import uuid 

#helper functions
def gen_thread_id(): #for generating new random thread id
    thread_id=uuid.uuid4()
    return thread_id

def reset_chat(): #will be called when new chat button is clicked
    thread_id=gen_thread_id()
    st.session_state['thread_id']=thread_id
    add_thread(st.session_state['thread_id'])

    st.session_state['message_history']=[]

def add_thread(thread_id):
    if 'thread_list' not in st.session_state:
        st.session_state['thread_list'] = [] 
    if not any(chat['id'] == thread_id for chat in st.session_state['thread_list']):
        chat_number = len(st.session_state['thread_list']) + 1 # creating label based on count
        label = f"Chat {chat_number}"
        st.session_state['thread_list'].append({'id': thread_id,'label': label})

def load_conversation(thread_id):
    return chatbot.get_state(config={'configurable': {'thread_id': thread_id}}).values.get("messages", []) # if message is present then it will return else it will return empty list [] in case of chat with no message 
#END

#Session Setup 
# st.session_state is a type of dictionary only but its value don't gets erased upon rerunning of script by pressing enter...it only gets refreshed or erased on manual reload of page
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = [] #here session_state is dictionary and in it a list is created called message_history
if 'thread_id' not in st.session_state:
    st.session_state['thread_id']=gen_thread_id()
if 'thread_list' not in st.session_state:
    raw_threads=retrieve_all_threads() #checking from all uniquee thread_id from db
    st.session_state['thread_list'] = [{'id': tid, 'label': f'Chat {i+1}'}for i, tid in enumerate(raw_threads)]
add_thread(st.session_state['thread_id'])
#CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}} # for persistance implementation
CONFIG = { #for better langsmith integration....tracing will be done according to thread_id
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {
            "thread_id": st.session_state["thread_id"]
        },
        "run_name": "chat_turn",
    }
#End

#Side Bar UI
st.sidebar.title('LangGraph ChatBot') 
if st.sidebar.button('New Chat'):
    reset_chat()
st.sidebar.header('Your Chats')
for chat in st.session_state['thread_list'][::]: #writing all thread_id in sidebar
    if st.sidebar.button(chat['label']):
        st.session_state['thread_id'] = chat['id']
        messages = load_conversation(chat['id'])

        temp_messages = [] #changing the format of msg history acc. to 'role':'human','content':text
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role='human'
            else:
                role='ai'
            temp_messages.append({'role': role, 'content': msg.content})
        st.session_state['message_history'] = temp_messages

#END

for msg in st.session_state['message_history']:
    with st.chat_message(msg['role']):
        st.text(msg['content'])

user_input=st.chat_input('Type here')
if(user_input):
    st.session_state['message_history'].append({'role':'human','content':user_input})
    with st.chat_message('user'):
        st.text(user_input)

    with st.chat_message("ai"):
        # Use a mutable holder so the generator can set/modify it
        status_holder = {"box": None}

        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                # Lazily create & update the SAME status container when any tool runs
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"🔧 Using `{tool_name}` …", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"🔧 Using `{tool_name}` …",
                            state="running",
                            expanded=True,
                        )

                # Stream ONLY assistant tokens
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        # Finalize only if a tool was actually used
        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="✅ Tool finished", state="complete", expanded=False
            )
    st.session_state['message_history'].append({'role':'ai','content':ai_message})