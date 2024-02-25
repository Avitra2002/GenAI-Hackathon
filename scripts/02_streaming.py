from utils.llm import CompletionStream, print_stream

if user_input := input("Question: "):
    messages = [{"role": "user", "content": user_input}]

    stream = CompletionStream(messages)
    with stream as response:
        stream.completion = print_stream(response)
