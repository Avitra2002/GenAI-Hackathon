from utils.llm import CompletionStream, print_stream

while True:
    if user_input := input("What is the primary objective of your event? (networking / roundtable)"):
        messages = [{"role": "user", "content": user_input}]
    elif useruser_input := input("Who is this event for? (specific industry / company?)"):
        messages = [{"role": "user", "content": user_input}]
    
    stream = CompletionStream(messages)
    with stream as response:
        stream.completion = print_stream(response)
