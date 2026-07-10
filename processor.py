def extract_tools_with_ai(text_content):
    """Uses Groq to identify tools AND a category"""
    if not text_content or len(text_content) < 20:
        return "General AI", "AI Tools"

    # Pre-defined categories for the AI to choose from
    categories = "Image Generation, Video & Animation, Automation & Workflow, AI Writing & Chat, Coding & Tech, Voice & Audio"

    prompt = f"""
    Analyze the following YouTube transcript:
    1. Categorize this video into ONE of these: [{categories}].
    2. List the AI tools mentioned.
    
    Format your response EXACTLY like this:
    Category: [Chosen Category]
    Tools: [Tool1, Tool2]

    Text: {text_content[:8000]}
    """
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        response = completion.choices[0].message.content
        
        # Simple parsing logic
        cat = response.split("Category:")[1].split("Tools:")[0].strip()
        tools = response.split("Tools:")[1].strip()
        return cat, tools
    except:
        return "General AI", "AI Tools"

# Also update the process_video function to save this category:
def process_video(video_url):
    # ... (existing code for ID and metadata)
    
    # Updated AI call
    category_found, tools_found = extract_tools_with_ai(text_for_ai)
    
    supabase.table("videos").upsert({
        "video_id": video_id,
        "title": meta['title'],
        "thumbnail_url": meta['thumbnail'],
        "category": category_found, # <--- Save the real category here
        "ai_summary": tools_found
    }).execute()
    
    return f"✅ Added to {category_found}: {meta['title']}"
