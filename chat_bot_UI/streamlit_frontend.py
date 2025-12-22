import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage

CONFIG = {'configurable': {'thread_id': 'thread-1'}} # for persistance implementation
# st.session_state is a type of dictionary only but its value don't gets erased upon rerunning of script by pressing enter...it only gets refreshed or erased on manual reload of page
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = [] #heresession_state is dictionary and in it a list is created called message_history

for msg in st.session_state['message_history']:
    with st.chat_message(msg['role']):
        st.text(msg['content'])

user_input=st.chat_input('Type here')
if(user_input):
    st.session_state['message_history'].append({'role':'human','content':user_input})
    with st.chat_message('user'):
        st.text(user_input)

    response = chatbot.invoke({'messages': [HumanMessage(content=user_input)]}, config=CONFIG)
    ai_message = response['messages'][-1].content

    st.session_state['message_history'].append({'role':'ai','content':ai_message})
    with st.chat_message('ai'):
        st.text(ai_message)