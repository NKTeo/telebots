# Multi-Bot Telegram Application

This application runs multiple Telegram bots simultaneously with a ping mechanism to keep the instance alive on Render.com.

## Local Setup

1. **Create a `.env` file** in the root directory with the following variables:
   ```
   # Bot Tokens
   WIKI_FACTS_TELE_TOKEN=your_wiki_facts_bot_token_here
   BUSINESS_IDEAS_GENERATOR_TELE_TOKEN=your_business_ideas_bot_token_here

   # OpenAI API Key (required for both bots)
   OPENAI_API_KEY=your_openai_api_key_here

   # Render.com URL (for keeping the instance alive)
   RENDER_URL=https://your-app-name.onrender.com

   # Port (default is 8080)
   PORT=8080
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

## Bot Features

### Wiki Facts Bot
- `/start` - Start the bot
- `/help` - Show help message
- `/fact` - Get a random Wikipedia article with summary and fun facts
- `/search [keyword]` - Search for a specific Wikipedia article

### Business Ideas Bot
- `/start` - Start the bot
- `/help` - Show help message
- `/random` - Generate a random business idea
- `/idea [keywords]` - Generate a business idea based on keywords

## Deploying to Render.com

1. Create a new Web Service on Render.com
2. Connect your repository
3. Set the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
4. Add these environment variables in Render.com:
   - `WIKI_FACTS_TELE_TOKEN`
   - `BUSINESS_IDEAS_GENERATOR_TELE_TOKEN`
   - `OPENAI_API_KEY`
   - `RENDER_URL` (set to your Render.com app URL)
   - `PORT` (Render.com will set this automatically)

## Health Check

The application includes a health check endpoint at `/health` that returns the status and timestamp. This is used by Render.com to keep the instance alive.

## Logging

All bot activities and errors are logged with timestamps. Check the logs in Render.com dashboard or your local console for debugging.

## Adding New Bots

1. Create a new bot file in the `bots` directory
2. Implement the bot's functionality
3. Add a `setup_handlers` function
4. Update `main.py` to include the new bot
5. Add the bot's token to your environment variables 