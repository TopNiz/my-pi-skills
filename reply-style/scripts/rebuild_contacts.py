#!/usr/bin/env python3
"""
Rebuild contact index and style profiles from saved message files.
Called after fetch_sent.py to:
  1. Scan all saved contact message files
  2. Rebuild the index.json
  3. Analyze language preferences per contact

Usage:
    python3 rebuild_contacts.py config.json
"""

import json
import os
import sys
import re
from pathlib import Path


def detect_language(body):
    """Rough language detection based on common patterns."""
    if not body:
        return "unknown"
    
    # French indicators
    french_patterns = r'\b(je|tu|il|elle|nous|vous|ils|elles|le|la|les|un|une|des|du|de|et|ou|mais|donc|car|pour|avec|dans|sur|sous|entre|par|pas|plus|très|bonjour|salut|merci|svp|stp|cordialement|bien|cdlt)\b'
    # English indicators
    english_patterns = r'\b(the|a|an|is|are|was|were|have|has|had|do|does|did|will|would|can|could|should|may|might|hello|hi|hey|thanks|thank|please|best|regards|cheers)\b'
    # Arabic indicators
    arabic_patterns = r'[\u0600-\u06FF]'

    body_lower = body.lower()
    
    french_count = len(re.findall(french_patterns, body_lower, re.IGNORECASE))
    english_count = len(re.findall(english_patterns, body_lower, re.IGNORECASE))
    arabic_count = len(re.findall(arabic_patterns, body))

    # Normalize by body length
    words = body_lower.split()
    word_count = len(words)
    if word_count < 3:
        return "unknown"

    # Simple heuristic: which language has more matches
    # French words are very common in English too, so weight English higher
    if arabic_count > 10:
        return "ar"
    elif english_count > french_count and english_count > 3:
        return "en"
    elif french_count > english_count and french_count > 3:
        return "fr"
    elif french_count > 3:
        return "fr"
    else:
        return "unknown"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 rebuild_contacts.py config.json")
        sys.exit(1)

    config_path = sys.argv[1]
    config_dir = os.path.dirname(os.path.abspath(config_path))

    with open(config_path) as f:
        config = json.load(f)

    contacts_dir = os.path.abspath(os.path.join(config_dir, config.get("contacts_dir", "../contacts")))
    messages_dir = os.path.join(contacts_dir, "messages")

    if not os.path.exists(messages_dir):
        print("❌ No messages directory found. Run fetch_sent.py first.")
        sys.exit(1)

    # Load existing index to preserve categories
    index_path = os.path.join(contacts_dir, "index.json")
    existing_index = {}
    if os.path.exists(index_path):
        with open(index_path) as f:
            existing_index = json.load(f)

    # Scan all message files
    contacts_data = {}
    for filepath in sorted(Path(messages_dir).glob("*.json")):
        with open(filepath, encoding='utf-8') as f:
            contact = json.load(f)

        email = contact.get('email', '')
        if not email:
            continue

        # Detect language from messages
        messages = contact.get('messages', [])
        if messages:
            # Use the most recent messages for language detection
            recent_bodies = [m.get('body', '') for m in messages[:5] if m.get('body')]
            if recent_bodies:
                combined = ' '.join(recent_bodies)
                detected = detect_language(combined)
                contact['language'] = detected
            else:
                contact['language'] = 'unknown'

        # Preserve existing category if known
        if email in existing_index and existing_index[email].get('category', 'unknown') != 'unknown':
            contact['category'] = existing_index[email]['category']
        else:
            contact['category'] = contact.get('category', 'unknown')

        contacts_data[email] = contact

    # Rebuild index
    index = {}
    for email, contact in contacts_data.items():
        msgs = contact.get('messages', [])
        index[email] = {
            'name': contact.get('name'),
            'category': contact.get('category', 'unknown'),
            'language': contact.get('language', 'unknown'),
            'message_count': len(msgs),
            'file': os.path.basename(filepath) if 'filepath' in dir() else f"{email.replace('@', '_at_').replace('.', '_dot_')}.json"
        }

    # Fix file paths in index
    for email in contacts_data:
        safe = email.replace('@', '_at_').replace('.', '_dot_')
        idx_entry = index.get(email, {})
        idx_entry['file'] = f"{safe}.json"

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"✅ Rebuilt index: {len(index)} contacts")

    # Show language breakdown
    lang_counts = {}
    cat_counts = {}
    for info in index.values():
        lang = info.get('language', 'unknown')
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        cat = info.get('category', 'unknown')
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    print(f"\n📊 Languages:")
    for lang, count in sorted(lang_counts.items()):
        print(f"   {lang}: {count} contacts")

    print(f"\n📊 Categories:")
    for cat, count in sorted(cat_counts.items()):
        print(f"   {cat}: {count} contacts")


if __name__ == "__main__":
    main()
