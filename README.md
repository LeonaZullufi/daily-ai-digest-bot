# Daily AI Digest Bot

An automated pipeline that runs daily and posts a summarized YouTube video to a Discord channel using AI.

## Project Purpose

This bot automates the process of:
1. Fetching the latest video from a YouTube channel
2. Extracting the video transcript
3. Using AI models from OpenRouter to summarize the transcript
4. Posting the summaries to a Discord channel

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/daily-ai-digest-bot.git
cd daily-ai-digest-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
DISCORD_WEBHOOK_URL=your_discord_webhook_url
YOUTUBE_CHANNEL_URL=https://www.youtube.com/@t3dotgg
```

## Adding GitHub Secrets

To run this bot on GitHub Actions, you need to add secrets to your repository:

1. Go to your GitHub repository
2. Click on **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret** and add the following:

| Secret Name | Value |
|-------------|-------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `DISCORD_WEBHOOK_URL` | Your Discord webhook URL |
| `YOUTUBE_CHANNEL_URL` | The YouTube channel URL to monitor |

## How the Automation Works

### GitHub Actions Workflow

The workflow (`.github/workflows/daily.yml`) is configured to run:
- **Automatically**: Once per day at midnight (UTC) using cron: `0 0 * * *`
- **Manually**: You can trigger it manually using the "Run workflow" button

### Bot Flow

1. **Fetch Latest Video**: Uses YouTube RSS feed to get the most recent video from the channel
2. **Extract Transcript**: Uses yt-dlp to download English subtitles/transcript
3. **Fetch Free Models**: Calls OpenRouter API to get all available models
4. **Filter Free Models**: Filters models with free pricing (prompt: $0, completion: $0)
5. **Select Best Models**: Picks top 2 models by context length
6. **Generate Summaries**: Sends transcript to both models with summarization prompt
7. **Post to Discord**: Sends formatted embed with both summaries to Discord webhook

## File Structure

```
daily-ai-digest-bot/
├── bot.py                 # Main bot logic
├── requirements.txt       # Python dependencies
├── .github/
│   └── workflows/
│       └── daily.yml      # GitHub Actions workflow
└── README.md              # This file
```

## Requirements

- Python 3.11+
- requests
- yt-dlp
- python-dotenv
