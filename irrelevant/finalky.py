import tempfile
from pathlib import Path
import pandas as pd
import re
import streamlit as st
from utils.llm import CompletionStream, get_completion

# @st.cache
# def load_data(csv_file_path):
#     return pd.read_csv(csv_file_path)

# # Function to filter guests based on event criteria
# def filter_guests(df, event_size):
#     return df.sample(n=event_size)

st.title("Guest Lists Generator")

# Load the guest list from a CSV file
guest_list = "Dataset.csv"
df = pd.read_csv(guest_list)
industry_keywords = df['Industry'].unique().tolist()
designation_keywords = df['Designation'].unique().tolist()

#initializing session state
if "ranked_designations" not in st.session_state:
    st.session_state["ranked_designations"] = []
if "num_invites" not in st.session_state:
    st.session_state.num_invites = 0
    
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

# Function to parse user preferences and extract designations
def parse_user_preferences(user_preferences):
    # Simple example - split by 'and' & ',', and strip whitespace
    preferences = [pref.strip() for pref in re.split('and|,', user_preferences)]
    return preferences

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

def allocate_invites(num_invites, top_designations, user_preferred_designations):
    if not top_designations:
        return{}
    
    st.session_state.num_invites = calculate_invites(event_size, show_up_rate)
    #ranked_designations = get_llm_response_and_rank(event_details, industry_keywords, designation_keywords, sys_message)
    total_invites_allocated = 0
    #hold the number of invites per designation
    invites_allocation = {}
    
    # Base allocation for each of the top designations
    base_allocation_per_designation = num_invites // len(top_designations)
    
    # Additional invites for preferred designations
    extra_invites = base_allocation_per_designation // 2  # For simplicity, give 50% more invites to preferred designations
   
    for designation in top_designations:
        if designation in user_preferred_designations:
            # Allocate extra invites to preferred designations
            invites_allocation[designation] = base_allocation_per_designation + extra_invites
        else:
            # Allocate base invites to other designations
            invites_allocation[designation] = base_allocation_per_designation
    
    # Update total invites allocated
        total_invites_allocated += invites_allocation[designation]
    
    # If there are any remaining invites due to rounding, allocate them to the most preferred designation
    remaining_invites = num_invites - total_invites_allocated
    if remaining_invites > 0 and user_preferred_designations:
        most_preferred = user_preferred_designations[0]  # Assuming the first preferred designation is the most preferred
        invites_allocation[most_preferred] += remaining_invites
    
    return invites_allocation

#initialise stage variable to control which button pops up when
if 'stage' not in st.session_state:
    st.session_state.stage = 1

def set_state(i):
    st.session_state.stage = i

if "chatbot_messages" not in st.session_state:
    st.session_state.chatbot_messages = []
messages = st.session_state.chatbot_messages  # alias as shorthand

event_details = {'event_goal': event_goal, 'event_topic': event_topic, 'event_type': event_type}

def showindustry(event_details, industry_keywords, designation_keywords, sys_message, show_up_rate, i):
        ranked_industries, ranked_designations = get_llm_response_and_rank(event_details, industry_keywords, designation_keywords, sys_message)
        st.session_state.indus = ranked_industries
        st.session_state.role = ranked_designations
        st.session_state.num_invites = calculate_invites(event_size, show_up_rate)
        
        

        

        prompt1 = """Convert the following data delimited by triple ticks to a industry ranked list: ```{data}``` """
        # prompt2 = """Convert the following data delimited by triple ticks to a ranked list with title role ranked list: ```{data}``` """

        

        industrylist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt1.format(data = st.session_state.indus)}]).choices[0].message.content

        # rolelist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt2.format(data = st.session_state.role)}]).choices[0].message.content


        messages.append({"role": "assistant", "content": industrylist})
        # messages.append({"role": "assistant", "content": rolelist})
        st.session_state.stage = i

