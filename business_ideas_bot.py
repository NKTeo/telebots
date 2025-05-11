import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import openai
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
BOT_TOKEN = os.getenv('BUSINESS_IDEAS_TELE_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "👋 Welcome to the Business Ideas Bot!\n\n"
        "I'll help you generate innovative business ideas and provide "
        "detailed analysis for each one.\n\n"
        "Available commands:\n"
        "💡 /idea - Get a new business idea\n"
        "🔍 /analyze [idea] - Get detailed analysis of a business idea\n"
        "❓ /help - Show all available commands"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/idea - Get a new business idea\n"
        "/analyze [idea] - Get detailed analysis of a business idea\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)

def generate_business_idea():
    """Generate a business idea using OpenAI API."""
    prompt = """Generate a unique and innovative business idea. Include:
1. Business Name
2. One-line description
3. Target market
4. Key value proposition
5. Initial investment range
6. Potential challenges
7. First steps to start

Format the response as:
BUSINESS NAME:
[name]

DESCRIPTION:
[one-line description]

TARGET MARKET:
[target market]

VALUE PROPOSITION:
[key value proposition]

INVESTMENT:
[investment range]

CHALLENGES:
[potential challenges]

FIRST STEPS:
[first steps to start]
"""

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a business consultant with expertise in entrepreneurship and market analysis."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.8
    )
    
    return response.choices[0].message.content

def analyze_business_idea(idea):
    """Analyze a business idea using OpenAI API."""
    prompt = f"""Analyze this business idea: {idea}

Please provide:
1. Market Analysis
2. Competitive Advantage
3. Revenue Model
4. Marketing Strategy
5. Risk Assessment
6. Growth Potential
7. Action Plan

Format the response as:
MARKET ANALYSIS:
[analysis]

COMPETITIVE ADVANTAGE:
[advantages]

REVENUE MODEL:
[model]

MARKETING STRATEGY:
[strategy]

RISK ASSESSMENT:
[risks]

GROWTH POTENTIAL:
[potential]

ACTION PLAN:
[plan]
"""

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a business consultant with expertise in entrepreneurship and market analysis."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800,
        temperature=0.7
    )
    
    return response.choices[0].message.content

async def idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a new business idea."""
    try:
        # Send "typing" action
        await update.message.chat.send_action(action="typing")
        
        # Generate business idea
        idea = generate_business_idea()
        
        # Format the message
        message = (
            f"💡 *New Business Idea*\n\n"
            f"{idea}\n\n"
            "Use /idea to get another business idea!\n"
            "Use /analyze [idea] to get detailed analysis of any business idea."
        )
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in idea command: {str(e)}")
        await update.message.reply_text(
            "Sorry, I encountered an error while generating the business idea. "
            "Please try again with /idea"
        )

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /analyze command with a business idea."""
    if not context.args:
        await update.message.reply_text(
            "Please provide a business idea to analyze.\n"
            "Example: /analyze A mobile app for pet sitting services"
        )
        return

    idea = ' '.join(context.args)
    await update.message.chat.send_action(action="typing")
    
    try:
        # Generate analysis
        analysis = analyze_business_idea(idea)
        
        # Format the message
        message = (
            f"🔍 *Analysis for: {idea}*\n\n"
            f"{analysis}\n\n"
            "Use /analyze [idea] to analyze another business idea!"
        )
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in analyze command: {str(e)}")
        await update.message.reply_text(
            "Sorry, I encountered an error while analyzing your business idea. "
            "Please try again with a different idea."
        )

def setup_handlers(application):
    """Set up the handlers for this bot"""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("idea", idea))
    application.add_handler(CommandHandler("analyze", analyze)) 