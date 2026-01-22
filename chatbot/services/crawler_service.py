import time
import hashlib
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager

from .rag_shared import (
    get_db_connection,
    normalize_url,
    clean_text,
    page_hash,
    chunk_text,
    chunk_hash,
    EMBEDDER
)

# =====================================================
# CONFIGURATION
# =====================================================
MAX_DEPTH = 20              # ⬆ increased
MAX_PAGES = 2000            # ⬆ increased
SELENIUM_WAIT = 0.2         # ⬆ increased

# =====================================================
# GLOBAL STATE
# =====================================================
visited_urls = set()
documents_buffer = []

# =====================================================
# SELENIUM DRIVER SETUP
# =====================================================
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver

# =====================================================
# HTML FETCHING
# =====================================================
def fetch_html(driver, url):
    try:
        driver.get(url)

        # ✅ Wait for DOM links (JS-heavy sites)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )

        time.sleep(SELENIUM_WAIT)
        html = driver.page_source

        # Debug: detect bot blocking
        if len(html) < 1000:
            print(f"⚠️ Possible block / empty page: {url}")

        return html

    except Exception as e:
        print(f"❌ Failed to load URL: {url} | Error: {e}")
        return None

# =====================================================
# DATABASE HELPERS
# =====================================================
def get_existing_page_hash(url):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT content_hash
        FROM pages
        WHERE url = %s
          AND is_active = TRUE
        """,
        (url,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def get_existing_document_hashes(url):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT hash
        FROM documents
        WHERE page_url = %s
        """,
        (url,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {row[0] for row in rows}


def upsert_page_record(url, content_hash, tenant_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO pages (url, content_hash, is_active, tenant_id)
        VALUES (%s, %s, TRUE, %s)
        ON CONFLICT (url)
        DO UPDATE SET
            content_hash = EXCLUDED.content_hash,
            is_active = TRUE,
            tenant_id = EXCLUDED.tenant_id,
            last_indexed = NOW()
        """,
        (url, content_hash, tenant_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def deactivate_removed_pages(active_urls, tenant_id):
    if not active_urls:
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE pages
        SET is_active = FALSE
        WHERE tenant_id = %s
          AND url NOT IN %s
        """,
        (tenant_id, tuple(active_urls))
    )
    conn.commit()
    cur.close()
    conn.close()

# =====================================================
# URL NORMALIZATION (SAFE FOR PAGINATION)
# =====================================================
def normalize_for_crawling(url):
    """
    Keeps query params to avoid killing pagination
    """
    parsed = urlparse(url)
    return urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        parsed.path.rstrip("/"),
        parsed.params,
        parsed.query,   # ✅ KEEP query params
        ""
    ))

# =====================================================
# CORE CRAWLER LOGIC
# =====================================================
def crawl_page(driver, current_url, depth, base_domain):
    if depth > MAX_DEPTH:
        return

    if len(visited_urls) >= MAX_PAGES:
        return

    normalized_url = normalize_for_crawling(current_url)

    if normalized_url in visited_urls:
        return

    visited_urls.add(normalized_url)

    print(f"🌐 Crawling ({len(visited_urls)}/{MAX_PAGES}) depth={depth}: {normalized_url}")

    html = fetch_html(driver, normalized_url)
    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")

    # -------------------------------------------------
    # Remove noise
    # -------------------------------------------------
    for tag in soup([
        "script", "style", "noscript"]):
        tag.decompose()

    # -------------------------------------------------
    # Extract visible text
    # -------------------------------------------------
    raw_text = soup.get_text(separator=" ")
    cleaned_text = clean_text(" ".join(raw_text.split()))

    print(f"📝 Text length: {len(cleaned_text)}")

    # ✅ Lower threshold so pages aren't silently dropped
    if len(cleaned_text) > 100:
        documents_buffer.append({
            "url": normalized_url,
            "text": cleaned_text
        })

    # -------------------------------------------------
    # Follow internal links (with subdomain support)
    # -------------------------------------------------
    for link in soup.find_all("a", href=True):
        href = link.get("href")

        if not href:
            continue

        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue

        next_url = normalize_for_crawling(
            urljoin(normalized_url, href)
        )

        parsed = urlparse(next_url)

        # ✅ Allow subdomains
        if not parsed.netloc.endswith(base_domain):
            continue

        crawl_page(
            driver=driver,
            current_url=next_url,
            depth=depth + 1,
            base_domain=base_domain
        )

# =====================================================
# VECTOR DATABASE SYNC
# =====================================================
def sync_vector_database(docs, tenant_id):
    conn = get_db_connection()
    cur = conn.cursor()

    active_pages = set()
    print("\n📦 Syncing vector database...\n")

    for doc in docs:
        page_url = doc["url"]
        page_text = doc["text"]
        active_pages.add(page_url)

        new_page_hash = page_hash(page_text)
        old_page_hash = get_existing_page_hash(page_url)

        if old_page_hash == new_page_hash:
            print(f"⏭ Unchanged: {page_url}")
            continue

        existing_chunk_hashes = get_existing_document_hashes(page_url)
        chunks = [c for c in chunk_text(page_text) if len(c) > 50]

        if not chunks:
            continue

        embeddings = EMBEDDER.encode(
            ["search_document: " + c for c in chunks],
                normalize_embeddings=True
            )

        inserted = skipped = 0

        for chunk, embedding in zip(chunks, embeddings):
            h = chunk_hash(chunk)
            if h in existing_chunk_hashes:
                skipped += 1
                continue

            cur.execute(
                """
                INSERT INTO documents
                (content, source, page_url, embedding, hash)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (hash) DO NOTHING
                """,
                (chunk, page_url, page_url, embedding.tolist(), h)
            )
            inserted += 1

        upsert_page_record(page_url, new_page_hash, tenant_id)

        print(f"🔄 {page_url} | new: {inserted}, reused: {skipped}")

    conn.commit()
    cur.close()
    conn.close()

    deactivate_removed_pages(active_pages, tenant_id)
    print("\n✅ Vector database sync complete\n")

# =====================================================
# CONTROLLER
# =====================================================
def ingest_website(start_url, tenant_id):
    visited_urls.clear()
    documents_buffer.clear()

    normalized_start = normalize_for_crawling(start_url)
    base_domain = urlparse(normalized_start).netloc.split(":")[0]

    driver = get_driver()
    try:
        crawl_page(driver, normalized_start, 0, base_domain)
    finally:
        driver.quit()

    if not documents_buffer:
        print("❌ No content collected")
        return

    sync_vector_database(documents_buffer, tenant_id)

