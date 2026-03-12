import os
import json
import requests
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
YOUTUBE_CHANNEL_URL = os.getenv("YOUTUBE_CHANNEL_URL")


def fetch_latest_youtube_video(channel_url):
    """Fetch the latest video from a YouTube channel using Invidious API."""
    channel_handle = channel_url.split('@')[-1].rstrip('/')
    
    invidious_instances = [
        "https://invidious.fdn.dev",
        "https://invidious.jingl.xyz",
        "https://invidious.kavin.rocks"
    ]
    
    for instance in invidious_instances:
        try:
            response = requests.get(
                f"{instance}/api/v1/channels/{channel_handle}/latest",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                video = data['latestVideos'][0]
                return {
                    'id': video['videoId'],
                    'title': video['title'],
                    'url': f"https://www.youtube.com/watch?v={video['videoId']}"
                }
        except:
            continue
    
    raise ValueError("Could not fetch latest video from any Invidious instance")


def extract_transcript(video_url):
    """Extract the transcript of a YouTube video using yt-dlp."""
    ydl_opts = {
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'outtmpl': '/tmp/subtitle'
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        
        if 'subtitles' in info and 'en' in info['subtitles']:
            subtitle_url = info['subtitles']['en'][0]['url']
            response = requests.get(subtitle_url)
            response.raise_for_status()
            
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            transcript = []
            for element in root.findall('.//text'):
                transcript.append(element.text or '')
            
            return ''.join(transcript)
        
        if 'automatic_captions' in info and 'en' in info['automatic_captions']:
            subtitle_url = info['automatic_captions']['en'][0]['url']
            response = requests.get(subtitle_url)
            response.raise_for_status()
            
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            transcript = []
            for element in root.findall('.//text'):
                transcript.append(element.text or '')
            
            return ''.join(transcript)
    
    return None


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
