import tempfile

import streamlit as st
import whisper
from pydub import AudioSegment

from utils.llm import CompletionStream
from utils.tokens import num_tokens_from_string

transcript = ""
SUMMARY_TEMPLATE = """Write a summary based on the following

{context}

SUMMARY:"""


@st.cache_resource
def load_model():
    return whisper.load_model("base")


@st.cache_data
def video_to_audio(video_file, format="mp3") -> str:
    tmp_audio_fname = f"./data/tmp_audio.{format}"
    audio = AudioSegment.from_file(video_file, format="mp4")
    audio.export(out_f=tmp_audio_fname, format=format)
    return tmp_audio_fname


@st.cache_data
def audio_to_text(audio_file) -> str:
    model = load_model()
    result = model.transcribe(audio_file, fp16=False)
    return str(result["text"])


st.title("Video & Audio Summary")
with st.sidebar:
    sys_message = st.text_area("System message", value="You are a helpful assistant.")
    uploaded_file = st.sidebar.file_uploader(
        "Upload a video file and convert it to a transcript.",
        type=["mp3", "m4a", "wav", "mp4"],
    )

tab_audio_video, tab_summary = st.tabs(["Audio & Video", "Summary"])

with tab_audio_video:
    if uploaded_file:
        with st.expander("", expanded=True):
            is_video = uploaded_file.name.endswith(".mp4")
            if is_video:
                st.video(uploaded_file)
            else:
                st.audio(uploaded_file)

        with tempfile.NamedTemporaryFile() as f:
            f.write(uploaded_file.read())
            f.flush()

            if is_video:
                audio_fname = video_to_audio(f.name)
                transcript = audio_to_text(audio_fname)
            else:
                transcript = audio_to_text(f.name)

            st.subheader("Generated Transcript")
            transcript = st.text_area("Context", value=transcript, height=240)

            n_token = num_tokens_from_string(transcript)
            st.write(f"Contains `{n_token:,}` tokens")
    else:
        st.info("Please upload an audio or video file first!")


with tab_summary:
    if uploaded_file and transcript:
        summary_prompt = st.text_area(
            "Summary prompt", value=SUMMARY_TEMPLATE, height=150
        )
        if st.button("Summarize"):
            updated_input = summary_prompt.format(context=transcript)
            messages = [
                {"role": "system", "content": sys_message},
                {"role": "user", "content": updated_input},
            ]
            stream = CompletionStream(messages)
            with stream as response:
                stream.completion = str(st.write_stream(response))
    else:
        st.write("Please upload an audio or video file first!")
