import os
from groq import Groq
from rag_shared import (
    get_db_connection, EMBEDDER
)

# =====================================================
# CONFIG
# =====================================================
TOP_K = 10
MAX_CONTEXT_CHARS = 3500
MAX_COMPLETION_TOKENS = 300

# =====================================================
# RETRIEVAL
# =====================================================
def retrieve_context(question, tenant_id):
    query_embedding = EMBEDDER.encode(question).tolist()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.content, d.source
        FROM documents d
        JOIN pages p ON d.page_url = p.url
        WHERE p.is_active = TRUE AND p.tenant_id = %s
        ORDER BY d.embedding <=> %s::vector
        LIMIT %s
    """, (tenant_id, query_embedding, TOP_K))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    context = []
    size = 0
    for text, src in rows:
        entry = f"[{src}] {text}"
        if size + len(entry) > MAX_CONTEXT_CHARS:
            break
        context.append(entry)
        size += len(entry)

    return context

# =====================================================
# LLM
# =====================================================
def ask_llm(question, context_chunks):
    if not context_chunks:
        return "I don't know based on the website."

    prompt = f"""
Answer ONLY from the context.
If not present, say:
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

# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":
    print("\n💬 CHATBOT READY\n")

    tenant_id = input("\n🔑 Enter Tenant ID: ").strip()
    
    while True:
        q = input("\n❓ Ask (or exit): ").strip()
        if q.lower() == "exit":
            break

        ctx = retrieve_context(q, tenant_id)
        ans = ask_llm(q, ctx)
        print("\n--- ANSWER ---\n", ans, "\n")
