import streamlit as st
from supabase import create_client
import os
from processor import process_video, search_and_bulk_add

# 1. INITIALIZE CONNECTION
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(URL, KEY)

st.set_page_config(page_title="AI HUB | Admin Console", layout="wide", page_icon="⚙️")

# Custom CSS for a clean Admin UI
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #10b981; color: white; border: none; }
    .stTextInput>div>div>input { border-radius: 8px; }
    .report-card { padding: 15px; border-radius: 10px; background-color: #1e293b; border: 1px solid #334155; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🚀 AI Hub Admin")
menu = st.sidebar.radio("Navigate to:", ["Discovery & Import", "Link Manager", "Roadmap Architect", "Tutorial Library"])

# --- FEATURE 1: DISCOVERY & BULK IMPORT ---
if menu == "Discovery & Import":
    st.header("🔎 Video Discovery & AI Processing")
    st.write("Search YouTube for top tutorials. The AI will categorize, extract tools, and write SEO blogs automatically.")

    col1, col2 = st.columns([2, 1])
    with col1:
        keyword = st.text_input("Enter Topic Keywords", placeholder="e.g. AI Faceless YouTube Channel")
    with col2:
        count = st.slider("Videos to process", 1, 10, 3)

    if st.button("Start Bulk Discovery"):
        if keyword:
            with st.spinner(f"AI is hunting for '{keyword}' tutorials..."):
                reports = search_and_bulk_add(keyword, max_results=count)
                for r in reports:
                    st.info(r)
                st.success("Batch Processing Complete!")
        else:
            st.warning("Please enter a keyword first.")

    st.divider()
    st.subheader("🔗 Manual Video Addition")
    single_url = st.text_input("Paste specific YouTube URL:")
    if st.button("Process Single Video"):
        with st.spinner("Analyzing video..."):
            res = process_video(single_url)
            st.success(res)

# --- FEATURE 2: LINK MANAGER ---
elif menu == "Link Manager":
    st.header("🔗 Affiliate Link Manager")
    st.write("Manage the links that appear on your beautiful Netlify frontend.")

    with st.expander("➕ Add/Update Affiliate Link", expanded=True):
        t_name = st.text_input("Tool Name (e.g. ElevenLabs)")
        t_link = st.text_input("Your Affiliate URL")
        t_active = st.checkbox("Active (visible on the site)", value=True)
        if st.button("Save to Database"):
            if t_name and t_link:
                # is_active is set explicitly here so a new/updated tool is never
                # silently hidden by the frontend's `.eq('is_active', true)` filter.
                supabase.table("affiliate_tools").upsert({
                    "tool_name": t_name.strip(),
                    "affiliate_link": t_link.strip(),
                    "is_active": t_active
                }).execute()
                st.success(f"Link for {t_name} is now {'live' if t_active else 'saved but hidden'}!")
            else:
                st.error("Fields cannot be empty.")

    st.subheader("Current Active Links")
    links = supabase.table("affiliate_tools").select("*").execute()
    if links.data:
        for l in links.data:
            c1, c2, c3, c4 = st.columns([2, 4, 1, 1])
            c1.write(f"**{l['tool_name']}**")
            c2.write(l['affiliate_link'])
            c3.write("🟢" if l.get("is_active") else "⚪")
            if c4.button("🗑️", key=l['tool_name']):
                supabase.table("affiliate_tools").delete().eq("tool_name", l['tool_name']).execute()
                st.rerun()

# --- FEATURE 3: ROADMAP ARCHITECT ---
elif menu == "Roadmap Architect":
    st.header("🗺️ Learning Roadmap Architect")
    st.write("Group tutorials into step-by-step 'Skill Paths' for your users.")

    tab1, tab2 = st.tabs(["Create New Roadmap", "Add Videos to Roadmap"])

    with tab1:
        r_title = st.text_input("Path Title (e.g., Become an AI Content Creator)")
        r_desc = st.text_area("Path Description")
        r_image = st.text_input("Cover Image URL (optional)")
        if st.button("Publish Roadmap"):
            if r_title:
                slug = r_title.lower().strip().replace(" ", "-")
                payload = {
                    "title": r_title,
                    "description": r_desc,
                    "slug": slug
                }
                if r_image:
                    payload["image_url"] = r_image
                supabase.table("roadmaps").insert(payload).execute()
                st.success(f"Roadmap '{r_title}' created!")
            else:
                st.error("Path Title is required.")

    with tab2:
        # Fetch current roadmaps
        rm_data = supabase.table("roadmaps").select("id, title").execute()
        if rm_data.data:
            rm_options = {r['title']: r['id'] for r in rm_data.data}
            sel_rm = st.selectbox("Select Roadmap", options=list(rm_options.keys()))

            # Fetch videos to add
            vid_data = supabase.table("videos").select("video_id, title").execute()
            vid_options = {v['title']: v['video_id'] for v in vid_data.data}
            if vid_options:
                sel_vid = st.selectbox("Select Video to add as a step", options=list(vid_options.keys()))

                order = st.number_input("Step Order (1, 2, 3...)", min_value=1)
                task = st.text_input("Task for this step (e.g., Watch this and create your first AI image)")

                if st.button("Add Step to Path"):
                    supabase.table("roadmap_steps").insert({
                        "roadmap_id": rm_options[sel_rm],
                        "video_id": vid_options[sel_vid],
                        "step_order": order,
                        "task_description": task
                    }).execute()
                    st.success(f"Added '{sel_vid}' as Step {order} to {sel_rm}")
            else:
                st.warning("No videos in the library yet — add some in Discovery & Import first.")
        else:
            st.warning("Create a roadmap first.")

# --- FEATURE 4: TUTORIAL LIBRARY ---
elif menu == "Tutorial Library":
    st.header("📚 Existing Tutorials")
    vids = supabase.table("videos").select("video_id, title, category, ai_summary").order("date_added", desc=True).execute()

    if not vids.data:
        st.info("No tutorials yet. Add some in Discovery & Import.")
    else:
        for v in vids.data:
            with st.container():
                st.markdown(f"""
                    <div class="report-card">
                        <h4>{v['title']}</h4>
                        <p><b>Category:</b> {v['category']} | <b>Tools:</b> {v['ai_summary']}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Delete Video", key=v['video_id']):
                    supabase.table("videos").delete().eq("video_id", v['video_id']).execute()
                    st.rerun()
