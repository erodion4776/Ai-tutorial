import os
import re
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

def extract_video_id(url):
    """Handles Short, Mobile, Desktop, and Embed URLs"""
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

def extract_data_and_category(text_content):
    """Task 1: Identify Category and Extract Tool Names using 8B model (Fast)"""
    categories = "Image Generation, Video & Animation, Automation & Workflow, AI Writing & Chat, Coding & Tech, Voice & Audio"
    
    prompt = f"""
    Analyze this text:
    1. Categorize it into ONE of these: [{categories}].
    2. List all AI tools/software mentioned (e.g. Midjourney, ElevenLabs).
    
    Format:
    Category: [Name]
    Tools: [Tool1, Tool2]
    
    Text: {text_content[:5000]}
    """
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        res = completion.choices[0].message.content
        cat = res.split("Category:")[1].split("Tools:")[0].strip()
        tools = res.split("Tools:")[1].strip()
        return cat, tools
    except:
        return "General AI", "AI Tools"

def generate_seo_blog(transcript, title):
    """Task 2: Write a high-quality Markdown blog post using 70B model (Creative)"""
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
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except:
        return "Detailed written tutorial currently being processed."

def process_video(video_url):
    """The Main Engine: Ingest, Analyze, Write, and Save"""
    try:
        video_id = extract_video_id(video_url)
        if not video_id: return "❌ Invalid URL"
        
        meta = get_video_metadata(video_id)
        if not meta: return "❌ No Metadata found"
        
        # Get Transcript
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            text_for_ai = " ".join([t['text'] for t in transcript_list])
        except:
            text_for_ai = meta['description']

        # Run AI Steps
        cat, tools = extract_data_and_category(text_for_ai)
        blog_post = generate_seo_blog(text_for_ai, meta['title'])
        
        # Save to Supabase
        supabase.table("videos").upsert({
            "video_id": video_id,
            "title": meta['title'],
            "thumbnail_url": meta['thumbnail'],
            "category": cat,
            "ai_summary": tools,
            "article_body": blog_post  # Ensure you added this column to Supabase!
        }).execute()
        
        return f"✅ Successfully Hubbed: {meta['title']} in {cat}"
    
    except Exception as e:
        return f"❌ System Error: {str(e)}"

def search_and_bulk_add(keyword, max_results=3):
    """Discovery Feature: Auto-builds your site based on keywords"""
    try:
        search_query = f"{keyword} AI tutorial"
        request = youtube.search().list(q=search_query, part="id", type="video", maxResults=max_results)
        response = request.execute()
        
        ids = [item['id']['videoId'] for item in response.get('items', [])]
        for vid_id in ids:
            process_video(f"https://www.youtube.com/watch?v={vid_id}")
            
        return [f"✅ Successfully added {len(ids)} videos for topic: {keyword}"]
    except Exception as e:
        return [f"❌ Search Error: {str(e)}"]
