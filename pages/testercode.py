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
# Placeholder for the guest list to ensure it remains on the page
guest_list_placeholder = st.empty()


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
    # Debugging output
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
from utils.llm import (
    DEFAULT_FREQUENCY_PENALTY,
    DEFAULT_MAX_TOKENS,
    DEFAULT_N_PAST_MESSAGES,
    DEFAULT_PRESENCE_PENALTY,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    CompletionStream,
)

if 'guest_list' not in st.session_state:
    st.session_state['guest_list'] = []
    
def chatbot():
    # Initialize chatbot messages in session state if not already present
    if "chatbot_playground_messages" not in st.session_state:
        st.session_state.chatbot_playground_messages = [{"role": "system", "content": sys_message}]

    messages = st.session_state.chatbot_playground_messages

    # Display existing chatbot messages
    for message in messages:
        if message["role"] != "system":
            st.write(f"{message['role'].title()}: {message['content']}")

    # Capture and display user input
    user_input = st.text_input("Your message", key="chat_input")
    if user_input:
        messages.append({"role": "user", "content": user_input})
        st.session_state.chatbot_playground_messages = messages  # Update session state
        st.experimental_rerun()  # Rerun the app to clear the input box

def guestlist_generator():
    if st.button("Generate Guest List"):
        event_details = {
            'event_goal': event_goal,
            'event_topic': event_topic,
            'event_type': event_type
        }

        # Assuming get_llm_response_and_rank function exists and works as intended
        ranked_industries, ranked_designations = get_llm_response_and_rank(event_details, sys_message)

        num_invites = calculate_invites(event_size, show_up_rate)

        # Assuming assign_scores_and_filter function exists and works as intended
        filtered_guest_list = assign_scores_and_filter(df, ranked_industries, ranked_designations, num_invites)

        if filtered_guest_list.empty:
            guest_list_placeholder.write("No matching guests found based on the ranking criteria.")
        else:
            guest_list_placeholder.header(f"Tentative Guest List for {num_invites} Invites")
            guest_list_placeholder.dataframe(filtered_guest_list)

chatbot()
guestlist_generator()
