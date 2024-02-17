import tempfile
from pathlib import Path

import streamlit as st
from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyMuPDFLoader,
    TextLoader,
)

from utils.llm import CompletionStream, get_completion
from utils.tokens import num_tokens_from_string

FILETYPE_TO_DOCLOADER = {
    ".docx": Docx2txtLoader,
    ".md": TextLoader,
    ".pdf": PyMuPDFLoader,
    ".txt": TextLoader,
}
QNA_TEMPLATE = """Use the following pieces of context to answer the question at the end

{context}

QUESTION: {question}

ANSWER:"""
SUMMARY_TEMPLATE = """Write a summary based on the following

{context}

SUMMARY:"""
PARSING_TEMPLATE = """Parse the following context into a JSON with relevant keys

{context}

JSON:"""


st.title("Prompt Documents")


file_raw_text = None
with st.sidebar:
    system_message = st.text_area(
        "System message", value="You are a helpful assistant."
    )
    if uploaded_file := st.file_uploader(
        "Upload a file",
        type=["docx", "txt", "md", "pdf"],
        accept_multiple_files=False,  # if accept_multiple_files enabled, uploaded_files has to be handled differently
    ):
        file_type = Path(uploaded_file.name).suffix.lower()
        doc_loader = FILETYPE_TO_DOCLOADER[file_type]

        with tempfile.NamedTemporaryFile() as f:
            f.write(uploaded_file.read())
            f.flush()
            documents = doc_loader(f.name).load()
            file_raw_text = "".join(doc.page_content for doc in documents)


if not file_raw_text:
    st.warning("Please upload a valid document first")
    st.stop()

tabs = st.tabs(["File Content", "Q&A", "Summary", "Parsing"])

with tabs[0]:
    if st.checkbox("Format Markdown"):
        st.write(file_raw_text)
    else:
        file_raw_text = st.text_area("Context", value=file_raw_text, height=360)
    st.write(f"Contains `{num_tokens_from_string(file_raw_text):,}` tokens")

with tabs[1]:
    qna_prompt = st.text_area("Q&A prompt", value=QNA_TEMPLATE, height=190)
    if user_input := st.text_input("Question: "):
        updated_input = qna_prompt.format(question=user_input, context=file_raw_text)

        st.write("Answer:")
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": updated_input},
        ]
        stream = CompletionStream(messages)
        with stream as response:
            stream.completion = st.write_stream(response)


with tabs[2]:
    summary_prompt = st.text_area("Summary prompt", value=SUMMARY_TEMPLATE, height=150)
    if st.button("Summarize"):
        updated_input = summary_prompt.format(context=file_raw_text)
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": updated_input},
        ]
        stream = CompletionStream(messages)
        with stream as response:
            stream.completion = st.write_stream(response)

with tabs[3]:
    parsing_prompt = st.text_area(
        "Parsing data prompt", value=PARSING_TEMPLATE, height=150
    )
    if st.button("Format"):
        updated_input = parsing_prompt.format(context=file_raw_text)
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": updated_input},
        ]

        response = get_completion(messages)
        st.json(response.choices[0].message.content)
