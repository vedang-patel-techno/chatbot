import os
import difflib
import re
from collections import Counter
from groq import Groq
from .rag_shared import (
    get_db_connection, EMBEDDER
)

# =====================================================
# CONFIG
# =====================================================
TOP_K = 15
MAX_CONTEXT_CHARS = 3500
MAX_COMPLETION_TOKENS = 300
FUZZY_THRESHOLD = 0.6  # Minimum similarity for fuzzy matching (0.0 to 1.0)
MIN_WORD_LENGTH = 3    # Only apply fuzzy matching to words longer than this

# =====================================================
# FUZZY SEARCH FUNCTIONALITY
# =====================================================
def build_vocabulary(tenant_id):
    """
    Build a vocabulary from all document content for fuzzy matching.
    
    Args:
        tenant_id: The tenant ID to filter documents
        
    Returns:
        Set of unique words from the document corpus
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.content
        FROM documents d
        JOIN pages p ON d.page_url = p.url
        WHERE p.is_active = TRUE AND p.tenant_id = %s
    """, (tenant_id,))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    vocabulary = set()
    for (content,) in rows:
        # Extract words using regex (alphanumeric + common punctuation)
        words = re.findall(r'\b[a-zA-Z]{2,}\b', content.lower())
        vocabulary.update(words)
    
    return vocabulary

def fuzzy_correct_word(word, vocabulary, threshold=FUZZY_THRESHOLD):
    """
    Find the best fuzzy match for a word in the vocabulary.
    
    Args:
        word: The potentially misspelled word
        vocabulary: Set of correct words
        threshold: Minimum similarity score (0.0 to 1.0)
        
    Returns:
        Best matching word or original word if no good match found
    """
    if len(word) < MIN_WORD_LENGTH:
        return word
    
    word_lower = word.lower()
    
    # If word is already in vocabulary, return as-is
    if word_lower in vocabulary:
        return word
    
    # Find best matches using difflib
    matches = difflib.get_close_matches(
        word_lower, 
        vocabulary, 
        n=1, 
        cutoff=threshold
    )
    
    if matches:
        return matches[0]
    
    return word

def apply_fuzzy_correction(question, tenant_id):
    """
    Apply fuzzy correction to the entire question.
    
    Args:
        question: The user's question
        tenant_id: The tenant ID for vocabulary building
        
    Returns:
        Tuple of (corrected_question, corrections_made)
    """
    # Build vocabulary from document corpus
    vocabulary = build_vocabulary(tenant_id)
    
    if not vocabulary:
        return question, []
    
    # Extract words from question
    words = re.findall(r'\b[a-zA-Z]+\b', question)
    corrections = []
    corrected_words = []
    
    for word in words:
        corrected = fuzzy_correct_word(word, vocabulary)
        corrected_words.append(corrected)
        
        if corrected.lower() != word.lower():
            corrections.append((word, corrected))
    
    # Reconstruct the question with corrections
    corrected_question = question
    for original, corrected in corrections:
        # Use word boundaries to avoid partial replacements
        pattern = r'\b' + re.escape(original) + r'\b'
        corrected_question = re.sub(pattern, corrected, corrected_question, flags=re.IGNORECASE)
    
    return corrected_question, corrections

SYNONYM_GROUPS = {
    # Contact information
    "phone": ["phone", "telephone", "mobile", "contact number", "phone number", "cell", "call"],
    "email": ["email", "e-mail", "mail", "email address"],
    "address": ["address", "location", "office", "office address", "place", "where"],
    "contact": ["contact", "reach", "get in touch", "phone", "email"],
    
    # Time related
    "hours": ["hours", "timing", "time", "schedule", "open", "close", "working hours"],
    "appointment": ["appointment", "booking", "schedule", "reservation"],
    
    # Common queries
    "cost": ["cost", "price", "fee", "charge", "rate", "pricing"],
    "service": ["service", "services", "offering", "offerings", "provide"],
    "doctor": ["doctor", "physician", "dr", "specialist"],
    
    # General
    "website": ["website", "site", "web", "online", "url"],
}

def expand_query(question):
    """
    Expand the query with synonyms to improve retrieval.
    
    Args:
        question: The original user question
        
    Returns:
        Expanded query string with synonyms added
    """
    question_lower = question.lower()
    expanded_terms = [question]  # Always include original query
    
    # Check each synonym group
    for base_term, synonyms in SYNONYM_GROUPS.items():
        # If any synonym is in the question, add all related terms
        for synonym in synonyms:
            if synonym in question_lower:
                # Add other synonyms from this group
                expanded_terms.extend([s for s in synonyms if s not in question_lower])
                break  # Only add once per group
    
    # Join all terms together
    return " ".join(expanded_terms)

