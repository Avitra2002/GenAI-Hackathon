import tempfile
from pathlib import Path
import pandas as pd
import re
import streamlit as st
import io
from utils.llm import CompletionStream, get_completion
from st_aggrid import AgGrid
import ast
import seaborn as sns
import matplotlib.pyplot as plt


st.markdown("# VIP Guest Manager :superhero::princess::santa:")
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
    print("##### Getting LLM response and ranking")
    industry_question = f"Rank the following industries based on their relevance to a {event_details['event_type']} about {event_details['event_topic']} with the goal of {event_details['event_goal']}: {', '.join(industry_keywords)}."
    designation_question = f"Rank the following designations based on their importance for the same event: {', '.join(designation_keywords)}."
    print("##### LLM - industry_response")
    industry_response = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": industry_question}]).choices[0].message.content
    ranked_industries = parse_llm_ranking_response(industry_response, industry_keywords)
    print("##### LLM - designation_response")
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
    print("##### LLM - industrylist")
    industrylist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt1.format(data = st.session_state.indus)}]).choices[0].message.content

    messages.append({"role": "assistant", "content": industrylist})
    # Display a toast message
    message = "❗ Please reorder priorities by typing the values"
    st.toast(message) 

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

if "started" in st.session_state and "industryConfirmed" not in st.session_state: 
    # if st.button("Confirm the Industry List"):
    if st.button("PROCEED TO ROLES 👨‍👩‍👧‍👦"):  
        st.session_state.industryConfirmed = True
        pulledlist = messages[-1]["content"] #pulling the last message from chat session state
        formatprompt = "From the data delimited in triple ticks below, remove the top row of text that is not part of the list item, and convert the list format into a python list of strings, where each item represents one item in the list. Never ever shorten the list with three dots. Remove the numbers from each item. ```{pulled}```" 

        print("##### LLM - industryformattedlist")
        industryformattedlist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": formatprompt.format(pulled = pulledlist)}]).choices[0].message.content #using gpt to process the string into a python list
        messages.append({"role": "assistant", "content": industryformattedlist})
            
        # industry confirmed, next role, create flage industryConfirmed = True
        st.markdown("> Update the Role list in chat and click 'SHOW THE RESULT' when ready. 👍")
        st.session_state.industry = industryformattedlist

        prompt2 = """Convert the following data delimited by triple ticks to a ranked list with title role ranked list: ```{data}``` """
        print("##### LLM - rolelist")
        rolelist = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": prompt2.format(data = st.session_state.role)}]).choices[0].message.content
        messages.append({"role": "assistant", "content": rolelist})
        st.chat_message("assistant").write(rolelist)
    
user_preferred_designations = []
top_designations = st.session_state.ranked_designations[:5] 
def finalize_invitees(ranked_designation, ranked_industries, invitees_df, max_invites):
    print("##### Finalizing invitees")
    # calculate matching score for each invitee
    invitees_df['matching_score'] = invitees_df.apply(lambda row: calculate_matching_score(row, ranked_designation, ranked_industries), axis=1)
    
    #round invitees_df['matching_score'] to 4 decimal
    invitees_df['matching_score'] = invitees_df['matching_score'].round(4)
    
    # sort by matching score
    invitees_df.sort_values(by='matching_score', ascending=False, inplace=True)
    
    # select top invitees based on max_invites
    invitees_df = invitees_df.head(max_invites)
    return invitees_df

def calculate_matching_score(row, ranked_designation, ranked_industries):
    # calculate matching score based on the position of the designation and industry in the ranked lists
    designation_score = (len(ranked_designation) - ranked_designation.index(row['Designation'])) / (2 * len(ranked_designation)) if row['Designation'] in ranked_designation else 0
    industry_score = (len(ranked_industries) - ranked_industries.index(row['Industry'])) / (2 * len(ranked_industries)) if row['Industry'] in ranked_industries else 0
    matching_score = designation_score + industry_score 
    return matching_score


