import streamlit as st
from supabase import create_client
import os

# 1. Setup Connection to Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# 2. UI Styling (Dark Theme & Professional Look)
st.set_page_config(page_title="AI Tutorial Hub", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .tool-card {
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 10px;
        background: #161b22;
        margin-bottom: 10px;
    }
    .affiliate-btn {
        background-color: #238636;
        color: white !important;
        padding: 8px 20px;
        text-decoration: none;
        border-radius: 5px;
        font-weight: bold;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar - Admin Panel (To add new videos)
with st.sidebar:
    st.title("⚙️ Admin Panel")
    new_video_url = st.text_input("Paste YouTube URL to Add:")
    if st.button("Process & Add Video"):
        with st.spinner("AI is analyzing the video..."):
            # This calls the processor logic we built in Sprint 3
            from processor import process_video 
            result = process_video(new_video_url)
            st.success(result)

# 4. Main View - Tutorial Gallery
st.title("🚀 Global AI Tutorial Hub")
st.write("Master AI tools with curated tutorials and direct access to software.")

# Fetch videos from Supabase
videos = supabase.table("videos").select("*").order("date_added", desc=True).execute()

if not videos.data:
    st.info("No videos added yet. Use the Admin Panel to add your first AI tutorial!")
else:
    # Create a grid layout
    for video in videos.data:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
            st.subheader(video['title'])
        
        with col2:
            st.write("### 🛠️ Tools Used")
            # Fetch tools linked to this video
            # (Note: In a full version, we'd join tables, but let's start simple)
            st.markdown(f"""
                <div class="tool-card">
                    <h4>Featured Tool</h4>
                    <p>Get started with the AI tool used in this video.</p>
                    <a href="#" class="affiliate-btn">Get Started Free</a>
                </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            st.write("### 📚 Digital Products")
            st.info("Grab our 'Master Prompt Library' for $25 / ₦20,000")
            st.link_button("Buy on Selar", "https://selar.co/yourlink")
        st.divider()
