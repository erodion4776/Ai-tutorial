import streamlit as st
from supabase import create_client
import os

# Setup
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

st.set_page_config(page_title="AI Tutorial Hub", layout="wide", page_icon="🚀")

# Modern UI Styling
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 5px;
        color: white;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; }
    .category-tag {
        background: #21262d;
        color: #58a6ff;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 12px;
        border: 1px solid #30363d;
    }
    .tool-card { border: 1px solid #30363d; padding: 15px; border-radius: 10px; background: #161b22; margin-bottom: 10px; }
    .affiliate-btn { background-color: #238636; color: white !important; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: block; text-align: center; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: DISCOVERY ---
with st.sidebar:
    st.title("👨‍💻 Admin")
    topic = st.text_input("Find New Tutorials:", placeholder="e.g. Logo Design")
    if st.button("Discovery & Import"):
        from processor import search_and_bulk_add
        search_and_bulk_add(topic)
        st.rerun()
    
    st.divider()
    st.subheader("🔗 Link Manager")
    m_tool = st.text_input("Tool Name:")
    m_link = st.text_input("Link:")
    if st.button("Save Link"):
        supabase.table("affiliate_tools").upsert({"tool_name": m_tool, "affiliate_link": m_link}).execute()
        st.success("Saved!")

# --- MAIN PAGE ---
st.title("🚀 Global AI Tutorial Hub")
st.write("Browse the world's best AI tutorials, categorized and ready for use.")

# 1. Fetch Category List and Links
links_data = supabase.table("affiliate_tools").select("tool_name, affiliate_link").execute()
affiliate_map = {item['tool_name'].lower().strip(): item['affiliate_link'] for item in links_data.data}

# 2. Category Navigation
available_categories = ["All", "Image Generation", "Video & Animation", "Automation & Workflow", "AI Writing & Chat", "Coding & Tech", "Voice & Audio"]
selected_cat = st.tabs(available_categories)

# 3. Handle Filtering and Display
for i, cat_name in enumerate(available_categories):
    with selected_cat[i]:
        # Build Query
        query = supabase.table("videos").select("*")
        if cat_name != "All":
            query = query.eq("category", cat_name)
        
        videos = query.order("date_added", desc=True).execute()

        if videos.data:
            for video in videos.data:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
                    st.markdown(f"<span class='category-tag'>{video['category']}</span>", unsafe_allow_html=True)
                    st.subheader(video['title'])
                
                with col2:
                    st.write("### 🛠️ Featured Tools")
                    raw_tools = video.get('ai_summary', '')
                    if raw_tools:
                        for tool in list(set([t.strip() for t in raw_tools.split(",")])):
                            link = affiliate_map.get(tool.lower())
                            if link:
                                st.markdown(f'<div class="tool-card"><strong>{tool}</strong><a href="{link}" class="affiliate-btn" target="_blank">Try {tool}</a></div>', unsafe_allow_html=True)
                            else:
                                st.info(f"Tool: {tool}")
                    
                    st.divider()
                    st.write("📚 **Premium Prompt Pack**")
                    st.link_button("Buy Library (₦20,000)", "https://selar.co/yourlink")
                st.divider()
        else:
            st.info(f"No videos in {cat_name} yet. Use the sidebar to import some!")
