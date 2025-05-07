import streamlit as st

st.set_page_config(
    page_title="Library System Reports",
    page_icon="📚",
)

st.write("# Welcome to SLS Report Page")

st.sidebar.success("Select a report above.")

st.markdown(
    """
    Welcome to the SLS reports starting page
    **👈 Select a report from the sidebar** to start analyzing the library books and authors
    ### Available reports
    - Popular Books Dashboard
    - Popular Authors Dashboard
    - Single Book Review
    - Single Author Review
"""
)