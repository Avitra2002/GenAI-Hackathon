import pandas as pd
import json
# Load the Excel data
def outputjson():
    df = pd.read_excel('smalldata.xlsx')

    # Convert the Excel data to JSON
    json_data = df.to_json(orient='records')

    # Load the JSON data into a Python list of dictionaries
    messages = json.loads(json_data)
    try:
        data = json.loads(json_data)
        print("The Excel file has been successfully converted to JSON.")
    except json.JSONDecodeError:
        print("The Excel file has not been successfully converted to JSON.")
        
    # Print the first item in the data
    # print(data[5])

    # Print the value of a specific column in the first item
    # print(data[0]['Industry'])
    return data