# Button to generate the Role list
# if "industryConfirmed" in st.session_state and st.button("Confirm the Role List"):
if "industryConfirmed" in st.session_state and st.button("SHOW THE RESULT ✨"):
    if "user_preferences" in st.session_state:
        # Parse user preferences to get a list of preferred designations
        preferred_designations = parse_user_preferences(user_input)
                
    pulledlist = messages[-1]["content"] #pulling the last message from chat session state
    formatprompt = "From the data delimited in triple ticks below, remove the top row of text that is not part of the list item, and convert the list format into a python list of strings, where each item represents one item in the list. Never ever try to shorten the response with three little dot. Remove the numbers from each item. ```{pulled}```" 

    print("##### LLM - roleformattedString")
    roleformattedString = get_completion([{"role": "system", "content": sys_message}, {"role": "user", "content": formatprompt.format(pulled = pulledlist)}]).choices[0].message.content #using gpt to process the string into a python list
    try:
        roleformattedlist = ast.literal_eval(roleformattedString)
    except:
        print("Error in parsing the roleformattedString", roleformattedString )
        # check if roleformattedString contains ...
        if "..." in roleformattedString:
            print("roleformattedString contains ...")   
        roleformattedlist = []
    
    print("##### LLM - industryformattedlist, RESULT PROCESSING")
    try:
        industryformattedlist = ast.literal_eval(st.session_state.industry)
    except:
        print("Error in parsing the industryformattedlist", st.session_state.industry )
        # check if industryformattedlist contains ...
        if "..." in st.session_state.industry:
            print("industryformattedlist contains ...")
            # replace ... with ',
            st.session_state.industry = st.session_state.industry.replace("...", "',")
            industryformattedlist = ast.literal_eval(st.session_state.industry)
        else:
            industryformattedlist = []

    iList = finalize_invitees(roleformattedlist, industryformattedlist, df, st.session_state.num_invites)
    
    
    # Display the final consolidated list
    st.markdown("### 🌟🌟🌟 VIP Guest List 🌟🌟🌟")
    st.markdown("> 💡 TIP: You can group any column by dragging it to the top of the table.\
        And right click from any place on the table and click Export to Excel / CSV to download the file. ")
    

    # buffer to use for excel writer
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    # Write each dataframe to a different worksheet.
        iList.to_excel(writer, sheet_name='Sheet1', index=False)

    # Reset buffer position
    buffer.seek(0)
    downloadExcel = st.download_button(
        label="Download as Excel",
        data=buffer,
        file_name='vipmanager_result.xlsx',
        mime='application/vnd.ms-excel'
    )    
    
    #AG-Grid   
    grid_options = {
        "columnDefs": [
            {
                "headerName": "Industry",
                "field": "Industry",
            },
            {
                "headerName": "Organisation",
                "field": "Organisation",
            },
            {
                "headerName": "Name",
                "field": "Name",
            },
            {
                "headerName": "Designation",
                "field": "Designation",
                "rowGroup": True,

            },
            {
                "headerName": "Score",
                "field": "matching_score",
            },

            {
                "headerName": "Remarks",
                "field": "Remarks",
            },
            {
                "headerName": "Industry",
                "field": "Industry",
                "rowGroup": True,
            },
        ],
        "defaultColDef": {
			"sortable": False,
			"filter": False,
            "enableRowGroup": True,
		},
        "sideBar": False,
        "groupDefaultExpanded": 1,
        "rowGroupPanelShow": 'always'
        
    }
    
    try:
         AgGrid(iList, grid_options)
    except Exception as e:
         st.write(e)
         
         
    plt.figure(figsize=(10, 10))
    sns.countplot(y='Industry', hue='Designation', data=iList, order = df['Industry'].value_counts().index)    
    plt.title('Industry vs Designation')
    st.pyplot(plt)
    
    # Second plot
    plt.figure(figsize=(10, 10))
    sns.countplot(y='Designation', hue='Industry', data=iList, order=iList['Designation'].value_counts().index)
    plt.title('Designation vs Industry')
    st.pyplot(plt)