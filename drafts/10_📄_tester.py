# import tempfile
# from pathlib import Path
# import pandas as pd

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
    ".txt": TextLoader,
    ".md": TextLoader,
    ".pdf": PyMuPDFLoader,
}

QNA_TEMPLATE = """Use the following pieces of context to answer the question at the end

{context}

QUESTION: {question}

ANSWER:"""

SUMMARY_TEMPLATE = """Write a short summary based on the following

{context}

SUMMARY:"""

PARSING_TEMPLATE = """Parse the following context into a JSON with relevant keys

{context}

JSON:"""


def build_messages(system_message: str, updated_input: str):
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": updated_input},
    ]


import tempfile
from pathlib import Path
import pandas as pd
import re
import streamlit as st
from utils.llm import CompletionStream, get_completion

from scripts.testdata import outputjson
from utils.llm import CompletionStream


st.title("Guest Lists Generator")

# Load the guest list from a CSV file
guest_list = "Dataset.csv"
df = pd.read_csv(guest_list)

industry_keywords = ['investment', 'real estate', 'aviation', 'security', 'banking', 'infrastructure', 'food/agriculture', 'media/entertainment', 'energy utility', 'logistics', 'aviation', 'engineering', 'urban development', 'healthcare', 'biotech', 'sustainability', 'cybersecurity', 'technology']
designation_keywords = ['board member', 'ceo', 'chairman', 'ned', 'secretary', 'treasurer', 'vice president']


# Sidebar inputs for event details
with st.sidebar:
    sys_message = st.text_area("System message", value="You are a helpful assistant.")
    event_goal = st.text_input("Event Goal")
    event_topic = st.text_input("Event Topic")
    event_type = st.selectbox("Event Type", ["Conference", "Workshop", "Seminar", "Networking"])
    event_size = st.number_input("Desired Event Size", value=100, min_value=1)
    show_up_rate = st.slider("Expected Show-up Rate (%)", min_value=1, max_value=100, value=60)

def calculate_invites(event_size, show_up_rate):
    return int(event_size / (show_up_rate / 100.0))


def parse_llm_ranking_response(llm_response, keywords):
    # Convert the response and keywords to lowercase for case-insensitive matching
    response_lower = llm_response.lower()
    keywords_lower = [keyword.lower() for keyword in keywords]

    # Initialize a dictionary to hold the keywords and their positions in the response
    keyword_positions = {keyword: response_lower.find(keyword) for keyword in keywords_lower}

    # Filter out keywords not found in the response
    found_keywords = {k: v for k, v in keyword_positions.items() if v != -1}

    # Sort the found keywords by their position in the response, assuming earlier mention implies higher relevance
    sorted_keywords = sorted(found_keywords, key=found_keywords.get)

    # Convert the sorted list back to the original case of the keywords
    ranked_keywords = [keywords[keywords_lower.index(keyword)] for keyword in sorted_keywords]

    return ranked_keywords


def get_llm_response_and_rank(event_details, industry_keywords, designation_keywords, sys_message):
    # Formulate questions for ranking industries and designations
    industry_question = f"Rank the following industries based on their relevance to a {event_details['event_type']} about {event_details['event_topic']} with the goal of {event_details['event_goal']}: {', '.join(industry_keywords)}."
    designation_question = f"Rank the following designations based on their importance for the same event: {', '.join(designation_keywords)}."

    # Get LLM response for industries
    industry_response = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": industry_question}]).choices[0].message.content
    # Parse the response to extract the ranking
    ranked_industries = parse_llm_ranking_response(industry_response, industry_keywords)

    # Get LLM response for designations
    designation_response = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": designation_question}]).choices[0].message.content
    # Parse the response to extract the ranking
    ranked_designations = parse_llm_ranking_response(designation_response, designation_keywords)

    return ranked_industries, ranked_designations

