from dotenv import load_dotenv
import os

load_dotenv()  # This loads .env from the current working directory
print("Loaded OpenAI Key:", os.getenv("OPENAI_KEY"))