# =====================================================
# RETRIEVAL
# =====================================================
def retrieve_context(question, tenant_id):
    """
    Hybrid RAG retrieval:
    1. Fuzzy correction
    2. Synonym expansion
    3. Query expansion for embeddings
    4. Vector similarity search
    5. Keyword fallback (ILIKE)
    6. Merge + deduplicate
    """

    # -------------------------------------------------
    # 1️⃣ Fuzzy correction
    # -------------------------------------------------
    corrected_question, corrections = apply_fuzzy_correction(question, tenant_id)

    if corrections:
        fixes = ", ".join([f"{o}→{c}" for o, c in corrections])
        print(f"🔧 Auto-corrected: {fixes}")

    # -------------------------------------------------
    # 2️⃣ Synonym expansion
    # -------------------------------------------------
    expanded_question = expand_query(corrected_question)

    # -------------------------------------------------
    # 3️⃣ Query embedding (FIXED)
    # -------------------------------------------------
    query_embedding = EMBEDDER.encode(
        ["search_query: " + expanded_question],
        normalize_embeddings=True
    )[0]

    query_embedding = query_embedding.tolist()  # pgvector fix

    # -------------------------------------------------
    # DB connection (MUST come before execute)
    # -------------------------------------------------
    conn = get_db_connection()
    cur = conn.cursor()

    # -------------------------------------------------
    # 4️⃣ Vector similarity search
    # -------------------------------------------------
    cur.execute("""
        SELECT d.content, d.source
        FROM documents d
        JOIN pages p ON d.page_url = p.url
        WHERE p.is_active = TRUE
          AND p.tenant_id = %s
        ORDER BY d.embedding <=> %s::vector
        LIMIT %s
    """, (tenant_id, query_embedding, TOP_K))

    vector_rows = cur.fetchall()

    # -------------------------------------------------
    # 5️⃣ Keyword fallback search
    # -------------------------------------------------
    keywords = re.findall(r'\b[a-zA-Z]{3,}\b', corrected_question.lower())
    keywords = list(set(keywords))[:4]

    keyword_rows = []

    for kw in keywords:
        cur.execute("""
            SELECT d.content, d.source
            FROM documents d
            JOIN pages p ON d.page_url = p.url
            WHERE p.is_active = TRUE
              AND p.tenant_id = %s
              AND d.content ILIKE %s
            LIMIT 3
        """, (tenant_id, f"%{kw}%"))

        keyword_rows.extend(cur.fetchall())

    cur.close()
    conn.close()

    # -------------------------------------------------
    # 6️⃣ Merge + deduplicate
    # -------------------------------------------------
    combined = vector_rows + keyword_rows

    seen = set()
    unique_rows = []

    for text, src in combined:
        h = hash(text)
        if h not in seen:
            seen.add(h)
            unique_rows.append((text, src))

    # -------------------------------------------------
    # 7️⃣ Build final context
    # -------------------------------------------------
    context = []
    total_chars = 0

    for text, src in unique_rows:
        entry = f"[{src}] {text}"
        if total_chars + len(entry) > MAX_CONTEXT_CHARS:
            break
        context.append(entry)
        total_chars += len(entry)

    # -------------------------------------------------
    # 8️⃣ Debug
    # -------------------------------------------------
    print("\n🔍 RETRIEVAL DEBUG:")
    for i, c in enumerate(context):
        print(f"\n--- Chunk {i+1} ---\n{c[:300]}")

    return context

# =====================================================
# MAIN
# =====================================================
def ask_llm(question, context_chunks):
    if not context_chunks:
        return "I don't know based on the website."

    prompt = f"""
Answer using ONLY the context.
You may paraphrase or summarize clearly stated facts.
If the answer cannot be found or reasonably inferred, say:
"I don't know based on the website."

    CONTEXT:
    {chr(10).join(context_chunks)}

    QUESTION:
    {question}

    ANSWER:
    """

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=MAX_COMPLETION_TOKENS
    )

    return res.choices[0].message.content


def get_chatbot_response(question, tenant_id):
    """Main function to get chatbot response."""
    context = retrieve_context(question, tenant_id)
    answer = ask_llm(question, context)
    return answer