def assign_scores_and_filter(df, ranked_industries, ranked_designations, num_invites):
    # Debugging output\
    
    st.write("Ranked Industries:", ranked_industries)
    st.write("Ranked Designations:", ranked_designations)

    # Create dictionaries for industries and designations with their rankings
    industry_rank_dict = {industry.lower(): rank for rank, industry in enumerate(ranked_industries, 1)}
    designation_rank_dict = {designation.lower(): rank for rank, designation in enumerate(ranked_designations, 1)}
    

    # Assign scores to each row in the DataFrame based on industry and designation rankings
    def get_row_score(row):
        industry_score = industry_rank_dict.get(row['Industry'].lower(), len(ranked_industries) + 1)
        designation_score = designation_rank_dict.get(row['Designation'].lower(), len(ranked_designations) + 1)
        return industry_score + designation_score  # Lower score is better

    # Apply the scoring function to each row
    df['Score'] = df.apply(get_row_score, axis=1)

    

    # Debugging output: Display a sample of the DataFrame after scoring
    st.write("Sample of scored DataFrame:", df.head(10)) 

    # Sort the DataFrame by score and select the top entries based on num_invites
    filtered_df = df.sort_values(by='Score').head(num_invites)

    return filtered_df

# Button to generate the guest list
if st.button("Generate Guest List"):
    # Get the event details from the user input
    event_details = {
        'event_goal': event_goal,
        'event_topic': event_topic,
        'event_type': event_type
    }
    # Obtain the ranked industries and designations based on the LLM response
    ranked_industries, ranked_designations = get_llm_response_and_rank(event_details, industry_keywords, designation_keywords, sys_message)

    num_invites = calculate_invites(event_size, show_up_rate)
    if "indus" not in st.session_state:
        st.session_state.indus = []

    if "role" not in st.session_state:
        st.session_state.role = []
    
    # Filter the guest list based on the rankings and number of invites
    filtered_guest_list = assign_scores_and_filter(df, ranked_industries, ranked_designations, num_invites)

    
    st.session_state.indus = ranked_industries

    st.session_state.role = ranked_designations

    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = []
    messages = st.session_state.chatbot_messages  # alias as shorthand

    prompt1 = """Convert the following data delimited by triple ticks to a industry ranked list: ```{data}``` """
    prompt2 = """Convert the following data delimited by triple ticks to a ranked list with title role ranked list: ```{data}``` """

    

    industrylist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt1.format(data = st.session_state.indus)}]).choices[0].message.content

    rolelist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt2.format(data = st.session_state.role)}]).choices[0].message.content


    messages.append({"role": "assistant", "content": industrylist})
    messages.append({"role": "assistant", "content": rolelist})

    if filtered_guest_list.empty:
        st.write("No matching guests found based on the ranking criteria.")
    else:
        st.header(f"Tentative Guest List for {num_invites} Invites")
        st.dataframe(filtered_guest_list)



st.title("Chatbot")


if "chatbot_messages" not in st.session_state:
    st.session_state.chatbot_messages = []
messages = st.session_state.chatbot_messages  # alias as shorthand



for message in messages:
    st.chat_message(message["role"]).write(message["content"])

if user_input := st.chat_input():
    st.chat_message("user").write(user_input)
    messages.append({"role": "user", "content": user_input})

    stream = CompletionStream(messages)
    with stream as response:
        stream.completion = str(st.chat_message("assistant").write_stream(response))
    messages.append({"role": "assistant", "content": stream.completion}) 
    

    while len(messages) > 50:  # limit context window by removing the earliest
        messages.pop(0)

    

# def assign_scores_and_filter(df, ranked_industries, ranked_designations, num_invites):
#     # Create dictionaries for industries and designations with their rankings
#     industry_rank_dict = {industry: rank for rank, industry in enumerate(ranked_industries, 1)}
#     designation_rank_dict = {designation: rank for rank, designation in enumerate(ranked_designations, 1)}

