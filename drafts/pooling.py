# Number of invitees to extract
n = 5  # Change this value to the number of invitees you want

# Desired designation to filter by (example: 'ceo')
desired_designation = 'ceo'  # Change this to the desired designation

# Ensure that the 'Designation' column exists and is in the correct format
if 'Designation' in st.session_state.filtered_guest_list.columns:
    st.session_state.filtered_guest_list['Designation'] = st.session_state.filtered_guest_list['Designation'].str.lower()

# Filter the DataFrame for rows that match the desired designation
designation_filtered_df = st.session_state.filtered_guest_list[st.session_state.filtered_guest_list['Designation'] == desired_designation.lower()]

# Sort the filtered DataFrame based on some criteria if needed (e.g., score)
# Assuming 'Score' column exists and lower scores are better
designation_filtered_df = designation_filtered_df.sort_values(by='Score')

# Extract the top n invitees based on the sorted DataFrame
top_n_invitees_df = designation_filtered_df.head(n)

# Display the top n invitees
if not top_n_invitees_df.empty:
    st.write(f"Top {n} invitees for the designation '{desired_designation}':")
    st.dataframe(top_n_invitees_df)
else:
    st.write(f"No invitees found for the designation '{desired_designation}'.")