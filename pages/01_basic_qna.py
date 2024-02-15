import streamlit as st
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()
client = AzureOpenAI()

if user_input := st.text_input("Question: "):
    messages = [{"role": "user", "content": user_input}]
    response = client.chat.completions.create(
        model="gpt-35-turbo-16k", messages=messages
    )
    st.write(f"Answer: {response.choices[0].message.content}")
