# based on https://docs.streamlit.io/knowledge-base/tutorials/build-conversational-apps
import streamlit as st

from utils.llm import CompletionStream, get_completion
import json
import pandas as pd
from io import BytesIO

def preprocess_data(df):
    # Convert the DataFrame to a list of dictionaries for easier processing with LLM
    data_list = df.to_dict('records')
    # Convert the list of dictionaries to a JSON string for the prompt
    json_data = json.dumps(data_list, indent=2)
    return json_data

st.title("Event Seating Arrangement Assistant")


# Collect event details from the user

num_tables = st.number_input("Enter the number of tables:", min_value=1, value=5)
seats_per_table = st.number_input("Enter the number of seats per table:", min_value=1, value=5)
event_type = st.selectbox("Select the type of event:", options=["Formal Round-Table", "Topic Discussion", "Networking", "Forum"])
event_goal_topic= st.text_input("Enter the goal/topic of this event")
t_org_ratio = st.number_input("Enter the number of Temasek attendees per table:", min_value=0, max_value=seats_per_table, value=2)

uploaded_file = st.file_uploader("Choose an Excel file with attendee information", type=['xlsx'])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    json_data = preprocess_data(df)

    # Generate LLM prompt based on event type and requirements
    prompt = f"""
Review the list of event attendees:

```{json_data}```
The columns are "Org category" (T: Temasek workers, Core TPCs, smaller TPCs, AUM, Platform/JV, TNE, Union), "Industry", "Designation" (BOD, GEC, Chmn, etc) and the "Remarks" to consider when deciding who to sit with each other.
Your task is to curate a seating arrangement for {num_tables} tables, each holding {seats_per_table} guests, at an event of type '{event_type}', centered around '{event_goal_topic}'. 

- Group attendees by industry relevance to '{event_goal_topic}', with priority industries at prominent tables.
- Prioritize seating by designation rank: Chairman > CEO > Board > MD > GEC > Dy Chmn > President > NED > Advisor > Secretary > Working Team.
- Ensure diversity of organizations at each table, with at least {t_org_ratio} 'T' org category members (a category in the Org Category column) because these are events held by Temasek Company.
- For formal round-tables, group similar designations; for networking events, mix adjacent ranks for better interaction.
- Consider 'Remarks' for any specific seating preferences or restrictions.
- Exclude overseas attendees from physical tables, but list them for online invitations based on relevance to the event topic(this is stated in the remark column).

Please organize the seating arrangement starting with Table 1 as the highest priority. Format the response as follows:


Table 1:
1. Name - Designation, Industry, Organisation name
2.
3. ...

Table 2:
1.
2.
3.

...
Please send online invitations to overseas attendees:
1. Name -  Designation, Industry, Organisation name
2.
3. ..."""
    

    # Use the LLM to generate the seating arrangement
    seating_arrangement = get_completion([ {"role": "user", "content": prompt}]).choices[0].message.content

    # Display the generated seating arrangement (you might need to process the LLM's output to display it nicely)
    st.text("Preview of the generated Seating Arrangement:")
    st.write(seating_arrangement)

    sections = seating_arrangement.strip().split('Table ')
    sections = [section for section in sections if section]  # Remove empty strings

    # Dictionary to store lists of people for each table and virtual attendees
    table_lists = {}

    for section in sections:
        lines = section.split('\n')
        if lines[0].startswith('Please'):
            # Handle the virtual attendees
            key = 'Virtual'
            people = lines[1:]  # Exclude the first line
        else:
            # Handle regular tables
            table_number, *people = lines  # Separate the table number from the list of people
            key = f'Table {table_number.split(":")[0]}'  # Get the table number
        
        # Store the list of people, removing the numbering and trimming whitespace
        table_lists[key] = [person.split('. ', 1)[-1].strip() for person in people if person]

    # Create a DataFrame from the table_lists dictionary
    df = pd.DataFrame(dict([(k, pd.Series(v)) for k,v in table_lists.items()]))

    # Display the DataFrame
    # st.dataframe(df)
    excel= BytesIO()
    with pd.ExcelWriter(excel, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
    excel.seek(0)

# Download link for the Excel file
    st.download_button(
        label="Download Excel file",
        data=excel.getvalue(),
        file_name="seating_arrangement.xlsx",
        mime="application/vnd.ms-excel")
