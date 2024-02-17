import streamlit as st

from utils.llm import CompletionStream, get_completion

st.title("Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if user_input := st.chat_input():
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    stream = CompletionStream(st.session_state.messages)
    with stream as response:
        reply = stream.completion = st.chat_message("assistant").write_stream(response)

    st.session_state.messages.append({"role": "assistant", "content": reply})

    # limit context window to last 10 messages
    while len(st.session_state.messages) > 10:
        st.session_state.messages.pop(0)

if st.sidebar.checkbox("Show current context window"):
    st.sidebar.json(st.session_state.messages, expanded=True)
