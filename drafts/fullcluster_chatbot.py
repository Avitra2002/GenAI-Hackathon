import tempfile
from pathlib import Path
import pandas as pd
import re
import streamlit as st
from utils.llm import CompletionStream, get_completion

@st.cache
def load_data(csv_file_path):
    return pd.read_csv(csv_file_path)

# Function to filter guests based on event criteria
def filter_guests(df, event_size):
    return df.sample(n=event_size)

st.title("Guest Lists Generator")

# Load the guest list from a CSV file
guest_list = "Dataset.csv"
df = pd.read_csv(guest_list)
industry_keywords = df['Industry'].unique().tolist()
designation_keywords = df['Designation'].unique().tolist()

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
    keyword_positions = {keyword: response_lower.find(keyword) for keyword in keywords_lower}
    found_keywords = {k: v for k, v in keyword_positions.items() if v != -1}
    sorted_keywords = sorted(found_keywords, key=found_keywords.get)
    ranked_keywords = [keywords[keywords_lower.index(keyword)] for keyword in sorted_keywords]
    return ranked_keywords

def get_llm_response_and_rank(event_details, industry_keywords, designation_keywords, sys_message):
    industry_question = f"Rank the following industries based on their relevance to a {event_details['event_type']} about {event_details['event_topic']} with the goal of {event_details['event_goal']}: {', '.join(industry_keywords)}."
    designation_question = f"Rank the following designations based on their importance for the same event: {', '.join(designation_keywords)}."
    industry_response = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": industry_question}]).choices[0].message.content
    ranked_industries = parse_llm_ranking_response(industry_response, industry_keywords)
    designation_response = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": designation_question}]).choices[0].message.content
    ranked_designations = parse_llm_ranking_response(designation_response, designation_keywords)
    return ranked_industries, ranked_designations

def extract_organization_type(designation):
    if 'TPC' in designation: return 'TPC'
    elif 'AUM' in designation: return 'AUM'
    elif 'smaller TPC' in designation: return 'smaller TPC'
    elif 'platform' in designation or "JV" in designation: return 'platform JV'
    elif 'TNE' in designation: return 'TNE'
    elif 'Union' in designation: return 'Union'
    else: return 'Other'

st.session_state.ranked_org_types = ['TPC', 'AUM', 'smaller TPC', 'platform JV', 'TNE', 'Union']

def cluster_and_sort_by_rank(df, ranked_industries, ranked_designations, ranked_org_types):
    df['OrgType'] = df['Designation'].apply(extract_organization_type).str.lower()
    ranked_org_types_lower = [org.lower() for org in ranked_org_types]
    ranked_designations_lower = [d.lower() for d in ranked_designations]
    ranked_industries_lower = [i.lower() for i in ranked_industries]
    org_type_rank_dict = {org: rank for rank, org in enumerate(ranked_org_types_lower, start=1)}
    designation_rank_dict = {desig: rank for rank, desig in enumerate(ranked_designations_lower, start=1)}
    industry_rank_dict = {ind: rank for rank, ind in enumerate(ranked_industries_lower, start=1)}
    df['OrgTypeRank'] = df['OrgType'].apply(lambda x: org_type_rank_dict.get(x, len(ranked_org_types_lower) + 1))
    df['DesignationRank'] = df['Designation'].str.lower().apply(lambda x: designation_rank_dict.get(x, len(ranked_designations_lower) + 1))
    df['IndustryRank'] = df['Industry'].str.lower().apply(lambda x: industry_rank_dict.get(x, len(ranked_industries_lower) + 1))
    sorted_df = df.sort_values(by=['OrgTypeRank', 'DesignationRank', 'IndustryRank'])
    return sorted_df.drop(columns=['OrgTypeRank', 'DesignationRank', 'IndustryRank'])

