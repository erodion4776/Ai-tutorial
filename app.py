import streamlit as st
from supabase import create_client
import os

# Setup
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

st.set_page_config(page_title="AI Tutorial Hub", layout="wide")

# CSS for a modern Look
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .tool-card { border: 1px solid #30363d; padding: 15px; border-radius: 10px; background: #161b22; margin-bottom: 10px; text-align: center; }
    .affiliate-btn { background-color: #238636; color: white !important; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: block; margin-top: 10px; }
    .search-bar { margin-bottom: 30px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: DISCOVERY & LINKS ---
with st.sidebar:
    st.title("⚙️ Creator Studio")
    
    # NEW: YOUTUBE DISCOVERY
    st.subheader("🔎 Discover Tutorials")
    topic = st.text_input("Topic (e.g. 'Midjourney'):")
    num_to_add = st.slider("Number of videos to import", 1, 10, 3)
    
    if st.button("Search & Import"):
        with st.spinner(f"Finding and analyzing {num_to_add} videos..."):
            from processor import search_and_bulk_add
            reports = search_and_bulk_add(topic, max_results=num_to_add)
            for r in reports:
                st.write(r)
            st.rerun()

    st.divider()
    
    st.subheader("🔗 Link Manager")
    m_tool = st.text_input("Tool Name:")
    m_link = st.text_input("Affiliate Link:")
    if st.button("Save Link"):
        supabase.table("affiliate_tools").upsert({"tool_name": m_tool, "affiliate_link": m_link}).execute()
        st.success("Link Saved!")

# --- MAIN PAGE: CLIENT SEARCH & GALLERY ---
st.title("🚀 Global AI Tutorial Hub")

# CLIENT SEARCH BAR
client_search = st.text_input("🔍 Search for a tool or tutorial (e.g. 'Claude' or 'Faceless video')", placeholder="What do you want to learn today?", key="main_search")

# DATA FETCHING
links_data = supabase.table("affiliate_tools").select("tool_name, affiliate_link").execute()
affiliate_map = {item['tool_name'].lower().strip(): item['affiliate_link'] for item in links_data.data}

# Logic to filter videos based on client search
if client_search:
    # Searches titles OR the AI-detected tools in Supabase
    videos = supabase.table("videos").select("*").or_(f"title.ilike.%{client_search}%,ai_summary.ilike.%{client_search}%").execute()
else:
    videos = supabase.table("videos").select("*").order("date_added", desc=True).execute()

# DISPLAY GALLERY
if videos.data:
    st.write(f"Showing {len(videos.data)} tutorials")
    for video in videos.data:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
            st.subheader(video['title'])
        with col2:
            st.write("### 🛠️ Tools Used")
            raw_tools = video.get('ai_summary', '')
            if raw_tools:
                for tool in list(set([t.strip() for t in raw_tools.split(",")])):
                    link = affiliate_map.get(tool.lower())
                    if link:
                        st.markdown(f'<div class="tool-card"><strong>{tool}</strong><a href="{link}" class="affiliate-btn" target="_blank">Get {tool}</a></div>', unsafe_allow_html=True)
                    else:
                        st.info(f"Detected: {tool}")
            
            st.divider()
            st.write("📚 **Premium Guide**")
            st.link_button("Buy Prompt Pack", "https://selar.co/yourlink")
        st.divider()
else:
    st.warning("No tutorials found for that search. Try another keyword!")
