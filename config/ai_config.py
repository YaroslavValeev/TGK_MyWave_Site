from dotenv import load_dotenv
import openai
import os
import logging
from scripts.gpt_integration import ask_gpt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure OpenAI
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

if not ASSISTANT_ID:
    raise ValueError("ASSISTANT_ID not found in environment variables")

openai.api_key = OPENAI_API_KEY

def get_assistant_response(user_message: str) -> str:
    """Get response from OpenAI assistant."""
    try:
        # Use the ask_gpt function from gpt_integration
        return ask_gpt(user_message)
    
    except Exception as e:
        logger.error(f"Error getting AI response: {e}")
        return "Извините, произошла ошибка при обработке вашего сообщения. Попробуйте позже."
