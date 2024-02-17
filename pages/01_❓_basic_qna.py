import streamlit as st

from utils.llm import get_completion

if user_input := st.text_input("Question: "):
    messages = [{"role": "user", "content": user_input}]

    response = get_completion(messages)
    st.write(f"Answer: {response.choices[0].message.content}")
