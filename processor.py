import os
import re
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from supabase import create_client

# 1. Initialize API Clients from Environment Variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
YT_API_KEY = os.getenv("YT_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
youtube = build('youtube', 'v3', developerKey=YT_API_KEY)

def extract_video_id(url):
    """Handles all YouTube URL formats (Short, Mobile, Desktop, Embed)"""
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

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

def extract_tools_with_ai(text_content):
    """Uses Groq Llama 3.1 8B to identify AI software mentioned"""
    if not text_content or len(text_content) < 20:
        return ["AI Tools"]

    prompt = f"""
    Analyze the following YouTube transcript/description. 
    Identify and list ONLY the names of AI tools, software, or platforms mentioned.
    Format the output as a simple comma-separated list (e.g., ChatGPT, ElevenLabs, Midjourney).
    If no specific tools are found, return 'AI Software'.
    
    Text: {text_content[:8000]}
    """
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content.split(",")
    except Exception as e:
        print(f"AI Error: {e}")
        return ["AI Tools"]

def process_video(video_url):
    """The main logic for a single video"""
    try:
        video_id = extract_video_id(video_url)
        if not video_id:
            return "❌ Invalid URL."
        
        meta = get_video_metadata(video_id)
        if not meta:
            return "❌ Metadata not found."
        
        # Get Transcript (Fallback to description)
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            text_for_ai = " ".join([t['text'] for t in transcript_list])
        except:
            text_for_ai = meta['description']

        # AI Tool Extraction
        tools_found = extract_tools_with_ai(text_for_ai)
        tools_string = ", ".join([t.strip() for t in tools_found])
        
        # Save to Supabase
        supabase.table("videos").upsert({
            "video_id": video_id,
            "title": meta['title'],
            "thumbnail_url": meta['thumbnail'],
            "category": "AI Tutorial",
            "ai_summary": tools_string
        }).execute()
        
        return f"✅ Added: {meta['title']}"
    
    except Exception as e:
        return f"❌ Error: {str(e)}"

def search_and_bulk_add(keyword, max_results=3):
    """New Feature: Searches YouTube and processes the top videos automatically"""
    try:
        search_query = f"{keyword} AI tutorial"
        request = youtube.search().list(
            q=search_query,
            part="id",
            type="video",
            maxResults=max_results,
            order="relevance"
        )
        response = request.execute()
        
        video_ids = [item['id']['videoId'] for item in response.get('items', [])]
        
        results = []
        for vid_id in video_ids:
            # Re-use the process_video logic for each search result
            url = f"https://www.youtube.com/watch?v={vid_id}"
            report = process_video(url)
            results.append(report)
            
        return results
    except Exception as e:
        return [f"❌ Search Error: {str(e)}"]
