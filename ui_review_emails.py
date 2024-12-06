import streamlit as st
import pandas as pd
import sqlite3
import html
import json
from config import MAX_FETCH_EMAILS, DB_PATH

def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def fetch_reviewed_emails(offset=0):
    conn = get_db_connection()
    try:
        query = f"""
        SELECT *
        FROM emails 
        WHERE reviewed = 1
        ORDER BY id DESC
        LIMIT {MAX_FETCH_EMAILS}
        OFFSET {offset}
        """
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()
        
def display_reviewed_email(email):
    st.markdown(f"""
    <div class="email-card">
        <h3>Email ID: {email['id']}</h3>
        <div class="email-header">
            <div class="email-subject">{html.escape(str(email["subject"]))}</div>
        </div>
        <table>
            <tr><th>Field</th><th>Value</th></tr>
            <tr><td>Sender Email</td><td>{html.escape(str(email["sender_email"]))}</td></tr>
            <tr><td>Date</td><td>{email["date"]}</td></tr>
            <tr><td>Received Time</td><td>{email["received_time"]}</td></tr>
            <tr><td>Snippet</td><td>{html.escape(str(email["snippet"]))}</td></tr>
            <tr><td>Label IDs</td><td>{html.escape(str(email["label_ids"]))}</td></tr>
            <tr><td>Category</td><td>{html.escape(str(email["category"]))}</td></tr>
            <tr><td>ML Category</td><td>{html.escape(str(email["ml_category"]))}</td></tr>
            <tr><td>Confidence Score</td><td>{email["confidence_score"]}</td></tr>
            <tr><td>Secondary Categories</td><td>{html.escape(str(email["secondary_categories"]))}</td></tr>
            <tr><td>All Categories</td><td>{html.escape(str(email["all_categories"]))}</td></tr>
            <tr><td>Manually Updated Category</td><td>{html.escape(str(email["manually_updated_category"]))}</td></tr>
            <tr><td>Is Manual</td><td>{email["is_manual"]}</td></tr>
            <tr><td>Is Read</td><td>{email["is_read"]}</td></tr>
            <tr><td>Is Important</td><td>{email["is_important"]}</td></tr>
            <tr><td>User Tags</td><td>{html.escape(str(email["user_tags"]))}</td></tr>
            <tr><td>User Feedback</td><td>{html.escape(str(email["user_feedback"]))}</td></tr>
            <tr><td>Reviewed</td><td>{email["reviewed"]}</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # Display email body in an expandable section
    with st.expander("View Email Body"):
        st.text(email["email_body"])

    # Display attachment info in an expandable section
    if email["attachment_info"]:
        with st.expander("View Attachment Info"):
            try:
                attachment_info = json.loads(email["attachment_info"])
                st.json(attachment_info)
            except json.JSONDecodeError:
                st.warning("Attachment info is not in valid JSON format.")
                st.text(email["attachment_info"])

def review_emails_page():
    st.title('📬 Review Emails In DB')
    
    if 'offset' not in st.session_state:
        st.session_state.offset = 0
    
    reviewed_emails = fetch_reviewed_emails(offset=st.session_state.offset)
    
    if reviewed_emails.empty:
        st.info("No reviewed emails found.")
    else:
        for _, email in reviewed_emails.iterrows():
            display_reviewed_email(email)
    
    if st.button("Load More", type="primary"):
        st.session_state.offset += MAX_FETCH_EMAILS
        new_emails = fetch_reviewed_emails(offset=st.session_state.offset)
        if new_emails.empty:
            st.info("No more emails to load.")
        else:
            for _, email in new_emails.iterrows():
                display_reviewed_email(email)