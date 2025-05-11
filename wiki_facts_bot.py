import os
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import openai
import urllib.parse
from flask import Flask
from threading import Thread

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Bots are running!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai.api_key = os.getenv('OPENAI_API_KEY')

# Get bot token from environment variable
BOT_TOKEN = os.getenv('WIKI_FACTS_TELE_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "👋 Welcome to the Wiki Facts Bot!\n\n"
        "I'll fetch interesting Wikipedia articles and provide you with "
        "summaries and fun facts to keep you engaged\n\n"
        "Available commands:\n"
        "📚 /fact - Get a random Wikipedia article\n"
        "🔍 /search [keyword] - Search for a specific topic\n"
        "❓ /help - Show all available commands"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/fact - Get a new random Wikipedia article with summary and fun facts\n"
        "/help - Show this help message\n"
        "/search [keyword] - Search for a Wikipedia article"
    )
    await update.message.reply_text(help_text)

def get_random_wiki_article():
    """Fetch a random Wikipedia article from the Good articles category."""
    url = "https://en.wikipedia.org/wiki/Special:RandomInCategory/Good_articles"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Get the title
    title = soup.find('h1', {'id': 'firstHeading'}).text
    
    # Get the main content
    content_div = soup.find('div', {'class': 'mw-parser-output'})
    paragraphs = content_div.find_all('p')
    
    # Combine the first few paragraphs for context
    content = ' '.join([p.text for p in paragraphs if p.text.strip()][:3])
    
    return {
        'title': title,
        'url': response.url,
        'content': content
    }

def generate_summary_and_insights(article):
    """Generate a summary and insights using OpenAI API."""
    prompt = f"""Article Title: {article['title']}
Content: {article['content']}

Please provide:
1. A concise summary (under 100 words) highlighting the most interesting facts
2. Three practical interesting things about this fact (under 30 words each)
3. End off with a question that is related to the fact and a short answer to it (under 30 words)

Format the response as:
SUMMARY:
[summary here]

Fun facts:
1. [first interesting thing]

2. [second interesting thing]

3. [third interesting thing]

Question: [question related to the fact]
Answer: [short answer to the question]
"""

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a knowledgeable friend who makes complex information accessible and relevant to daily life."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )
    
    return response.choices[0].message.content

async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a random Wikipedia article with summary and insights."""
    try:
        # Send "typing" action
        await update.message.chat.send_action(action="typing")
        
        # Get random article
        article = get_random_wiki_article()
        
        # Generate summary and insights
        summary_and_insights = generate_summary_and_insights(article)
        
        # Format the message
        message = (
            f"📚 *{article['title']}*\n\n"
            f"{summary_and_insights}\n\n"
            f"🔗 [Read full article]({article['url']})\n\n"
            "Use /fact to get another random article!"
        )
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in fact command: {str(e)}")
        await update.message.reply_text(
            "Sorry, I encountered an error while fetching the article. "
            "Please try again with /fact"
        )

def search_wikipedia(keyword):
    """Search Wikipedia for relevant articles."""
    # Use Wikipedia's search API
    search_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": keyword,
        "srlimit": 1,  # Get the most relevant result
        "srprop": "snippet|title"
    }
    
    try:
        response = requests.get(search_url, params=params)
        data = response.json()
        
        if "query" in data and "search" in data["query"] and data["query"]["search"]:
            # Get the most relevant result
            result = data["query"]["search"][0]
            title = result["title"]
            
            # Now get the full article content
            return get_wiki_article_by_title(title)
        else:
            return None, "No relevant articles found. Please try a different search term."
            
    except Exception as e:
        return None, f"An error occurred while searching: {str(e)}"

def get_wiki_article_by_title(title):
    """Fetch a Wikipedia article by its exact title."""
    encoded_title = urllib.parse.quote(title)
    url = f"https://en.wikipedia.org/wiki/{encoded_title}"
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get the main content
        content_div = soup.find('div', {'class': 'mw-parser-output'})
        paragraphs = content_div.find_all('p')
        
        # Combine the first few paragraphs for context
        content = ' '.join([p.text for p in paragraphs if p.text.strip()][:3])
        
        return {
            'title': title,
            'url': response.url,
            'content': content
        }, None
    except requests.exceptions.RequestException:
        return None, "Failed to fetch the article. Please try again."
    except Exception as e:
        return None, f"An error occurred: {str(e)}"

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /search command with a keyword."""
    if not context.args:
        await update.message.reply_text(
            "Please provide a keyword to search for.\n"
            "Example: /search artificial intelligence"
        )
        return

    keyword = ' '.join(context.args)
    await update.message.chat.send_action(action="typing")
    
    # First search for relevant articles
    article, error = search_wikipedia(keyword)
    
    if error:
        await update.message.reply_text(error)
        return
    
    try:
        # Generate summary and insights
        summary_and_insights = generate_summary_and_insights(article)
        
        # Format the message
        message = (
            f"🔍 *Search Result for: {keyword}*\n\n"
            f"📚 *{article['title']}*\n\n"
            f"{summary_and_insights}\n\n"
            f"🔗 [Read full article]({article['url']})\n\n"
            "Use /search [keyword] to search for another topic!"
        )
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in search command: {str(e)}")
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your search. "
            "Please try again with a different keyword."
        )

def setup_handlers(application):
    """Set up the handlers for this bot"""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("fact", fact))
    application.add_handler(CommandHandler("search", search))

def main():
    """Start all bots."""
    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Start each bot in a separate thread
    bot_threads = []
    for bot_name, token in bot_tokens.items():
        thread = Thread(target=run_bot, args=(token, bot_name))
        thread.start()
        bot_threads.append(thread)
        logger.info(f"Started thread for bot: {bot_name}")

    # Wait for all bot threads
    for thread in bot_threads:
        thread.join()

if __name__ == '__main__':
    main() 