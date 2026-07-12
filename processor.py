import os
import re
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from supabase import create_client

# 1. INITIALIZE API CLIENTS
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
YT_API_KEY = os.getenv("YT_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
youtube = build('youtube', 'v3', developerKey=YT_API_KEY)

# Groq model IDs — kept in one place so future migrations only need a one-line change.
# llama-3.1-70b-versatile was decommissioned Jan 2025 (hard error if used).
# llama-3.1-8b-instant / llama-3.3-70b-versatile were announced deprecated June 17, 2026.
FAST_MODEL = "openai/gpt-oss-20b"      # category + tool extraction
WRITER_MODEL = "openai/gpt-oss-120b"   # long-form SEO blog generation


def extract_video_id(url):
    """Handles Short, Mobile, Desktop, and Embed URLs"""
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None


def get_transcript_with_timeout(video_id, timeout_seconds=10):
    """
    YouTube frequently blocks transcript requests coming from datacenter/cloud IPs
    (Streamlit Cloud, Render, etc). When blocked, the underlying library can hang or
    retry for a long time with no built-in timeout, which is what causes bulk search
    to appear stuck for minutes instead of seconds.

    This wraps the call in a hard timeout so a blocked/slow request gives up fast and
    falls back to the video description, instead of stalling the whole batch.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(YouTubeTranscriptApi.get_transcript, video_id)
        try:
            transcript_list = future.result(timeout=timeout_seconds)
            return " ".join([t['text'] for t in transcript_list])
        except FutureTimeoutError:
            print(f"Transcript fetch timed out after {timeout_seconds}s for {video_id} "
                  f"(likely YouTube blocking this server's IP) — falling back to description.")
            return None
        except Exception as e:
            print(f"Transcript fetch error for {video_id}: {e}")
            return None


def get_video_metadata(video_id):
    """Fetches details from YouTube Data API"""
    try:
        request = youtube.videos().list(part="snippet", id=video_id)
        response = request.execute()
        if response['items']:
            data = response['items'][0]['snippet']
            return {
                "title": data['title'],
                "thumbnail": data['thumbnails']['high']['url'],
                "description": data['description']
            }
    except Exception as e:
        print(f"Metadata Error: {e}")
    return None


def extract_data_and_category(text_content):
    """Task 1: Identify Category and Extract Tool Names using the fast model"""
    categories = "Image Generation, Video & Animation, Automation & Workflow, AI Writing & Chat, Coding & Tech, Voice & Audio"

    prompt = f"""
    Analyze this text:
    1. Categorize it into ONE of these: [{categories}].
    2. List all AI tools/software mentioned (e.g. Midjourney, ElevenLabs), separated by commas only.
       Do NOT wrap the list in brackets. Do NOT number them.

    Respond in exactly this format, with nothing else:
    Category: <name>
    Tools: <Tool1, Tool2, Tool3>

    Text: {text_content[:5000]}
    """
    try:
        completion = groq_client.chat.completions.create(
            model=FAST_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        res = completion.choices[0].message.content
        cat = res.split("Category:")[1].split("Tools:")[0].strip()

        tools_raw = res.split("Tools:")[1].strip()
        # Defensive cleanup: strip stray brackets/quotes the model might still add,
        # since ai_summary is matched verbatim against affiliate_tools.tool_name later.
        tools_raw = tools_raw.strip("[]").strip()
        tools = ", ".join(t.strip().strip('"\'') for t in tools_raw.split(",") if t.strip())

        return cat or "General AI", tools or "AI Tools"
    except Exception as e:
        print(f"Category/Tools extraction error: {e}")
        return "General AI", "AI Tools"


def generate_seo_blog(transcript, title):
    """Task 2: Write a high-quality Markdown blog post using the writer model"""
    if not transcript or len(transcript) < 100:
        return "Comprehensive guide coming soon..."

    prompt = f"""
    You are an expert AI Blogger. Convert this YouTube transcript into a professional, SEO-optimized blog post.
    Title: {title}

    Requirements:
    - Use Markdown formatting (## for headers).
    - Section 1: Introduction (The Problem & Solution).
    - Section 2: Key Takeaways (Bulleted list).
    - Section 3: Step-by-Step Tutorial (Detailed guide).
    - Section 4: Final Verdict/Conclusion.
    - Style: Engaging, authoritative, and clear.

    Transcript: {transcript[:10000]}
    """
    try:
        completion = groq_client.chat.completions.create(
            model=WRITER_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Blog generation error: {e}")
        return "Detailed written tutorial currently being processed."


def process_video(video_url):
    """The Main Engine: Ingest, Analyze, Write, and Save"""
    try:
        video_id = extract_video_id(video_url)
        if not video_id:
            return "❌ Invalid URL"

        meta = get_video_metadata(video_id)
        if not meta:
            return "❌ No Metadata found"

        # Get Transcript — hard-timeout guarded, see get_transcript_with_timeout()
        text_for_ai = get_transcript_with_timeout(video_id, timeout_seconds=10)
        if not text_for_ai:
            text_for_ai = meta['description']

        # Run AI Steps
        cat, tools = extract_data_and_category(text_for_ai)
        blog_post = generate_seo_blog(text_for_ai, meta['title'])

        # Save to Supabase — date_added set explicitly so ordering never depends
        # on a DB-side default silently not being configured.
        supabase.table("videos").upsert({
            "video_id": video_id,
            "title": meta['title'],
            "thumbnail_url": meta['thumbnail'],
            "category": cat,
            "ai_summary": tools,
            "article_body": blog_post,
            "date_added": datetime.now(timezone.utc).isoformat()
        }).execute()

        return f"✅ Successfully Hubbed: {meta['title']} in {cat}"

    except Exception as e:
        return f"❌ System Error: {str(e)}"


def search_and_bulk_add(keyword, max_results=3):
    """
    Discovery Feature: Auto-builds your site based on keywords.

    This is a generator — it yields a status string after each video finishes
    processing, instead of silently working for minutes and returning one final
    list. app.py should iterate over this and print each yielded status as it
    arrives, so bulk search never looks frozen.
    """
    try:
        search_query = f"{keyword} AI tutorial"
        request = youtube.search().list(q=search_query, part="id", type="video", maxResults=max_results)
        response = request.execute()
        ids = [item['id']['videoId'] for item in response.get('items', [])]
    except Exception as e:
        yield f"❌ Search Error: {str(e)}"
        return

    if not ids:
        yield f"⚠️ No videos found for topic: {keyword}"
        return

    yield f"🔎 Found {len(ids)} videos for '{keyword}' — processing one by one..."

    for i, vid_id in enumerate(ids, start=1):
        yield f"⏳ ({i}/{len(ids)}) Processing https://www.youtube.com/watch?v={vid_id} ..."
        result = process_video(f"https://www.youtube.com/watch?v={vid_id}")
        yield f"({i}/{len(ids)}) {result}"

    yield f"✅ Finished processing {len(ids)} videos for topic: {keyword}"
