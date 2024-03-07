import streamlit as st

from utils.llm import CompletionStream

QNA_FILEPATH = "./data/hackathon_qa.md"
QNA_PROMPT = """You are an AI chatbot for the inaugural Gen AI Hackathon organized by Temasek and SUTD.
Your role is to assist students with technical questions to implement the prototype for the event.
Use the following pieces of context delimited by triple ticks to answer question at the end with respect to the context of the event.
If the answer is not in the context, please say you don't know and do not make suggestions.

```
{context}
```

Question: {question}"""


@st.cache_resource
def load_faq():
    with open(QNA_FILEPATH, "r") as f:
        return f.read()


def load_qna():
    if st.sidebar.toggle(" "):
        if user_input := st.text_input("Question:"):
            file_raw_text = load_faq()
            system_prompt = QNA_PROMPT.format(
                context=file_raw_text, question=user_input
            )
            messages = [{"role": "system", "content": system_prompt}]

            st.write("Answer:")
            stream = CompletionStream(messages)
            with stream as response:
                stream.completion = str(st.write_stream(response))
