import streamlit as st

from utils.llm import CompletionStream, get_completion

st.title("Chatbot")

if "chatbot_messages" not in st.session_state:
    st.session_state.chatbot_messages = []
messages = st.session_state.chatbot_messages  # alias as shorthand

for message in messages:
    st.chat_message(message["role"]).write(message["content"])

if user_input := st.chat_input():
    st.chat_message("user").write(user_input)
    messages.append({"role": "user", "content": user_input})

    stream = CompletionStream(messages)
    with stream as response:
        stream.completion = st.chat_message("assistant").write_stream(response)
    messages.append({"role": "assistant", "content": stream.completion})

    # limit context window
    while len(messages) > 10:
        messages.pop(0)
