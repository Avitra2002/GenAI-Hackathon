import streamlit as st

from utils.llm import get_completion, CompletionStream

is_streaming = st.sidebar.checkbox("Stream reply?")

if user_input := st.text_input("Question: "):
    messages = [{"role": "user", "content": user_input}]

    if is_streaming:
        stream = CompletionStream(messages)
        with stream as response:
            stream.completion = st.write_stream(response)
    else:
        response = get_completion(messages)
        st.write(f"Answer: {response.choices[0].message.content}")
