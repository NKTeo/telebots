import os
import logging
import threading
import time
import asyncio
import requests
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
from wiki_facts_bot import setup_handlers as setup_wiki_facts_bot
from business_ideas_bot import setup_handlers as setup_business_ideas_bot

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Store bot applications
bot_applications = {}

# Global event loop and lock
loop = None
loop_lock = threading.Lock()

def run_flask(port=8080):
    app.run(host='0.0.0.0', port=port)

def ping_server():
    """Ping the server to keep it alive."""
    while True:
        try:
            # Get the server URL from environment variable or use localhost for development
            server_url = os.getenv('SERVER_URL', 'http://localhost:8080')
            response = requests.get(server_url)
            logger.info(f"Ping response: {response.status_code}")
        except Exception as e:
            logger.error(f"Error pinging server: {str(e)}")
        time.sleep(840)  # Ping every 14 minutes

async def setup_webhook(application: Application, token: str, webhook_url: str):
    """Set up webhook for a bot."""
    webhook_path = f"{webhook_url}/{token}"
    await application.bot.set_webhook(url=webhook_path)
    logger.info(f"Webhook set up for bot {token[:8]}... at {webhook_path}")

def get_or_create_eventloop():
    """Get the current event loop or create a new one."""
    global loop
    with loop_lock:
        if loop is None or loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

@app.route('/<token>', methods=['POST'])
def webhook(token):
    """Handle incoming webhook updates."""
    if token not in bot_applications:
        return "Invalid token", 400

    application = bot_applications[token]
    update = Update.de_json(request.get_json(), application.bot)
    
    try:
        # Get or create event loop
        current_loop = get_or_create_eventloop()
        
        # Run the async function in the event loop
        current_loop.run_until_complete(application.process_update(update))
        return "OK"
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return "Error processing update", 500

@app.route('/')
def home():
    return "Bots are running!"

async def main():
    # Create and set the global event loop
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Get bot tokens
    wiki_facts_token = os.getenv('WIKI_FACTS_TELE_TOKEN')
    business_ideas_token = os.getenv('BUSINESS_IDEAS_TELE_TOKEN')

    if not wiki_facts_token or not business_ideas_token:
        logger.error("Missing bot tokens in environment variables")
        return

    # Get webhook URL from environment or use ngrok for local development
    webhook_url = os.getenv('WEBHOOK_URL')
    is_local = os.getenv('ENVIRONMENT', 'production') == 'development'

    if is_local:
        try:
            from pyngrok import ngrok, conf
            ngrok_auth_token = os.getenv('NGROK_AUTH_TOKEN')
            if not ngrok_auth_token:
                logger.error("NGROK_AUTH_TOKEN not found in environment variables!")
                return
                
            conf.get_default().auth_token = ngrok_auth_token
            port = 8080
            public_url = ngrok.connect(port).public_url
            webhook_url = public_url
            logger.info(f"Local development: ngrok tunnel established at {public_url}")
        except ImportError:
            logger.error("pyngrok not installed. Please run: pip install pyngrok")
            return
        except Exception as e:
            logger.error(f"Failed to start ngrok: {str(e)}")
            return
    elif not webhook_url:
        logger.error("WEBHOOK_URL not set in environment variables")
        return

    try:
        # Initialize Wiki Facts Bot
        wiki_facts_app = Application.builder().token(wiki_facts_token).build()
        setup_wiki_facts_bot(wiki_facts_app)
        await wiki_facts_app.initialize()
        bot_applications[wiki_facts_token] = wiki_facts_app
        await setup_webhook(wiki_facts_app, wiki_facts_token, webhook_url)
        logger.info("Wiki Facts Bot webhook set up")

        # Initialize Business Ideas Bot
        business_ideas_app = Application.builder().token(business_ideas_token).build()
        setup_business_ideas_bot(business_ideas_app)
        await business_ideas_app.initialize()
        bot_applications[business_ideas_token] = business_ideas_app
        await setup_webhook(business_ideas_app, business_ideas_token, webhook_url)
        logger.info("Business Ideas Bot webhook set up")

        # Start Flask server in a separate thread
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        # Start ping mechanism in a separate thread
        ping_thread = threading.Thread(target=ping_server)
        ping_thread.daemon = True
        ping_thread.start()

        # Keep the main thread alive
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        # Remove webhooks and shutdown applications
        for token, application in bot_applications.items():
            try:
                await application.bot.delete_webhook()
                await application.shutdown()
                logger.info(f"Removed webhook and shut down bot with token: {token[:8]}...")
            except Exception as e:
                logger.error(f"Error during shutdown: {str(e)}")

if __name__ == '__main__':
    asyncio.run(main()) 