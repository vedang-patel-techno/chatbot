#!/usr/bin/env python3
"""
Word Search Tool
Searches for a word in the documents table and exports matching sentences and URLs to a file.
"""

import os
import sys
import re
from datetime import datetime
from rag_shared import get_db_connection


def extract_sentences(text):
    """
    Split text into sentences using basic punctuation rules.
    
    Args:
        text: The text to split into sentences
        
    Returns:
        List of sentences
    """
    # Split on sentence-ending punctuation followed by space/newline
    # This regex handles ., !, ? followed by space or end of string
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def search_word_in_documents(search_word, output_file=None, tenant_id=None):
    """
    Search for a word in the documents table and export matching sentences to a file.
    
    Args:
        search_word: The word to search for
        output_file: Path to output file (optional, auto-generated if not provided)
        tenant_id: Optional tenant ID to filter results
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Build query based on whether tenant_id is provided
    if tenant_id:
        query = """
            SELECT d.content, d.source, p.tenant_id
            FROM documents d
            JOIN pages p ON d.page_url = p.url
            WHERE p.is_active = TRUE 
              AND p.tenant_id = %s
              AND d.content ILIKE %s
            ORDER BY d.source, d.id
        """
        cur.execute(query, (tenant_id, f'%{search_word}%'))
    else:
        query = """
            SELECT d.content, d.source, p.tenant_id
            FROM documents d
            JOIN pages p ON d.page_url = p.url
            WHERE p.is_active = TRUE 
              AND d.content ILIKE %s
            ORDER BY d.source, d.id
        """
        cur.execute(query, (f'%{search_word}%',))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    # Extract matching sentences from results
    matching_sentences = []
    for content, source, tid in results:
        sentences = extract_sentences(content)
        for sentence in sentences:
            # Check if the sentence contains the search word (case-insensitive)
            if re.search(re.escape(search_word), sentence, re.IGNORECASE):
                matching_sentences.append({
                    'sentence': sentence,
                    'url': source,
                    'tenant_id': tid
                })
    
    # Generate output filename if not provided
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_word = "".join(c if c.isalnum() else "_" for c in search_word)
        output_file = f"search_results_{safe_word}_{timestamp}.txt"
    
    # Get unique URLs for summary
    unique_urls = []
    seen_urls = set()
    for item in matching_sentences:
        url = item['url']
        if url not in seen_urls:
            unique_urls.append(url)
            seen_urls.add(url)
    
    # Write results to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"=" * 80 + "\n")
        f.write(f"SEARCH RESULTS FOR: '{search_word}'\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if tenant_id:
            f.write(f"Tenant ID: {tenant_id}\n")
        f.write(f"Total Matching Sentences: {len(matching_sentences)}\n")
        f.write(f"Total Unique URLs: {len(unique_urls)}\n")
        f.write(f"=" * 80 + "\n\n")
        
        # Write URL summary section
        if unique_urls:
            f.write("UNIQUE URLs WHERE WORD WAS FOUND:\n")
            f.write("-" * 80 + "\n")
            for idx, url in enumerate(unique_urls, 1):
                f.write(f"{idx}. {url}\n")
            f.write("\n" + "=" * 80 + "\n\n")
        
        if not matching_sentences:
            f.write("No matching sentences found.\n")
        else:
            f.write("DETAILED RESULTS:\n")
            f.write("=" * 80 + "\n\n")
            
            for idx, item in enumerate(matching_sentences, 1):
                sentence = item['sentence']
                url = item['url']
                tid = item['tenant_id']
                
                # Write sentence with URL shown inline
                f.write(f"Sentence #{idx}:\n")
                f.write(f"{sentence}\n")
                f.write(f"📍 Source URL: {url}\n")
                if tid:
                    f.write(f"🔑 Tenant ID: {tid}\n")
                f.write("\n" + "-" * 80 + "\n\n")
    
    return output_file, len(matching_sentences), len(unique_urls)


def main():
    """Main entry point for the script."""
    print("\n🔍 WORD SEARCH TOOL\n")
    
    # Get search word from command line or prompt
    if len(sys.argv) > 1:
        search_word = sys.argv[1]
    else:
        search_word = input("Enter word to search: ").strip()
    
    if not search_word:
        print("❌ No search word provided")
        sys.exit(1)
    
    # Ask for tenant ID (optional)
    tenant_id = input("Enter Tenant ID (press Enter to search all): ").strip()
    if not tenant_id:
        tenant_id = None
    
    # Ask for output file (optional)
    output_file = input("Enter output filename (press Enter for auto-generated): ").strip()
    if not output_file:
        output_file = None
    
    try:
        print(f"\n🔎 Searching for '{search_word}'...")
        result_file, count, unique_urls = search_word_in_documents(search_word, output_file, tenant_id)
        
        print(f"\n✅ Search complete!")
        print(f"📊 Found {count} matching sentences")
        print(f"🌐 Across {unique_urls} unique URLs")
        print(f"📄 Results saved to: {result_file}")
        print(f"📍 Full path: {os.path.abspath(result_file)}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