#     # Assign scores to each row in the DataFrame based on industry and designation rankings
#     def get_row_score(row):
#         industry_score = industry_rank_dict.get(row['Industry'], len(ranked_industries) + 1)  # Default score if not found
#         designation_score = designation_rank_dict.get(row['Designation'], len(ranked_designations) + 1)  # Default score if not found
#         return industry_score + designation_score  # Lower score is better

#     # Apply the scoring function to each row
#     df['Score'] = df.apply(get_row_score, axis=1)

#     # Sort the DataFrame by score and select the top entries based on num_invites
#     filtered_df = df.sort_values(by='Score').head(num_invites)

#     return filtered_df


# if st.button("Generate Guest List"):
#     # Get the event details from the user input
#     event_details = {
#         'event_goal': event_goal,
#         'event_topic': event_topic,
#         'event_type': event_type
#     }

#     # Obtain the ranked industries and designations based on the LLM response
#     ranked_industries, ranked_designations = get_llm_response_and_rank(event_details, industry_keywords, designation_keywords, sys_message)

#     # Calculate the number of invites based on the event size and expected show-up rate
#     num_invites = calculate_invites(event_size, show_up_rate)

#     # Filter the guest list based on the rankings and number of invites
#     filtered_guest_list = assign_scores_and_filter(df, ranked_industries, ranked_designations, num_invites)

#     if filtered_guest_list.empty:
#         st.write("No matching guests found based on the ranking criteria.")
#     else:
#         st.header(f"Tentative Guest List for {num_invites} Invites")
#         st.dataframe(filtered_guest_list)
# else:
#     st.write("Enter event details and expected attendance to generate a guest list.")








# file_raw_text = ""
# with st.sidebar:
#     sys_message = st.text_area("System message", value="You are a helpful assistant.")
#     if uploaded_file := st.file_uploader(
#         "Upload a file",
#         type=["docx", "txt", "md", "pdf"],
#         accept_multiple_files=False,
#     ):
#         # if accept_multiple_files=True, uploaded_files has to be handled differently esp for mixed file types
#         file_type = Path(uploaded_file.name).suffix.lower()
#         doc_loader = FILETYPE_TO_DOCLOADER[file_type]

#         # convert uploaded_file(BytesIO) back into a temp file to be read by loader
#         with tempfile.NamedTemporaryFile(delete=False) as f:
#             f.write(uploaded_file.read())
#             f.flush()
#             documents = doc_loader(f.name).load()
#             file_raw_text = "".join(doc.page_content for doc in documents)

# tabs = st.tabs(["File Content", "Q&A", "Summary", "Parsing"])

# with tabs[0]:
#     if st.checkbox("Apply Markdown formatting"):
#         st.write(file_raw_text)
#     else:
#         file_raw_text = st.text_area("Context", value=file_raw_text, height=360)
#     st.write(f"Contains `{num_tokens_from_string(file_raw_text):,}` tokens")

# with tabs[1]:
#     qna_prompt = st.text_area("Q&A prompt", value=QNA_TEMPLATE, height=190)
#     if user_input := st.text_input("Question: "):
#         updated_input = qna_prompt.format(question=user_input, context=file_raw_text)
#         st.write("Answer:")
#         messages = build_messages(sys_message, updated_input)
#         stream = CompletionStream(messages)
#         with stream as response:
#             stream.completion = str(st.write_stream(response))

# with tabs[2]:
#     summary_prompt = st.text_area("Summary prompt", value=SUMMARY_TEMPLATE, height=150)
#     if st.button("Summarize"):
#         updated_input = summary_prompt.format(context=file_raw_text)
#         messages = build_messages(sys_message, updated_input)
#         stream = CompletionStream(messages)
#         with stream as response:
#             stream.completion = str(st.write_stream(response))

# with tabs[3]:
#     parsing_prompt = st.text_area(
#         "Parsing data prompt", value=PARSING_TEMPLATE, height=150
#     )
#     if st.button("Format"):
#         updated_input = parsing_prompt.format(context=file_raw_text)
#         messages = build_messages(sys_message, updated_input)
#         response = get_completion(messages)
#         st.json(response.choices[0].message.content)
