import os 
import logging
from dotenv import load_dotenv
# -------------------------------
# Configuration
# -------------------------------

load_dotenv(".env")  # Load environment variables from .env file

# OpenRouter - https://openrouter.ai
OR_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OR_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.3-70b-instruct:free"
REQUESTS_PER_MINUTE = 20
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE
MAX_TOTAL_TOKENS = 130000  


# HuggingFace - https://huggingface.co
HF_API_URL = "https://api-inference.huggingface.co/models" 
HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

# Github API
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

logging.basicConfig(level=logging.INFO)

# Github metadata api
GITHUB_METADATA_URL = "http://localhost:3800/metadata/user"
GITHUB_CONTENT_URL = "http://localhost:3800/metadata/content/user"

#GITHUB_METADATA_URL = "https://observatory.openebench.bsc.es/github-metadata-api/metadata/user"
#GITHUB_CONTENT_URL = "https://observatory.openebench.bsc.es/github-metadata-api/metadata/content/user"

# Gitlab API
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")



logging.basicConfig(level=logging.INFO)