import os
import requests
from bs4 import BeautifulSoup
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# 1. Fetch & clean website text
# -----------------------------
def fetch_website_text(url: str, max_chars: int = 8000) -> str:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        return f"ERROR_FETCHING_WEBSITE: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove unwanted tags
    for tag in soup(["script", "style", "noscript", "header", "footer", "svg"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)

    # Reduce whitespace
    text = " ".join(text.split())

    # Limit size to avoid token explosion   
    return text[:max_chars]


# -----------------------------
# 2. Ask Groq using strict context
# -----------------------------
def ask_website_bot(question: str, website_url: str):
    website_text = fetch_website_text(website_url)

    if website_text.startswith("ERROR"):
        return website_text

    prompt = f"""
You are a website assistant.

STRICT RULES:
- Answer ONLY using the website content provided.
- Do NOT use general knowledge.
- Do NOT guess.
- If the answer is not present, say:
  "I don't see this information on the website."

WEBSITE CONTENT:
{website_text}

QUESTION:
{"What treks are available on this website?"if not question else question}
"""

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=500,
        stream=True,
    )

    # Stream output
    for chunk in completion:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)


# -----------------------------
# 3. Run
# -----------------------------
if __name__ == "__main__":
    WEBSITE_URL = "https://www.technostacks.com/"
    QUESTION = "testemonials"

    ask_website_bot(QUESTION, WEBSITE_URL)
