import os
from pathlib import Path
import PyPDF2

from .rag_shared import (
    get_db_connection,
    clean_text,
    page_hash,
    chunk_hash,
    chunk_text,
    EMBEDDER,
    init_db
)

# =====================================================
# PDF EXTRACTION
# =====================================================
def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file."""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
            
            return clean_text(text)
    except Exception as e:
        raise RuntimeError(f"❌ Failed to extract text from PDF: {e}")


# =====================================================
# DB HELPERS
# =====================================================
def get_page_hash_by_source(source):
    """Get the content hash for a given source (PDF filename)."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT content_hash FROM pages WHERE url = %s AND is_active = TRUE",
        (source,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def upsert_page(source, content_hash, tenant_id):
    """Insert or update page record for PDF."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pages (url, content_hash, is_active, tenant_id)
        VALUES (%s, %s, TRUE, %s)
        ON CONFLICT (url)
        DO UPDATE SET
            content_hash = EXCLUDED.content_hash,
            last_indexed = NOW(),
            is_active = TRUE,
            tenant_id = EXCLUDED.tenant_id
    """, (source, content_hash, tenant_id))
    conn.commit()
    cur.close()
    conn.close()


def delete_page_chunks(source):
    """Delete all chunks associated with a source."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM documents WHERE page_url = %s",
        (source,)
    )
    conn.commit()
    cur.close()
    conn.close()


# =====================================================
# VECTOR DB SYNC
# =====================================================
def sync_pdf_to_db(pdf_path, tenant_id):
    """Extract PDF content and sync to vector database."""
    # Use filename as source identifier
    source = f"pdf://{Path(pdf_path).name}"
    
    print(f"\n📄 Processing PDF: {pdf_path}")
    
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    
    if len(text) < 100:
        raise RuntimeError("❌ PDF contains insufficient text content")
    
    print(f"✅ Extracted {len(text)} characters")
    
    # Check if content has changed
    new_hash = page_hash(text)
    old_hash = get_page_hash_by_source(source)
    
    if old_hash == new_hash:
        print(f"⏭ PDF unchanged, skipping")
        return
    
    print(f"🔄 Updating PDF in database...")
    
    # Delete old chunks
    delete_page_chunks(source)
    
    # Chunk and embed
    conn = get_db_connection()
    cur = conn.cursor()
    
    chunks = list(chunk_text(text))
    embeddings = EMBEDDER.encode(chunks)
    
    print(f"📦 Generated {len(chunks)} chunks")
    
    for chunk, emb in zip(chunks, embeddings):
        cur.execute("""
            INSERT INTO documents (content, source, page_url, embedding, hash)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (hash) DO NOTHING
        """, (
            chunk,
            source,
            source,
            emb.tolist(),
            chunk_hash(chunk)
        ))
    
    conn.commit()
    cur.close()
    conn.close()
    
    # Update page record
    upsert_page(source, new_hash, tenant_id)
    
    print("✅ PDF successfully ingested\n")


# =====================================================
# CONTROLLER
# =====================================================
def ingest_pdf(pdf_path, tenant_id):
    """Main function to ingest a PDF file."""
    init_db()
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"❌ PDF file not found: {pdf_path}")
    
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("❌ File must be a PDF")
    
    sync_pdf_to_db(pdf_path, tenant_id)

