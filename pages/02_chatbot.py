import streamlit as st
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()
client = AzureOpenAI()

st.title("Chatbot")

if "chatbot_messages" not in st.session_state:
    st.session_state.chatbot_messages = []
msg_history = st.session_state.chatbot_messages

for msg in msg_history:
    st.chat_message(msg["role"]).write(msg["content"])

if user_input := st.chat_input("Question: "):
    st.chat_message("user").write(user_input)
    msg_history.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="gpt-35-turbo-16k", messages=msg_history, stream=True
    )
    reply = st.chat_message("assistant").write_stream(response)
    msg_history.append({"role": "assistant", "content": reply})
