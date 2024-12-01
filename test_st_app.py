import streamlit as st
from streamlit_float import float_init, float_css_helper

# Initialize float feature/capability
float_init()

# CSS to make the content container scrollable
st.markdown(
    """
    <style>
    .scrollable-container {
        height: 400px;
        overflow-y: scroll;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Main function for the Streamlit app
def main():
    st.title('Scrollable Content with Fixed Footer')

    # Create a scrollable container for the content
    content_container = st.container()
    with content_container:
        st.markdown('<div class="scrollable-container">', unsafe_allow_html=True)
        
        # Add some dummy data to test scrolling
        for i in range(1, 101):
            st.write(f"This is item number {i}")

        st.markdown('</div>', unsafe_allow_html=True)

    # Create a fixed footer container with buttons
    footer_container = st.container()
    with footer_container:
        col1, col2 = st.columns(2)
        with col1:
            if st.button('Get Next 10 emails'):
                st.write("Fetching next 10 emails...")
        with col2:
            if st.button('Submit'):
                st.write("Submitting changes...")
    
    # Apply floating behavior to the footer container
    css = float_css_helper(bottom="0", background="white")
    footer_container.float(css)

if __name__ == "__main__":
    main()