# Generate initial lists button
if st.button("Generate Initial Lists"):
    if "indus" not in st.session_state:
        st.session_state.indus = []

    if "role" not in st.session_state:
        st.session_state.role = []
    
    if "num_invites" in st.session_state:
        st.header(f"Clustered and Sorted Guest List for {int(st.session_state.num_invites)} people")
    else:
        st.header("Clustered and Sorted Guest List")

    event_details = {'event_goal': event_goal, 'event_topic': event_topic, 'event_type': event_type}
    ranked_industries, ranked_designations = get_llm_response_and_rank(event_details, industry_keywords, designation_keywords, sys_message)
    st.session_state.indus = ranked_industries
    st.session_state.role = ranked_designations
    st.session_state.num_invites = calculate_invites(event_size, show_up_rate)
    

    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = []
    messages = st.session_state.chatbot_messages  # alias as shorthand

    prompt1 = """Convert the following data delimited by triple ticks to a industry ranked list: ```{data}``` """
    # prompt2 = """Convert the following data delimited by triple ticks to a ranked list with title role ranked list: ```{data}``` """

    

    industrylist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt1.format(data = st.session_state.indus)}]).choices[0].message.content

    # rolelist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt2.format(data = st.session_state.role)}]).choices[0].message.content


    messages.append({"role": "assistant", "content": industrylist})
    # messages.append({"role": "assistant", "content": rolelist})

# Chatbot interaction section
st.subheader("Chatbot Interaction")
st.write("Review the ranked lists above. If you'd like to make changes, you can request them here.")

if "chatbot_messages" not in st.session_state:
    st.session_state.chatbot_messages = []
messages = st.session_state.chatbot_messages  # alias as shorthand



for message in messages:
    st.chat_message(message["role"]).write(message["content"])

if user_input := st.chat_input():
    st.chat_message("user").write(user_input)
    messages.append({"role": "user", "content": "Do not add or remove or change the names in the list but change the order based on the input :"+ user_input})

    stream = CompletionStream(messages)
    with stream as response:
        stream.completion = str(st.chat_message("assistant").write_stream(response))
    messages.append({"role": "assistant", "content": stream.completion}) 
    

    while len(messages) > 50:  # limit context window by removing the earliest
        messages.pop(0)

import ast
# Layout configuration using columns
left_col, right_col = st.columns(2)

if "filtered_guest_list" not in st.session_state:
    st.session_state.filtered_guest_list = pd.DataFrame()

industryformattedlist = []
roleformattedlist = []

# Using the left column for the indus list generation
with left_col:
# Button to generate the industry list
    if st.button("Final Industry List Generate"):
        pulledlist = messages[-1]["content"] #pulling the last message from chat session state
        formatprompt = "From the data delimited in triple ticks below, remove the top row of text that is not part of the list item, and convert the list format into a python list of strings, where each item represents one item in the list. Remove the numbers from each item. ```{pulled}```" 

        industryformattedlist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": formatprompt.format(pulled = pulledlist)}]).choices[0].message.content #using gpt to process the string into a python list
    # st.write(industryformattedlist)
        messages.append({"role": "assistant", "content": industryformattedlist})
    # st.chat_message("assistant").write(industryformattedlist)
        st.write("Okay! Now we need to confirm the Role list. Please go through the same steps, and clikc the Final Role List Generate button when ready.")

    # industryformattedlist 

        st.session_state.industry = industryformattedlist

        prompt2 = """Convert the following data delimited by triple ticks to a ranked list with title role ranked list: ```{data}``` """

        rolelist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt2.format(data = st.session_state.role)}]).choices[0].message.content

        messages.append({"role": "assistant", "content": rolelist})

        st.chat_message("assistant").write(rolelist)
        
with right_col:
# Button to generate the Role list
    if st.button("Final Role List Generate"):
        pulledlist = messages[-1]["content"] #pulling the last message from chat session state
        formatprompt = "From the data delimited in triple ticks below, remove the top row of text that is not part of the list item, and convert the list format into a python list of strings, where each item represents one item in the list. Remove the numbers from each item. ```{pulled}```" 

        roleformattedlist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": formatprompt.format(pulled = pulledlist)}]).choices[0].message.content #using gpt to process the string into a python list
    # st.write(roleformattedlist)
        messages.append({"role": "assistant", "content": roleformattedlist})
        st.chat_message("assistant").write(roleformattedlist)

        roleformattedlist = ast.literal_eval(roleformattedlist)
    # st.write(st.session_state.industry)
        industryformattedlist = ast.literal_eval(st.session_state.industry)
        st.session_state.roleformattedlist = ast.literal_eval(roleformattedlist)  # Convert the string to a list and store in session state

        st.write(roleformattedlist)
    

        # Cluster and sort the DataFrame based on the potentially updated ranked lists
    clustered_sorted_df = cluster_and_sort_by_rank(df, industryformattedlist, roleformattedlist, st.session_state.ranked_org_types)
    st.header(f"Clustered and Sorted Guest List for {int(st.session_state.num_invites)} people")
    st.dataframe(clustered_sorted_df)
