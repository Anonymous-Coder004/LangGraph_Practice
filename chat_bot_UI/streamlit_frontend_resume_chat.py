import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage
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
    st.session_state['thread_list']=[]
add_thread(st.session_state['thread_id'])
CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}} # for persistance implementation
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

    with st.chat_message('ai'):
        ai_message = st.write_stream( #st.write_stream is used to print values from gerneator obj
            message_chunk.content for message_chunk, metadata in chatbot.stream( #instead of invoke stream is used to call ..it will make a generator funtion
                {'messages': [HumanMessage(content=user_input)]},
                config= CONFIG,
                stream_mode= 'messages'
            )
        )
    st.session_state['message_history'].append({'role':'ai','content':ai_message})