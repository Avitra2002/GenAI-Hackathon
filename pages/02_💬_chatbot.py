# based on https://docs.streamlit.io/knowledge-base/tutorials/build-conversational-apps
import streamlit as st
from scripts.testdata import outputjson
from utils.llm import CompletionStream

jsoninput = outputjson()

st.title("Chatbot")

context = "You are an AI chatbot for an event planning team. Your role is to help them determine who to seat at which tables, based on user input and data. You will use the data delimited by triple ticks as your database from which to decide table seatings. Do not add your own input into the data. Make sure to check the remarks for each decision. Individual remarked to have a spouse must seat at the same table as their spouse. Individuals remarked to be based overseas / virtual invite only cannot be sat at a table. If there are any issues, make that clear to the user. ```{tables}```"

# Consider this table, placed in the back of the room, comprised solely of the following individuals:

# Henry

# Evelyn

# Gabriel

# Joshua

# Xavier

# Tell me all the issues associated with this table comprehensively, making sure to consider every individual, and give me proposed solutions.

context = context.format(tables = jsoninput)

if "tableseating_messages" not in st.session_state:
    st.session_state.tableseating_messages = [0]
messages = st.session_state.tableseating_messages  # alias as shorthand
messages[0] = {"role": "system", "content": context}
# inputcontext = get_completion([{"role": "system", "content": context}, {"role": "user", "content": formatprompt.format(pulled = pulledlist)}]).choices[0].message.content



for message in messages:
    st.chat_message(message["role"]).write(message["content"])

if user_input := st.chat_input():
    system_prompt = context
    st.chat_message("user").write(user_input)
    messages.append({"role": "user", "content": user_input})

    stream = CompletionStream(messages)
    stream.temperature = 0.01
    stream.top_p = 0.98
    with stream as response:
        stream.completion = str(st.chat_message("assistant").write_stream(response))
    messages.append({"role": "assistant", "content": stream.completion}) 

    while len(messages) > 50:  # limit context window by removing the earliest
        messages.pop(0)

# if user_input := st.chat_input()("Question:"):
#             file_raw_text = load_faq()
#             system_prompt = QNA_PROMPT.format(
#                 context=file_raw_text, question=user_input
#             ) # exceldata = data
#             messages = [{"role": "system", "content": system_prompt}]

#             st.write("Answer:")
#             stream = CompletionStream(messages)
#             with stream as response:
#                 stream.completion = str(st.write_stream(response))