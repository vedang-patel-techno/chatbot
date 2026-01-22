import os
import re
import hashlib
import psycopg2
from urllib.parse import urlparse
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# =====================================================
# LOAD ENV
# =====================================================
load_dotenv()

# =====================================================
# CONFIG
# =====================================================
CHUNK_SIZE = 220
DB_CONFIG = {
    "host": "localhost",
    "dbname": "rag_db",
    "user": "vedang",
    "password": "vedang123",
    "port": 5432
}

# =====================================================
# GLOBALS
# =====================================================
EMBEDDER = SentenceTransformer(
    "nomic-ai/nomic-embed-text-v1",
    trust_remote_code=True
)

# =====================================================
# DB SETUP
# =====================================================
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# =====================================================
# UTILS
# =====================================================
def normalize_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

def clean_text(text):
    return text.replace("\x00", "").strip()

def page_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def chunk_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def chunk_text(text, size=200, overlap=50):
    words = text.split()
    step = size - overlap
    for i in range(0, len(words), step):
        yield " ".join(words[i:i + size])

def extract_keywords(question):
    words = re.findall(r'\b[a-zA-Z]{3,}\b', question.lower())
    return list(set(words))

