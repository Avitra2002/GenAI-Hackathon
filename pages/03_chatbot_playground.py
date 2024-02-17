import streamlit as st

from utils.llm import (DEFAULT_FREQUENCY_PENALTY, DEFAULT_MAX_TOKENS,
                       DEFAULT_PRESENCE_PENALTY, DEFAULT_TEMPERATURE,
                       DEFAULT_TOP_P, CompletionStream, get_completion)

DEFAULT_K_PAST_MESSAGES = 11


st.title("Chatbot Playground")


def reset():
    if "messages" in st.session_state:
        del st.session_state["messages"]


with st.sidebar:
    system_message = st.text_area(
        "System message", value="You are a helpful assistant.", on_change=reset
    )
    with st.expander("Parameters to tweak"):
        max_response = st.number_input(
            "Max response",
            value=DEFAULT_MAX_TOKENS,
            min_value=1,
            max_value=1600,
            help=(
                "Set a limit on the number of tokens per model response. "
                "The API supports a maximum of MaxTokensPlaceholderDoNotTranslate tokens shared between "
                "the prompt (including system message, examples, message history, and user query) "
                "and the model's response. One token is roughly 4 characters for typical English text."
            ),
        )
        temperature = st.number_input(
            "Temperature",
            value=DEFAULT_TEMPERATURE,
            min_value=0.0,
            max_value=1.0,
            help=(
                "Controls randomness. Lowering the temperature means that the model will produce more repetitive "
                "and deterministic responses. Increasing the temperature will result in more unexpected or creative responses. "
                "Try adjusting temperature or Top P but not both."
            ),
        )
        top_p = st.number_input(
            "Top P",
            value=DEFAULT_TOP_P,
            min_value=0.0,
            max_value=1.0,
            help=(
                "Similar to temperature, this controls randomness but uses a different method. "
                "Lowering Top P will narrow the model’s token selection to likelier tokens. "
                "Increasing Top P will let the model choose from tokens with both high and low likelihood. "
                "Try adjusting temperature or Top P but not both."
            ),
        )
        frequency_penalty = st.number_input(
            "Frequency Penalty",
            value=DEFAULT_FREQUENCY_PENALTY,
            min_value=0.0,
            max_value=1.0,
            help=(
                "Reduce the chance of repeating a token proportionally based on how often it has appeared in the text so far. "
                "This decreases the likelihood of repeating the exact same text in a response."
            ),
        )
        presence_penalty = st.number_input(
            "Presence Penalty",
            value=DEFAULT_PRESENCE_PENALTY,
            min_value=0.0,
            max_value=1.0,
            help=(
                "Reduce the chance of repeating any token that has appeared in the text at all so far. "
                "This increases the likelihood of introducing new topics in a response."
            ),
        )
    k_past_messages = st.slider(
        "Include past messages",
        value=DEFAULT_K_PAST_MESSAGES,
        min_value=1,
        max_value=21,
        step=2,
        help=(
            "Select the number of past messages to include in each new API request. "
            "This helps give the model context for new user queries. "
            "Setting this number to 10 will include 5 user queries and 5 system responses."
        ),
    )


if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": system_message}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if user_input := st.chat_input():
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    stream = CompletionStream(
        messages=st.session_state.messages,
        max_tokens=max_response,
        temperature=temperature,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
    )
    with stream as response:
        reply = stream.completion = st.chat_message("assistant").write_stream(response)

    st.session_state.messages.append({"role": "assistant", "content": reply})

    # limit context window
    while len(st.session_state.messages) > k_past_messages:
        st.session_state.messages.pop(1)


if st.sidebar.checkbox("Show current context window"):
    st.sidebar.json(st.session_state.messages, expanded=True)
