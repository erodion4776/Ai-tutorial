import os
import re
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from supabase import create_client

# Initialize Clients
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
YT_API_KEY = os.getenv("YT_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
youtube = build('youtube', 'v3', developerKey=YT_API_KEY)

def extract_video_id(url):
    """
    Extracts the video ID from various YouTube URL formats.
    Handles youtu.be, youtube.com/watch?v=, and youtube.com/embed/
    """
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_video_metadata(video_id):
    """Fetches title and thumbnail from YouTube API"""
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
        print(f"YouTube API Error: {e}")
    return None

def extract_tools_with_ai(text_content):
    """Uses Groq Llama 3.1 to find tool names in the text"""
    if not text_content or len(text_content) < 20:
        return ["AI Tools"]

    prompt = f"""
    Analyze the following text from a YouTube video. 
    List ONLY the names of AI software, tools, or platforms mentioned (e.g., Midjourney, ChatGPT, ElevenLabs).
    Format the output as a simple comma-separated list.
    Text: {text_content[:8000]}
    """
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content.split(",")
    except:
        return ["AI Tools"]

def process_video(video_url):
    try:
        # 1. Robust ID Extraction
        video_id = extract_video_id(video_url)
        if not video_id:
            return "❌ Error: Invalid YouTube URL format."
        
        # 2. Get Metadata
        meta = get_video_metadata(video_id)
        if not meta:
            return f"❌ Error: Could not find metadata for ID: {video_id}. Check if your YouTube API Key is correct."
        
        # 3. Get Transcript
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            text_for_ai = " ".join([t['text'] for t in transcript_list])
        except:
            text_for_ai = meta['description']

        # 4. AI Extraction
        tools_found = extract_tools_with_ai(text_for_ai)
        
        # 5. Save to Supabase
        supabase.table("videos").upsert({
            "video_id": video_id,
            "title": meta['title'],
            "thumbnail_url": meta['thumbnail'],
            "category": "AI Tutorial",
            "ai_summary": ", ".join(tools_found)
        }).execute()
        
        return f"✅ Success! Added: {meta['title']}"
    
    except Exception as e:
        return f"❌ System Error: {str(e)}"
