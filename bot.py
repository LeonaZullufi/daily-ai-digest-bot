import os
import json
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
YOUTUBE_CHANNEL_URL = os.getenv("YOUTUBE_CHANNEL_URL")


def fetch_latest_youtube_video(channel_url):
    """Fetch the latest video from a YouTube channel using RSS feed."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.get(channel_url, headers=headers, timeout=30)
    response.raise_for_status()
    
    import re
    channel_id_match = re.search(r'"channelId":"UC([a-zA-Z0-9_-]{22})"', response.text)
    if not channel_id_match:
        channel_id_match = re.search(r'channel_id=UC([a-zA-Z0-9_-]{22})', response.text)
    
    if not channel_id_match:
        raise ValueError("Could not find channel ID")
    
    channel_id = "UC" + channel_id_match.group(1)
    
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    response = requests.get(rss_url, headers=headers, timeout=30)
    response.raise_for_status()
    
    import xml.etree.ElementTree as ET
    
    namespaces = {
        'atom': 'http://www.w3.org/2005/Atom',
        'yt': 'http://www.youtube.com/xml/schemas/2015'
    }
    
    root = ET.fromstring(response.content)
    
    entry = root.find('atom:entry', namespaces)
    if entry is None:
        raise ValueError("No entry found in RSS feed")
    
    video_id_elem = entry.find('yt:videoId', namespaces)
    if video_id_elem is None:
        raise ValueError("No videoId found in entry")
    
    video_id = video_id_elem.text
    
    title_elem = entry.find('atom:title', namespaces)
    video_title = title_elem.text if title_elem is not None else "Untitled"
    
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    return {
        'id': video_id,
        'title': video_title,
        'url': video_url
    }


def extract_transcript(video_url):
    """Extract the transcript of a YouTube video using youtube-transcript-api."""
    import re
    
    video_id_match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', video_url)
    if not video_id_match:
        raise ValueError("Could not extract video ID from URL")
    
    video_id = video_id_match.group(1)
    
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        
        transcript_parts = [item['text'] for item in transcript_list]
        transcript = ' '.join(transcript_parts)
        
        return transcript
    except Exception as e:
        raise ValueError(f"Could not fetch transcript: {str(e)}")


def fetch_free_openrouter_models():
    """Fetch the list of models from OpenRouter API and filter only models with free pricing."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        "https://openrouter.ai/api/v1/models",
        headers=headers
    )
    response.raise_for_status()
    
    data = response.json()
    free_models = []
    
    for model in data.get('data', []):
        pricing = model.get('pricing', {})
        if pricing.get('prompt') == '0' and pricing.get('completion') == '0':
            free_models.append({
                'id': model['id'],
                'name': model['name'],
                'context_length': model.get('context_length', 0)
            })
    
    return free_models


def pick_best_models(free_models, count=2):
    """Select the best models based on context length."""
    sorted_models = sorted(free_models, key=lambda x: x['context_length'], reverse=True)
    return sorted_models[:count]


def summarize_transcript(transcript, model_id):
    """Send the transcript to an OpenRouter model with a summarization prompt."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/daily-ai-digest-bot",
        "X-Title": "Daily AI Digest Bot"
    }
    
    prompt = "Summarize this YouTube video transcript in 5 bullet points.\n\n" + transcript[:15000]
    
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000
    }
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    
    data = response.json()
    return data['choices'][0]['message']['content']


def send_to_discord(video_info, summaries):
    """Send the result to a Discord channel using a webhook."""
    embed = {
        "title": f"📺 Daily AI Digest - {video_info['title']}",
        "url": video_info['url'],
        "color": 5814783,
        "fields": []
    }
    
    for i, summary in enumerate(summaries):
        embed["fields"].append({
            "name": f"Summary {i + 1}",
            "value": summary[:1000]
        })
    
    payload = {
        "embeds": [embed],
        "content": "🎬 **New AI Daily Digest Available!**"
    }
    
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    response.raise_for_status()


def main():
    """Main function to run the daily digest bot."""
    print("Fetching latest YouTube video...")
    video = fetch_latest_youtube_video(YOUTUBE_CHANNEL_URL)
    print(f"Found video: {video['title']}")
    
    print("Extracting transcript...")
    transcript = extract_transcript(video['url'])
    if not transcript:
        print("No transcript available for this video.")
        return
    
    print("Fetching free OpenRouter models...")
    free_models = fetch_free_openrouter_models()
    print(f"Found {len(free_models)} free models")
    
    print("Selecting best 2 models by context length...")
    best_models = pick_best_models(free_models, 2)
    print(f"Selected models: {[m['name'] for m in best_models]}")
    
    print("Generating summaries...")
    summaries = []
    for model in best_models:
        print(f"Summarizing with {model['name']}...")
        summary = summarize_transcript(transcript, model['id'])
        summaries.append(summary)
    
    print("Sending to Discord...")
    send_to_discord(video, summaries)
    print("Done!")


if __name__ == "__main__":
    main()
