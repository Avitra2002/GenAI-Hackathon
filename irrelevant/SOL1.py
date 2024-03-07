import tempfile
from pathlib import Path
import pandas as pd
import re
import streamlit as st
import io
from utils.llm import CompletionStream, get_completion
from streamlit_option_menu import option_menu

#Horizontal navbar
selected = option_menu(
    menu_title = None,
    options = ["Home", "Projects", "Contact"],
    icons=["award-fill", "book", "envelope"],
    menu_icon= "cast",
    default_index=0,
    orientation = "horizontal"
)

st.markdown("# VIP Guest Manager :superhero::princess::santa:")
# add :woman_judge:	emoji
st.markdown("This tool is designed to help you manage your VIP guest list for an event. It uses AI to help you rank the most relevant guests based on your event's goal and topic.")


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
    sys_message = "You are a helpful assistant."
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

# Generate initial lists button
if st.button("GET STARTED 🚀"):
    st.session_state.started = True
    if "indus" not in st.session_state:
        st.session_state.indus = []

    if "role" not in st.session_state:
        st.session_state.role = []

    event_details = {'event_goal': event_goal, 'event_topic': event_topic, 'event_type': event_type}
    ranked_industries, ranked_designations = get_llm_response_and_rank(event_details, industry_keywords, designation_keywords, sys_message)
    st.session_state.indus = ranked_industries
    st.session_state.role = ranked_designations
    st.session_state.ranked_designations = ranked_designations  # Store ranked_designations in st.session_state
    st.session_state.num_invites = calculate_invites(event_size, show_up_rate)
    

    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = []
    messages = st.session_state.chatbot_messages  # alias as shorthand

    prompt1 = """Convert the following data delimited by triple ticks to a industry ranked list: ```{data}``` """
    
    industrylist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt1.format(data = st.session_state.indus)}]).choices[0].message.content

    messages.append({"role": "assistant", "content": industrylist})
    # Display a toast message
    message = "❗ Please reorder priorities by typing the values"
    toast_obj = st.toast(message)  # Assigning the toast object is optional


if "chatbot_messages" not in st.session_state:
    st.session_state.chatbot_messages = []
messages = st.session_state.chatbot_messages  # alias as shorthand


for message in messages:
    # print message if the first two letter are not "['"
    if str(message["content"])[:2] != "['":
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


if "started" in st.session_state and "industryConfirmed" not in st.session_state: 
    # if st.button("Confirm the Industry List"):
    if st.button("PROCEED TO ROLES 👨‍👩‍👧‍👦"):  
        pulledlist = messages[-1]["content"] #pulling the last message from chat session state
        formatprompt = "From the data delimited in triple ticks below, remove the top row of text that is not part of the list item, and convert the list format into a python list of strings, where each item represents one item in the list. Never shorten string in list with 3 dots. Remove the numbers from each item. ```{pulled}```" 

        industryformattedlist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": formatprompt.format(pulled = pulledlist)}]).choices[0].message.content #using gpt to process the string into a python list
        messages.append({"role": "assistant", "content": industryformattedlist})
            
        # industry confirmed, next role, create flage industryConfirmed = True
        st.session_state.industryConfirmed = True
        
        # st.write("Okay! Now we need to confirm the Role list. Please go through the same steps, and click the Final Role List Generate button when ready.")
        st.markdown("> Update the Role list in chat and click 'SHOW THE RESULT' when ready. 👍")
        # industryformattedlist 

        st.session_state.industry = industryformattedlist

        prompt2 = """Convert the following data delimited by triple ticks to a ranked list with title role ranked list: ```{data}``` """

        rolelist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt2.format(data = st.session_state.role)}]).choices[0].message.content

        messages.append({"role": "assistant", "content": rolelist})

        st.chat_message("assistant").write(rolelist)
    
user_preferred_designations = []
top_designations = st.session_state.ranked_designations[:5] 
invites_allocation = allocate_invites(st.session_state.num_invites, top_designations, user_preferred_designations)

final_list_df = pd.DataFrame()

# Button to generate the Role list
# if "industryConfirmed" in st.session_state and st.button("Confirm the Role List"):
if "industryConfirmed" in st.session_state and st.button("SHOW THE RESULT ✨"):
    if "user_preferences" in st.session_state:
        # Parse user preferences to get a list of preferred designations
        preferred_designations = parse_user_preferences(user_input)
                
        
    pulledlist = messages[-1]["content"] #pulling the last message from chat session state
    formatprompt = "From the data delimited in triple ticks below, remove the top row of text that is not part of the list item, and convert the list format into a python list of strings, where each item represents one item in the list. Never shorten string in list with 3 dots Remove the numbers from each item. ```{pulled}```" 

    roleformattedlist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": formatprompt.format(pulled = pulledlist)}]).choices[0].message.content #using gpt to process the string into a python list
    #BUGFIX messages.append({"role": "assistant", "content": roleformattedlist})
    #BUGFIX st.chat_message("assistant").write( roleformattedlist)


    roleformattedlist = ast.literal_eval(roleformattedlist)
    industryformattedlist = ast.literal_eval(st.session_state.industry)
    
    # print comma-separate value from roleformattedlist
    # st.write(', '.join(roleformattedlist))
    
    # Invoking the 'allocate_invites' function with the necessary parameters
    invites_allocation = allocate_invites(st.session_state.num_invites, roleformattedlist[:5], user_preferred_designations)

    # Iterate over the allocations to display the final role list with allocated invites
    for designation, num_invites in invites_allocation.items():
        filtered_df = df[df['Designation'].str.contains(designation, case=False)].head(num_invites)
        st.markdown(f"#### Top invites for {designation}:")
        st.dataframe(filtered_df)
        final_list_df = pd.concat([final_list_df, filtered_df], axis=0)
    # Reset the index of the final DataFrame since concatenation can result in duplicate indices
    final_list_df.reset_index(drop=True, inplace=True)

    # Display the final consolidated list
    st.markdown("### Final Consolidated Guest List:")
    st.dataframe(final_list_df)
    
    # buffer to use for excel writer
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    # Write each dataframe to a different worksheet.
        final_list_df.to_excel(writer, sheet_name='Sheet1', index=False)

    # Reset buffer position
    buffer.seek(0)
    downloadExcel = st.download_button(
        label="Download as Excel",
        data=buffer,
        file_name='vipmanager_result.xlsx',
        mime='application/vnd.ms-excel'
    )  