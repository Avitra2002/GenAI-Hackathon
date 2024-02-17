# GenAI Hackathon Starter Kit

## Objective
Starter kit for prototyping GenAI apps quickly.

## Prerequisites
1. Python 3.9 is recommended
1. Some basic knowledge of [Streamlit](https://streamlit.io/) or learn from simple [tutorials](https://docs.streamlit.io/get-started/tutorials)
1. Minimal knowledge about OpenAI API and Prompt Engineering.


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
1. Setup environment variables. Replace the environment variables in `.env` with the values provided
    ```
    cp -i .env.example .env
    ```

## Running the app
1. On subsequent run, activate virtual environment 
1. Run script
    ```
    python -m scripts.01_minimal
    ```
1. Run app
    ```
    streamlit run home.py 
    ```
    