import os
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

def get_video_metadata(video_id):
    """Fetches title and thumbnail from YouTube API"""
    request = youtube.videos().list(part="snippet", id=video_id)
    response = request.execute()
    if response['items']:
        data = response['items'][0]['snippet']
        return {
            "title": data['title'],
            "thumbnail": data['thumbnails']['high']['url'],
            "description": data['description']
        }
    return None

def extract_tools_with_ai(text_content):
    """Uses Groq Llama 3.1 to find tool names in the text"""
    if not text_content:
        return ["No tools found"]

    prompt = f"""
    Analyze the following text from a YouTube video. 
    List ONLY the names of AI software, tools, or platforms mentioned (e.g., Midjourney, ChatGPT, ElevenLabs).
    Format the output as a simple comma-separated list.
    Text: {text_content[:8000]}
    """
    
    completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",  # Updated to the current supported model
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content.split(",")

def process_video(video_url):
    try:
        # Extract ID from URL
        video_id = video_url.split("v=")[-1].split("&")[0]
        
        # 1. Get Metadata
        meta = get_video_metadata(video_id)
        if not meta:
            return "Error: Could not find video metadata."
        
        # 2. Get Transcript (Fallback to Description if transcript fails)
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            text_for_ai = " ".join([t['text'] for t in transcript_list])
        except:
            # If no transcript, use the video description instead
            text_for_ai = meta['description']

        # 3. Extract Tools via Groq AI
        tools_found = extract_tools_with_ai(text_for_ai)
        
        # 4. Save to Supabase
        supabase.table("videos").upsert({
            "video_id": video_id,
            "title": meta['title'],
            "thumbnail_url": meta['thumbnail'],
            "category": "AI Tutorial",
            "ai_summary": ", ".join(tools_found)
        }).execute()
        
        return f"✅ Success! Added: {meta['title']}. Tools identified: {', '.join(tools_found)}"
    
    except Exception as e:
        return f"❌ Error processing video: {str(e)}"
