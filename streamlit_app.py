import streamlit as st
import pandas as pd
import sqlite3
from streamlit_float import float_init, float_css_helper

# Set page config at the very beginning
st.set_page_config(layout="wide")

# Initialize float feature
float_init()

# Function to get a database connection
def get_db_connection():
    return sqlite3.connect('taskeroo.db')

# Function to update the database schema
def update_db_schema(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(emails)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'is_manual' not in columns:
        cursor.execute("ALTER TABLE emails ADD COLUMN is_manual INTEGER DEFAULT 0")
    if 'manually_updated_category' not in columns:
        cursor.execute("ALTER TABLE emails ADD COLUMN manually_updated_category TEXT")
    if 'reviewed' not in columns:
        cursor.execute("ALTER TABLE emails ADD COLUMN reviewed INTEGER DEFAULT 0")
    conn.commit()


def fetch_unreviewed_emails(conn, limit=10):
    return pd.read_sql_query(f"""
        SELECT id, subject, sender_email, snippet, label_ids, category, 
               manually_updated_category, is_manual, 
               COALESCE(manually_updated_category, category) as current_category 
        FROM emails 
        WHERE reviewed = 0
        LIMIT {limit}
    """, conn)
    
# Function to fetch unique labels from the database
def fetch_unique_labels(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT manually_updated_category FROM emails WHERE manually_updated_category IS NOT NULL AND manually_updated_category != ''")
    manually_updated_categories = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT category FROM emails WHERE category IS NOT NULL AND category != ''")
    categories = [row[0] for row in cursor.fetchall()]
    return list(set(manually_updated_categories + categories))

# Function to update email category in the database
def update_email_category(conn, email_id, new_category):
    cursor = conn.cursor()
    cursor.execute("UPDATE emails SET manually_updated_category = ?, is_manual = 1, reviewed = 1 WHERE id = ?", (new_category, email_id))
    conn.commit()

# Function to display a single email
def display_email(email, labels):
    with st.expander(f"**{email['subject']}**", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**From:** {email['sender_email']}")
            st.write(f"**Snippet:** {email['snippet']}")
            st.write(f"**Labels:** {email['label_ids']}")
            
            # Display manual edit status
            if email['is_manual']:
                st.markdown("🖊️ **Manually Edited**")
            
            # Display original and updated categories
            original_category = email['category']
            updated_category = email['manually_updated_category'] if email['is_manual'] else original_category
            
            st.markdown(f"**Original Category:** {original_category}")
            if email['is_manual']:
                st.markdown(f"**Updated Category:** {updated_category}")
                
        with col2:
            new_category = st.selectbox(
                "Category",
                labels,
                index=labels.index(updated_category) if updated_category in labels else 0,
                key=f"category_{email['id']}"
            )
            
    return new_category != updated_category, new_category


# Main function for the Email Categorization page
def email_categorization_page():
    st.title('Teach Email Categories')
    st.write("This page allows you to teach the model \
             new categories and over time improve the model's performance.")
    
    conn = get_db_connection()
    update_db_schema(conn)
    labels = fetch_unique_labels(conn)
    
    if 'emails' not in st.session_state:
        st.session_state.emails = fetch_unreviewed_emails(conn)
    
    if st.button('Get Next 10 Emails'):
        st.session_state.emails = fetch_unreviewed_emails(conn)
        st.rerun()
    
    emails = st.session_state.emails
    
    if emails.empty:
        st.write("No emails found in the database.")
    else:
        updated = False
        for index, email in emails.iterrows():
            category_changed, new_category = display_email(email, labels)
            if category_changed:
                update_email_category(conn, email['id'], new_category)
                updated = True
                #update the email in the session state
                st.session_state.emails.loc[index, 'manually_updated_category'] = new_category
                st.session_state.emails.loc[index, 'is_manual'] = 1
        
        if updated:
            st.success("Categories updated!")
            st.rerun()
    
    conn.close()

# Settings page
def review_page():
    st.title("Review Learned Categories")
    st.write("This page provides insights into the email categorization process.")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Total number of emails
    cursor.execute("SELECT COUNT(*) FROM emails")
    total_emails = cursor.fetchone()[0]
    st.metric("Total Emails", total_emails)

    # Number of unreviewed emails
    cursor.execute("SELECT COUNT(*) FROM emails WHERE reviewed = 0")
    unreviewed_emails = cursor.fetchone()[0]
    st.metric("Unreviewed Emails", unreviewed_emails)

    # Number of manually categorized emails
    cursor.execute("SELECT COUNT(*) FROM emails WHERE is_manual = 1")
    manual_categorized = cursor.fetchone()[0]
    st.metric("Manually Categorized Emails", manual_categorized)

    # Number of reviewed emails
    cursor.execute("SELECT COUNT(*) FROM emails WHERE reviewed = 1")
    reviewed_emails = cursor.fetchone()[0]
    st.metric("Reviewed Emails", reviewed_emails)

    # Percentage of manually categorized emails
    if total_emails > 0:
        manual_percentage = (manual_categorized / total_emails) * 100
        st.metric("Percentage Manually Categorized", f"{manual_percentage:.2f}%")

    # Top 5 categories
    cursor.execute("""
        SELECT COALESCE(manually_updated_category, category) as final_category, COUNT(*) as count
        FROM emails
        GROUP BY final_category
        ORDER BY count DESC
        LIMIT 5
    """)
    top_categories = cursor.fetchall()
    st.subheader("Top 5 Categories")
    for category, count in top_categories:
        st.write(f"- {category}: {count}")

    # Number of unique categories
    cursor.execute("""
        SELECT COUNT(DISTINCT COALESCE(manually_updated_category, category))
        FROM emails
    """)
    unique_categories = cursor.fetchone()[0]
    st.metric("Unique Categories", unique_categories)

    # Recent manual categorizations
    st.subheader("Recent Manual Categorizations")
    recent_manual = pd.read_sql_query("""
        SELECT subject, sender_email, manually_updated_category
        FROM emails
        WHERE is_manual = 1
        ORDER BY id DESC
        LIMIT 5
    """, conn)
    st.dataframe(recent_manual)

    conn.close()

# About page
def stats_page():
    st.title("Stats")
    st.write("This page allows you to see the stats of the model & its performance.")

# Main app
def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Teach", "Review", "Stats"])
    
    if page == "Teach":
        email_categorization_page()
    elif page == "Review":
        review_page()
    elif page == "Stats":
        stats_page()

if __name__ == "__main__":
    main()