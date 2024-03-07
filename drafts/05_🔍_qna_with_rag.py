import tempfile
from pathlib import Path

import streamlit as st
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.faiss import FAISS

from utils.llm import get_completion
from utils.tokens import num_tokens_from_string

FAISS_INDEX_DIR = "./data/faiss_index"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 128
QNA_TEMPLATE = """Use the following pieces of context to answer the question at the end

{context}

QUESTION: {question}

ANSWER:"""


@st.cache_resource
def load_embeddings():
    # equivalent to SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


embeddings = load_embeddings()
vector_store = None
file_raw_text = ""

st.title("Q&A on Documents with Retrieval-Augmented Generation (RAG)")


with st.sidebar:
    sys_message = st.text_area("System message", value="You are a helpful assistant.")
    if uploaded_file := st.file_uploader(
        "Upload a file", type=["pdf"], accept_multiple_files=False
    ):
        # if accept_multiple_files=True, uploaded_files has to be handled differently for loading and saving embeddings
        index_file = Path(f"{FAISS_INDEX_DIR}/{uploaded_file.name}.faiss")
        if index_file.exists():

            vector_store = FAISS.load_local(
                folder_path=FAISS_INDEX_DIR,
                embeddings=embeddings,
                index_name=uploaded_file.name,
            )
            st.success(f"{uploaded_file.name}.faiss in `{FAISS_INDEX_DIR}` loaded")

        top_k = st.slider("Top k chunk docs to use", value=3, min_value=1, max_value=5)

tab_file_content, tab_qna = st.tabs(["File Content", "Q&A"])

if uploaded_file is None:
    tab_file_content.write("Upload a pdf first!")
    tab_qna.write("Upload a pdf first!")
    st.stop()

with tab_file_content:
    if uploaded_file.type == "application/pdf":
        file_raw_text = ""
        with tempfile.NamedTemporaryFile() as f:
            f.write(uploaded_file.read())
            documents = PyMuPDFLoader(f.name).load()
            file_raw_text = "".join(page.page_content for page in documents)
            # if applicable, consider adding table extraction besides text extraction for improvements
            # https://artifex.com/blog/table-recognition-extraction-from-pdfs-pymupdf-python

    st.text_area("Context", value=file_raw_text, height=300)
    n_token = num_tokens_from_string(file_raw_text)
    st.write(f"Contains `{n_token:,}` tokens")

    if st.button("Chunk document, generate embeddings and save to vector store"):
        with st.spinner("Chunking, generating and saving..."):
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
            )
            chunked_docs = text_splitter.split_documents(documents)
            vector_store = FAISS.from_documents(chunked_docs, embeddings)
            vector_store.save_local(
                folder_path=FAISS_INDEX_DIR, index_name=uploaded_file.name
            )
            st.success(
                f"Generated {len(chunked_docs):,} chunks and saved embeddings to local vector store in {FAISS_INDEX_DIR}"
            )

with tab_qna:
    if not vector_store:
        st.write("Process uploaded pdf file first under the `File Content` tab!")
    else:
        qna_prompt = st.text_area("Q&A prompt", value=QNA_TEMPLATE, height=190)

        if user_input := st.text_area("Question"):
            context = ""
            docs_and_scores = vector_store.similarity_search_with_score(
                user_input, k=top_k
            )

            st.write("Answer:")
            if docs_and_scores:
                for doc, score in docs_and_scores:
                    context += f"\n{doc.page_content}"

                updated_input = qna_prompt.format(context=context, question=user_input)
                messages = [
                    {"role": "system", "content": sys_message},
                    {"role": "user", "content": updated_input},
                ]

                response = get_completion(messages)
                reply = response.choices[0].message.content
                st.write(reply.replace("$", r"\$"))  # fix dollar sign issue

                st.write("### Document chunks retrieved")
                for doc, score in docs_and_scores:
                    with st.expander(
                        label=f'Page: {doc.metadata["page"]+1}, Score: {score:.3f}',
                        expanded=False,
                    ):
                        st.text(doc.page_content)
