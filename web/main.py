import streamlit as st

# Page configuration
st.set_page_config(
    page_title = "Math7 Prompt Bench",
    page_icon = "🔢",
    layout = "wide"
)

def check_auth():
    """Check if user is logged in"""
    return st.session_state.get("logged_in", False)


