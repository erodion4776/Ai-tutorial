import os
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from supabase import create_client

# Initialize Clients (These variables will be set in Render)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
YT_API_KEY = os.getenv("YT_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
youtube = build('youtube', 'v3', developerKey=YT_API_KEY)

def get_video_metadata(video_id):
    request = youtube.videos().list(part="snippet", id=video_id)
    response = request.execute()
    if response['items']:
        data = response['items'][0]['snippet']
        return {
            "title": data['title'],
            "thumbnail": data['thumbnails']['high']['url']
        }
    return None

def extract_tools_with_ai(transcript):
    """Uses Groq Llama 3 to find tool names in the text"""
    prompt = f"Analyze this YouTube transcript and list ONLY the names of AI software or tools mentioned. Format: tool1, tool2, tool3. Transcript: {transcript[:8000]}"
    
    completion = groq_client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content.split(",")

def process_video(video_url):
    video_id = video_url.split("v=")[-1].split("&")[0]
    
    # 1. Get Metadata
    meta = get_video_metadata(video_id)
    
    # 2. Get Transcript
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([t['text'] for t in transcript_list])
    except:
        transcript_text = ""

    # 3. Extract Tools via Groq
    tools_found = extract_tools_with_ai(transcript_text)
    
    # 4. Save to Supabase
    supabase.table("videos").upsert({
        "video_id": video_id,
        "title": meta['title'],
        "thumbnail_url": meta['thumbnail'],
        "category": "AI Tutorial"
    }).execute()
    
    return f"Processed: {meta['title']}. Tools found: {tools_found}"
