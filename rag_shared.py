import os
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
EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")

# =====================================================
# DB SETUP
# =====================================================
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE,
            tenant_id TEXT,
            content_hash TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            last_indexed TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            content TEXT,
            source TEXT,
            page_url TEXT,
            embedding VECTOR(384),
            hash TEXT UNIQUE
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

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

def chunk_text(text):
    words = text.split()
    for i in range(0, len(words), CHUNK_SIZE):
        yield " ".join(words[i:i + CHUNK_SIZE])     
