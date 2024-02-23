import streamlit as st
from qna import load_qna


st.set_page_config(page_title="GenAI Hackathon 2024", page_icon="🤖", layout="centered")
st.image("poster.png")

load_qna()
