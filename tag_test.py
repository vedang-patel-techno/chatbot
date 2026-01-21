import os
import psycopg2
from groq import Groq
from dotenv import lofad_dotenv
from datetime import date

# =====================================================
# LOAD ENV
# =====================================================
load_dotenv()

# =====================================================
# DB CONFIG
# =====================================================
DB_CONFIG = {
    "host": "localhost",
    "dbname": "database",
    "user": "vedang",
    "password": "vedang123",
    "port": 5432
}

# =====================================================
# GROQ CLIENT
# =====================================================
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# =====================================================
# DB CONNECTION
# =====================================================
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# =====================================================
# TAG TOOLS (SAFE FUNCTIONS)
# =====================================================

def tool_user_count():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM core_user;")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return f"Total users: {count}"

def tool_latest_users(limit=5):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT name, email, created_at
        FROM core_user
        ORDER BY created_at DESC
        LIMIT %s;
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return "No users found."

    return "\n".join(
        f"{name} ({email}) joined on {created}"
        for name, email, created in rows
    )

def tool_today_orders():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM core_order
        WHERE DATE(created_at) = %s;
    """, (date.today(),))
    count, total = cur.fetchone()
    cur.close()
    conn.close()
    return f"Today's orders: {count}, Total revenue: ₹{total}"

def tool_all_songs():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM core_songs;")
    count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return f"Total songs: {count}"



def tool_monthly_revenue():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM core_order
        WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE);
    """)
    total = cur.fetchone()[0]
    cur.close()
    conn.close()

    return f"This month's total revenue: ₹{total}"

# =====================================================
# INTENT DETECTOR (RULE-BASED)
# =====================================================
def detect_tool(question: str):
    q = question.lower()

    if "total number of songs" in q:
        return tool_all_songs

    if "how many user" in q or "total user" in q or "tell me how many user are there":
        return tool_user_count

    if "latest user" in q or "recent user" in q:
        return tool_latest_users

    if "today order" in q:
        return tool_today_orders

    if "monthly revenue" in q or "this month revenue" in q:
        return tool_monthly_revenue

    return None

# =====================================================
# OPTIONAL: LLM FORMATTER (NOT REQUIRED)
# =====================================================
def format_with_llm(raw_answer, question):
    prompt = f"""
User asked:
{question}

Database result:
{raw_answer}

Rewrite this in a clear, user-friendly way.
"""

    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=200
    )

    return res.choices[0].message.content

# =====================================================
# MAIN LOOP
# =====================================================
if __name__ == "__main__":
    print("\n🧠 PostgreSQL TAG Assistant Ready")
    print("Type 'exit' to quit\n")

    while True:
        question = input("❓ Ask a DB question: ").strip()

        if question.lower() == "exit":
            print("👋 Bye")
            break

        tool = detect_tool(question)

        if not tool:
            print("❌ I can only answer database-related questions.\n")
            continue

        raw_result = tool()

        # Optional LLM formatting
        final_answer = format_with_llm(raw_result, question)

        print("\n--- ANSWER ---\n")
        print(final_answer)
        print("\n--------------\n")
