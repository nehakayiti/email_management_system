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
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db_connection():
    return sqlite3.connect('taskeroo.db', check_same_thread=False)

@st.cache_data
def fetch_unique_labels():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT category FROM emails WHERE category IS NOT NULL AND category != ''
        UNION
        SELECT DISTINCT manually_updated_category FROM emails 
        WHERE manually_updated_category IS NOT NULL AND manually_updated_category != ''
    """)
    labels = [row[0] for row in cursor.fetchall()]
    return sorted(labels)

def update_email_category(conn, email_id, new_category):
    print(f"Updating database for email ID: {email_id} with new category: {new_category}")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE emails 
        SET manually_updated_category = ?, is_manual = 1, reviewed = 1 
        WHERE id = ?
    """, (new_category, email_id))
    conn.commit()
    print("Database update committed")

@st.cache_data
def fetch_unreviewed_emails(_limit=10):
    conn = get_db_connection()
    query = """
        SELECT id, subject, sender_email, snippet, label_ids, category, 
               manually_updated_category, is_manual, 
               COALESCE(manually_updated_category, category) as current_category,
               datetime(date, 'unixepoch') as date_time
        FROM emails 
        WHERE reviewed = 0
        LIMIT ?
    """
    # Convert _limit to an integer and pass it as a tuple
    return pd.read_sql_query(query, conn, params=(int(_limit),))

def display_email(email, categories):
    email_id = email['id']
    widget_key = f"category_{email_id}"

    print(f"Displaying email ID: {email_id}")
    print(f"Initial category: {email['current_category']}")

    # Use session state to store the current and original categories
    if f"original_category_{email_id}" not in st.session_state:
        st.session_state[f"original_category_{email_id}"] = email['current_category']
    if f"current_category_{email_id}" not in st.session_state:
        st.session_state[f"current_category_{email_id}"] = email['current_category']

    def render_email_card():
        original_category = st.session_state[f"original_category_{email_id}"]
        current_category = st.session_state[f"current_category_{email_id}"]
        print(f"Rendering email card with original category: {original_category} and current category: {current_category}")
        
        category_display = f"""
        <div class="email-category">
            <span class="category-tag original"><i class="fas fa-history"></i> Original: {html.escape(original_category)}</span>
            <span class="category-tag current"><i class="fas fa-folder"></i> Current: {html.escape(current_category)}</span>
        </div>
        """ if original_category != current_category else f"""
        <div class="email-category">
            <span class="category-tag current"><i class="fas fa-folder"></i> Current: {html.escape(current_category)}</span>
        </div>
        """

        st.markdown(f"""
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

    st.markdown('<div class="email-actions">', unsafe_allow_html=True)
    st.markdown('<div class="action-label">Categorize this email:</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    with col1:
        new_category = st.selectbox(
            "Select a category",
            categories,
            index=categories.index(st.session_state[f"current_category_{email_id}"]) if st.session_state[f"current_category_{email_id}"] in categories else 0,
            key=f"select_{widget_key}"
        )
        print(f"Selected new category: {new_category}")
    with col2:
        if st.button("Update Category", key=f"apply_{widget_key}", type="primary"):
            print(f"Update button pressed for email ID: {email_id}")
            update_email_category(get_db_connection(), email_id, new_category)
            print(f"Database updated with new category: {new_category}")
            st.session_state[f"current_category_{email_id}"] = new_category
            st.success(f"Category updated to: {new_category}")
            st.rerun()

    return False

def email_categorization_page():
    st.title('📧 Teach Email Categories')
    
    conn = get_db_connection()
    labels = fetch_unique_labels()
    
    if 'emails' not in st.session_state:
        st.session_state.emails = fetch_unreviewed_emails()
    
    emails = st.session_state.emails
    
    if emails.empty:
        st.info("🎉 Great job! You've categorized all available emails. Check back later for more.")
    else:
        for index, email in emails.iterrows():
            print(f"Processing email at index {index}")
            display_email(email, labels)

    if st.button('🔄 Get Next Batch', key='next_batch'):
        print("Next Batch button pressed")
        st.session_state.emails = fetch_unreviewed_emails()
        st.rerun()

def review_page():
    st.title("📊 Review Learned Categories")
    
    conn = get_db_connection()
    
    col1, col2 = st.columns(2)
    
    with col1:
        total_emails = pd.read_sql_query("SELECT COUNT(*) as count FROM emails", conn).iloc[0]['count']
        st.metric("Total Emails", total_emails)

        unreviewed_emails = pd.read_sql_query("SELECT COUNT(*) as count FROM emails WHERE reviewed = 0", conn).iloc[0]['count']
        st.metric("Unreviewed Emails", unreviewed_emails)

    with col2:
        manual_categorized = pd.read_sql_query("SELECT COUNT(*) as count FROM emails WHERE is_manual = 1", conn).iloc[0]['count']
        st.metric("Manually Categorized", manual_categorized)

        if total_emails > 0:
            reviewed_percentage = ((total_emails - unreviewed_emails) / total_emails) * 100
            st.metric("Reviewed Percentage", f"{reviewed_percentage:.2f}%")

    st.subheader("Top 5 Categories")
    top_categories = pd.read_sql_query("""
        SELECT COALESCE(manually_updated_category, category) as final_category, COUNT(*) as count
        FROM emails
        GROUP BY final_category
        ORDER BY count DESC
        LIMIT 5
    """, conn)
    
    if not top_categories.empty:
        with chart_container():
            st.bar_chart(top_categories.set_index('final_category'))
    else:
        st.info("No categorized emails yet.")

    st.subheader("Recent Manual Categorizations")
    recent_manual = pd.read_sql_query("""
        SELECT subject, sender_email, manually_updated_category
        FROM emails
        WHERE is_manual = 1
        ORDER BY id DESC
        LIMIT 5
    """, conn)
    
    if not recent_manual.empty:
        st.dataframe(recent_manual, use_container_width=True)
    else:
        st.info("No manual categorizations yet.")

    conn.close()

def main():
    with st.sidebar:
        selected = option_menu(
            "Main Menu",
            ["Teach", "Review", "Stats"],
            icons=['pencil-square', 'check-circle', 'graph-up'],
            menu_icon="cast",
            default_index=0,
            key="main_menu"  # Add this line to provide a unique key
        )
    
    if selected == "Teach":
        email_categorization_page()
    elif selected == "Review":
        review_page()
    elif selected == "Stats":
        st.title("📈 Email Stats")
        st.info("Coming soon! This page will show detailed statistics about your email categorization.")

if __name__ == "__main__":
    main()