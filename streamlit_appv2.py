import streamlit as st
from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stateful_button import button
from streamlit_extras.chart_container import chart_container
from streamlit_option_menu import option_menu
import pandas as pd
import sqlite3
from streamlit_float import float_init, float_css_helper
import html
import plotly.graph_objects as go
import plotly.express as px
from urllib.parse import urlparse
import datetime
from collections import Counter
import re
from ui_review_emails import review_emails_page  # Add this import at the top

# Set page config at the very beginning
st.set_page_config(layout="wide", page_title="Taskeroo - Email Categorization", page_icon="📧")

# Initialize float feature
float_init()

# Custom CSS for a modern look
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f6;
    }
    .stButton>button {
        border-radius: 20px;
    }
    .stProgress .st-bo {
        background-color: #4CAF50;
    }
    .email-card {
        background-color: white;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;  /* Add this line for the border */
    }
    .email-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .email-subject {
        font-size: 18px;
        font-weight: bold;
        color: #1a73e8;
    }
    .email-labels {
        display: flex;
        gap: 8px;
    }
    .email-label {
        background-color: #f1f3f4;
        color: #5f6368;
        padding: 4px 8px;
        border-radius: 16px;
        font-size: 12px;
    }
    .email-sender {
        color: #5f6368;
        font-size: 14px;
        margin-bottom: 12px;
    }
    .email-snippet {
        color: #202124;
        font-size: 14px;
        line-height: 1.4;
        margin-bottom: 16px;
    }
    .email-category {
        margin-bottom: 16px;
        display: flex;
        gap: 10px;
    }
    .category-tag {
        display: inline-flex;
        align-items: center;
        padding: 4px 8px;
        border-radius: 16px;
        font-size: 14px;
    }
    .category-tag.original {
        background-color: #fce8e6;
        color: #d93025;
    }
    .category-tag.current {
        background-color: #e8f0fe;
        color: #1967d2;
    }
    .email-actions {
        background-color: #f8f9fa;
        padding: 16px;
        border-radius: 8px;
        margin-top: 16px;
    }
    .action-label {
        font-weight: 500;
        margin-bottom: 8px;
        color: #202124;
    }
    .stSelectbox > div > div {
        background-color: white;
    }
    .stButton > button {
        background-color: #1a73e8;
        color: white;
        font-weight: 500;
        padding: 8px 16px;
        border-radius: 4px;
    }
    .stSelectbox > div > label {
        display: none;
    }
    .stSelectbox {
        margin-top: -15px;
    }
    .email-actions {
        display: flex;
        align-items: center;
        gap: 2px;
    }
    .category-select {
        flex-grow: 1;
    }
    .review-checkbox {
        min-width: 15px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def fetch_unique_labels():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM emails")
        labels = [row[0] for row in cursor.fetchall()]
        return labels
    finally:
        conn.close()

def get_db_connection():
    return sqlite3.connect('taskeroo.db', check_same_thread=False)

def fetch_unreviewed_emails(limit=10):
    conn = get_db_connection()
    try:
        query = f"""
        SELECT id, subject, sender_email, snippet, 
        label_ids, category, manually_updated_category, is_manual
        FROM emails 
        WHERE reviewed = 0
        ORDER BY id
        LIMIT {limit}
        """
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()

def update_email_category(email_id, new_category):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE emails 
            SET manually_updated_category = ?, is_manual = 1
            WHERE id = ?
        """, (new_category, email_id))
        conn.commit()
    finally:
        conn.close()

def mark_email_as_reviewed(email_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE emails SET reviewed = 1 WHERE id = ?", (email_id,))
        conn.commit()
    finally:
        conn.close()

def mark_all_as_reviewed(email_ids):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany("UPDATE emails SET reviewed = 1 WHERE id = ?", [(id,) for id in email_ids])
        conn.commit()
    finally:
        conn.close()

def display_email(email, categories, index):
    email_id = email['id']
    widget_key = f"category_{email_id}"

    if f"category_{email_id}" not in st.session_state:
        st.session_state[f"category_{email_id}"] = {
            'original': email['category'],
            'current': email['manually_updated_category'] if pd.notna(email['manually_updated_category']) else email['category']
        }

    def update_category():
        new_category = st.session_state[f"select_{widget_key}"]
        update_email_category(email_id, new_category)
        st.session_state[f"category_{email_id}"]['current'] = new_category
        st.session_state.emails.loc[index, 'manually_updated_category'] = new_category

    email_card = st.empty()
    
    def render_email_card():
        original_category = st.session_state[f"category_{email_id}"]['original']
        current_category = st.session_state[f"category_{email_id}"]['current']

        category_display = f"""
        <div class="email-category">
            <span class="category-tag current"><i class="fas fa-folder"></i> Category Updated </span>
            <span class="category-tag original"><i class="fas fa-history"></i> Original: {html.escape(str(original_category))}</span>
            <span class="category-tag current"><i class="fas fa-folder"></i> Current: {html.escape(str(current_category))}</span>
        </div>
        """ if original_category != current_category else f"""
        <div class="email-category">
            <span class="category-tag current"><i class="fas fa-folder"></i> Current: {html.escape(str(current_category))}</span>
        </div>
        """

        email_card.markdown(f"""
        <div class="email-card">
            <div class="email-header">
                <div class="email-subject">{html.escape(email["subject"])}</div>
                <div class="email-labels">
                    {''.join([f'<span class="email-label">{html.escape(label.strip())}</span>' for label in email['label_ids'].split(',') if email['label_ids']])}
                </div>
            </div>
            <div class="email-sender">
                <i class="fas fa-user-circle"></i> {html.escape(email["sender_email"])}
            </div>
            <div class="email-snippet">{html.escape(email["snippet"][:100])}...</div>
            {category_display}
        </div>
        """, unsafe_allow_html=True)

    render_email_card()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.selectbox(
            "Select a new category",
            categories,
            index=categories.index(st.session_state[f"category_{email_id}"]['current']) if st.session_state[f"category_{email_id}"]['current'] in categories else 0,
            key=f"select_{widget_key}",
            on_change=update_category,
        )
    with col2:
        st.checkbox("Mark as Reviewed", key=f"review_{widget_key}", on_change=lambda: mark_as_reviewed(email_id, index))
    
    # Re-render the email card after any changes
    render_email_card()

def mark_as_reviewed(email_id, index):
    mark_email_as_reviewed(email_id)
    st.session_state.emails.drop(index, inplace=True)
    #st.rerun()

def email_categorization_page():
    st.title('📧 Teach Email Categories')
    
    labels = fetch_unique_labels()
    
    if 'emails' not in st.session_state or st.session_state.emails.empty:
        st.session_state.emails = fetch_unreviewed_emails()
    
    if st.session_state.emails.empty:
        st.info("🎉 Great job! You've categorized all available emails. Check back later for more.")
    else:
        for index, email in st.session_state.emails.iterrows():
            display_email(email, labels, index)

    if st.button("Mark All As Reviewed & Get Next Batch", type="primary"):
        mark_all_as_reviewed(st.session_state.emails['id'].tolist())
        st.session_state.emails = fetch_unreviewed_emails()
        st.rerun()

def email_stats_page():
    st.title("📊 Email Categorization Stats")

    # Fetch basic stats
    total_emails, unreviewed_emails, review_progress = get_email_stats()

    # Create columns for basic stats
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Emails", f"{total_emails:,}")
    col2.metric("Unreviewed Emails", f"{unreviewed_emails:,}")
    col3.metric("Review Progress", f"{review_progress:.1f}%")

    conn = get_db_connection()
    try:
        # Category distribution
        category_df = pd.read_sql_query("""
            SELECT 
                COALESCE(manually_updated_category, category) as final_category, 
                COUNT(*) as count
            FROM emails
            GROUP BY final_category
            ORDER BY count DESC
        """, conn)

        # Top senders
        top_senders = pd.read_sql_query("""
            SELECT sender_email, COUNT(*) as count
            FROM emails
            GROUP BY sender_email
            ORDER BY count DESC
            LIMIT 10
        """, conn)

        # Time-based analysis
        time_stats = pd.read_sql_query("""
            SELECT 
                date,
                COUNT(*) as email_count
            FROM emails
            GROUP BY date
            ORDER BY date
        """, conn)
        
        # Additional stats
        manual_updates = pd.read_sql_query("SELECT COUNT(*) as count FROM emails WHERE is_manual = 1", conn).iloc[0]['count']
        unique_stats = pd.read_sql_query("""
            SELECT 
                COUNT(DISTINCT sender_email) as unique_senders,
                COUNT(DISTINCT COALESCE(manually_updated_category, category)) as unique_categories
            FROM emails
        """, conn)
        emails_with_attachments = pd.read_sql_query("""
            SELECT COUNT(*) as count
            FROM emails
            WHERE attachment_info IS NOT NULL AND attachment_info != ''
        """, conn).iloc[0]['count']
        avg_email_length = pd.read_sql_query("""
            SELECT AVG(LENGTH(email_body)) as avg_length
            FROM emails
        """, conn).iloc[0]['avg_length']
        subject_words = pd.read_sql_query("SELECT subject FROM emails", conn)

    finally:
        conn.close()

    # Display category distribution
    st.subheader("Category Distribution")
    fig = px.pie(category_df, values='count', names='final_category', title='Email Categories')
    st.plotly_chart(fig)

    # Display top senders
    st.subheader("Top 10 Email Senders")
    fig = px.bar(top_senders, x='sender_email', y='count', title='Most Common Senders')
    st.plotly_chart(fig)

    # Display additional stats
    st.subheader("Additional Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Manual Updates", f"{manual_updates:,}")
    col2.metric("Unique Senders", f"{unique_stats['unique_senders'].iloc[0]:,}")
    col3.metric("Unique Categories", f"{unique_stats['unique_categories'].iloc[0]:,}")

    col1, col2 = st.columns(2)
    col1.metric("Emails with Attachments", f"{emails_with_attachments:,}")
    col2.metric("Avg Email Length", f"{avg_email_length:.0f} characters")

    # Most common words in subject
    words = [word.lower() for subject in subject_words['subject'] for word in re.findall(r'\w+', subject)]
    word_counts = Counter(words).most_common(10)
    common_words_df = pd.DataFrame(word_counts, columns=['word', 'count'])
    
    st.subheader("Most Common Words in Subject Lines")
    fig = px.bar(common_words_df, x='word', y='count', title='Top 10 Words in Subject Lines')
    st.plotly_chart(fig)

    # Derived stats
    st.subheader("Derived Statistics")
    if total_emails > 0:
        attachment_rate = (emails_with_attachments / total_emails) * 100
        st.metric("Attachment Rate", f"{attachment_rate:.1f}%")

        manual_update_rate = (manual_updates / total_emails) * 100
        st.metric("Manual Update Rate", f"{manual_update_rate:.1f}%")

    if unreviewed_emails > 0:
        estimated_time_to_complete = unreviewed_emails * 0.5  # Assuming 30 seconds per email
        st.metric("Estimated Time to Complete Review", f"{estimated_time_to_complete:.1f} minutes")

def get_email_stats():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM emails")
        total_emails = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM emails WHERE reviewed = 0")
        unreviewed_emails = cursor.fetchone()[0]
        reviewed_emails = total_emails - unreviewed_emails
        review_progress = (reviewed_emails / total_emails) * 100 if total_emails > 0 else 0
        return total_emails, unreviewed_emails, review_progress
    finally:
        conn.close()

def main():
    total_emails, unreviewed_emails, review_progress = get_email_stats()
    
    with st.sidebar:
        selected = option_menu(
            "Main Menu",
            ["Teach", "Stats", "Review Emails"],  # Add "Review" to the menu options
            icons=['pencil-square', 'graph-up', 'envelope-open'],  # Add an icon for Review
            menu_icon="cast",
            default_index=0,
            key="main_menu"
        )
        
        st.markdown("---")
        st.markdown("### 📊 Quick Stats")
        
        st.metric("Total Emails", f"{total_emails:,}")
        st.metric("Unreviewed Emails", f"{unreviewed_emails:,}")
        st.metric("Review Progress", f"{review_progress:.1f}%")
        
        st.markdown("---")
    
    if selected == "Teach":
        email_categorization_page()
    elif selected == "Stats":
        email_stats_page()
    elif selected == "Review Emails":  # Add this condition
        review_emails_page()

if __name__ == "__main__":
    main()