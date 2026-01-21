# =====================================================
# IMPORTS
# =====================================================
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from rag_shared import (
    get_db_connection,
    normalize_url,
    clean_text,
    page_hash,
    chunk_hash,
    chunk_text,
    EMBEDDER,
    init_db
)

# =====================================================
# CONFIG
# =====================================================
MAX_DEPTH = 8
MAX_PAGES = 80
SELENIUM_WAIT = 3  # seconds

# =====================================================
# GLOBALS
# =====================================================
visited = set()
documents = []

# =====================================================
# SELENIUM SETUP
# =====================================================
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def fetch_rendered_html(driver, url):
    try:
        driver.get(url)
        time.sleep(SELENIUM_WAIT)  # wait for JS to load
        return driver.page_source
    except Exception as e:
        print(f"❌ Failed to load {url}: {e}")
        return None

# =====================================================
# CRAWLER
# =====================================================
def crawl(url, depth=0, base_domain=None, driver=None):
    if depth > MAX_DEPTH or len(visited) >= MAX_PAGES:
        return

    normalized = normalize_url(url)

    if normalized in visited:
        return

    visited.add(normalized)
    print(f"🌐 Crawling ({depth}): {normalized}")

    html = fetch_rendered_html(driver, normalized)
    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")

    # Remove noise (keeping header and footer as they may contain essential info)
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    text = clean_text(" ".join(soup.get_text().split()))
    if len(text) > 100:
        documents.append({
            "url": normalized,
            "text": text
        })

    # Follow internal links
    for link in soup.find_all("a", href=True):
        href = link["href"]

        if href.startswith(("#", "mailto:", "tel:")):
            continue

        next_url = normalize_url(urljoin(normalized, href))

        if urlparse(next_url).netloc != base_domain:
            continue

        crawl(next_url, depth + 1, base_domain, driver)

    time.sleep(0.5)

# =====================================================
# DB HELPERS
# =====================================================
def get_page_hash(url):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT content_hash FROM pages WHERE url = %s AND is_active = TRUE",
        (url,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def upsert_page(url, content_hash, tenant_id):
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
    """, (url, content_hash, tenant_id))
    conn.commit()
    cur.close()
    conn.close()


def delete_page_chunks(url):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM documents WHERE page_url = %s",
        (url,)
    )
    conn.commit()
    cur.close()
    conn.close()


def deactivate_removed_pages(active_urls, tenant_id):
    if not active_urls:
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE pages
        SET is_active = FALSE
        WHERE tenant_id = %s
          AND url NOT IN %s
    """, (tenant_id, tuple(active_urls)))
    conn.commit()
    cur.close()
    conn.close()

# =====================================================
# VECTOR DB SYNC
# =====================================================
def sync_vector_db(docs, tenant_id):
    conn = get_db_connection()
    cur = conn.cursor()

    active_pages = set()
    print("\n📦 Syncing embeddings...\n")

    for doc in docs:
        url = doc["url"]
        text = doc["text"]
        active_pages.add(url)

        new_hash = page_hash(text)
        old_hash = get_page_hash(url)

        if old_hash == new_hash:
            print(f"⏭ Skipped unchanged: {url}")
            continue

        print(f"🔄 Updating page: {url}")
        delete_page_chunks(url)

        chunks = list(chunk_text(text))
        embeddings = EMBEDDER.encode(chunks)

        for chunk, emb in zip(chunks, embeddings):
            cur.execute("""
                INSERT INTO documents (content, source, page_url, embedding, hash)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (hash) DO NOTHING
            """, (
                chunk,
                url,
                url,
                emb.tolist(),
                chunk_hash(chunk)
            ))

        upsert_page(url, new_hash, tenant_id)

    conn.commit()
    cur.close()
    conn.close()

    deactivate_removed_pages(active_pages, tenant_id)
    print("\n✅ Vector DB synced\n")

# =====================================================
# CONTROLLER
# =====================================================
def ingest_website(url, tenant_id):
    init_db()
    visited.clear()
    documents.clear()

    start_url = normalize_url(url)
    domain = urlparse(start_url).netloc

    driver = get_driver()
    try:
        crawl(start_url, base_domain=domain, driver=driver)
    finally:
        driver.quit()

    if not documents:
        raise RuntimeError("❌ No content scraped")

    sync_vector_db(documents, tenant_id)

# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":
    init_db()
    print("\n🚀 SELENIUM CRAWLER READY\n")

    while True:
        site = input("🌐 Website URL (or exit): ").strip()
        if site.lower() == "exit":
            break

        tenant_id = input("🔑 Tenant ID: ").strip()
        if not tenant_id:
            print("❌ Tenant ID required")
            continue

        ingest_website(site, tenant_id)
