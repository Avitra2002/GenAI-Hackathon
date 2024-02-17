import streamlit as st

from utils.llm import (
    DEFAULT_FREQUENCY_PENALTY,
    DEFAULT_MAX_TOKENS,
    DEFAULT_N_PAST_MESSAGES,
    DEFAULT_PRESENCE_PENALTY,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    CompletionStream,
    get_completion,
)

st.title("Chatbot Playground")


def clear_messages():
    if "chatbot_playground_messages" in st.session_state:
        del st.session_state["chatbot_playground_messages"]


with st.sidebar:
    system_message = st.text_area(
        "System message", value="You are a helpful assistant.", on_change=clear_messages
    )
    n_past_messages = st.slider(
        "Include past messages",
        value=DEFAULT_N_PAST_MESSAGES,
        min_value=1,
        max_value=21,
        step=2,
    )
    with st.expander("Parameters"):
        max_tokens = st.slider(
            "Max response", value=DEFAULT_MAX_TOKENS, min_value=1, max_value=1600
        )
        temperature = st.slider(
            "Temperature", value=DEFAULT_TEMPERATURE, min_value=0.0, max_value=2.0
        )
        top_p = st.slider("Top P", value=DEFAULT_TOP_P, min_value=0.0, max_value=1.0)
        frequency_penalty = st.slider(
            "Frequency Penalty",
            value=DEFAULT_FREQUENCY_PENALTY,
            min_value=-2.0,
            max_value=2.0,
        )
        presence_penalty = st.slider(
            "Presence Penalty",
            value=DEFAULT_PRESENCE_PENALTY,
            min_value=-2.0,
            max_value=2.0,
        )


if "chatbot_playground_messages" not in st.session_state:
    st.session_state.chatbot_playground_messages = [
        {"role": "system", "content": system_message}
    ]
messages = st.session_state.chatbot_playground_messages

for message in messages:
    st.chat_message(message["role"]).write(message["content"])

if user_input := st.chat_input():
    st.chat_message("user").write(user_input)
    messages.append({"role": "user", "content": user_input})

    stream = CompletionStream(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
    )
    with stream as response:
        reply = stream.completion = st.chat_message("assistant").write_stream(response)

    messages.append({"role": "assistant", "content": reply})

    # limit context window
    while len(messages) > n_past_messages:
        messages.pop(1)  # preserve system message at index 0