# Generate initial lists button
if st.session_state.stage == 0:
    
    if "indus" not in st.session_state:
        st.session_state.indus = []
        

    if "role" not in st.session_state:
        st.session_state.role = []

    
    

    st.button("Generate Initial Lists", on_click = showindustry, args = (event_details, industry_keywords, designation_keywords, sys_message, show_up_rate, 1))


    






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

def showrole(messages, sys_message, i):
    pulledlist = messages[-1]["content"] #pulling the last message from chat session state
    formatprompt = "From the data delimited in triple ticks below, remove the top row of text that is not part of the list item, and convert the list format into a python list of strings, where each item represents one item in the list. Remove the numbers from each item. ```{pulled}```" 

    industryformattedlist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": formatprompt.format(pulled = pulledlist)}]).choices[0].message.content #using gpt to process the string into a python list
    # st.write(industryformattedlist)
    # messages.append({"role": "assistant", "content": industryformattedlist})
    # st.chat_message("assistant").write(industryformattedlist)
    st.write("Okay! Now we need to confirm the Role list. Please go through the same steps, and click the Final Role List Generate button when ready.")

 

    st.session_state.industry = industryformattedlist

    prompt2 = """Convert the following data delimited by triple ticks to a ranked list with title role ranked list: ```{data}``` """

    rolelist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt2.format(data = st.session_state.role)}]).choices[0].message.content

    messages.append({"role": "assistant", "content": rolelist})

    st.chat_message("assistant").write(rolelist)

    st.session_state.stage = i

# Button to generate the industry list
if st.session_state.stage == 1:
    # Chatbot interaction section
    st.subheader("Chatbot Interaction")
    st.write("Review the ranked role list above. If you'd like to make changes, you can request them here.")

    

    st.button("Final Industry List Generate", on_click = showrole, args = (messages, sys_message, 2))



#user_preferences_input = st.text_input("Enter your preferences for the event (e.g., 'We mainly want CEOs and Chairmen to attend'):")
user_preferred_designations = []
top_designations = st.session_state.ranked_designations[:5] 
invites_allocation = allocate_invites(st.session_state.num_invites, top_designations, user_preferred_designations)


def showfinallist(messages, sys_message, user_preferred_designations, i):
    if "user_preferences" in st.session_state:
        # Parse user preferences to get a list of preferred designations
        preferred_designations = parse_user_preferences(user_input)

    pulledlist = messages[-1]["content"] #pulling the last message from chat session state
    formatprompt = "From the data delimited in triple ticks below, remove the top row of text that is not part of the list item, and convert the list format into a python list of strings, where each item represents one item in the list. Remove the numbers from each item. ```{pulled}```" 

    roleformattedlist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": formatprompt.format(pulled = pulledlist)}]).choices[0].message.content #using gpt to process the string into a python list
    # st.write(roleformattedlist)
    messages.append({"role": "assistant", "content": roleformattedlist})
    st.chat_message("assistant").write(roleformattedlist)

    roleformattedlist = ast.literal_eval(roleformattedlist)
    # st.write(st.session_state.industry)
    industryformattedlist = ast.literal_eval(st.session_state.industry)

    # st.write(roleformattedlist)
    
    # Invoking the 'allocate_invites' function with the necessary parameters
    invites_allocation = allocate_invites(st.session_state.num_invites, roleformattedlist[:5], user_preferred_designations)

    # Iterate over the allocations to display the final role list with allocated invites
    

    st.session_state.stage = i

# Button to generate the Role list
if st.session_state.stage == 2:
    st.button("Show Final Table", on_click = showfinallist, args = (messages, sys_message, user_preferred_designations, 3))
    
if st.session_state.stage == 3:
    for designation, num_invites in invites_allocation.items():
        filtered_df = df[df['Designation'].str.contains(designation, case=False)].head(num_invites)
        st.write(f"Top invites for {designation}:")
        st.dataframe(filtered_df)

  
