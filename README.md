# GenAI Hackathon Starter Kit

## Intro
This repository serves as a starter kit to prototype apps quickly and easily for the GenAI Hackathon.

## Prerequisites
* Python 3.8 is acceptable for most of the use cases
* Python 3.9 and above is required for langchain pandas agent


## Setup
1. Clone this repository
    ```
    git clone git@bitbucket.org:temasek/starter-kit.git
    ```
1. Create a virtual environment 
    ```
    python -m venv venv
    ```
1. Activate virtual environment 
    * On Mac machine
    ```
    source venv/bin/activate 
    ```   
    * On Windows machine
    ```
    venv\Scripts\activate
    ```
1. Install packages 
    ```
    pip install -r requirements.txt
    ```

1. Create a file called `.env` in the root folder, and add the following content, with actual values you will be given:
    ```
    AZURE_OPENAI_ENDPOINT=https://xxxxxxx.openai.azure.com/
    AZURE_OPENAI_API_KEY=xxxxxxx
    OPENAI_API_VERSION=xxxx
    ```

## Running the app
1. On subsequent run, activate virtual environment 
1. Run script
    ```
    python scripts/01_minimal.py
    ```
1. Run app
    ```
    streamlit run home.py 
    ```

