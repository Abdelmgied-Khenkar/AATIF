"""
Download MultiJail Arabic subset from HuggingFace
===================================================
MultiJail: 315 English prompts × 10 languages (including Arabic)
Source: ICLR 2024 — "Multilingual Jailbreak Challenges in Large Language Models"

Usage:
    pip install datasets
    python benchmarks/download_multijail_arabic.py
"""

import json
import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent


def download_from_huggingface():
    """Download MultiJail dataset from HuggingFace."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("Install datasets first: pip install datasets --break-system-packages")
        return None

    print("Downloading MultiJail from HuggingFace...")
    ds = load_dataset("DAMO-NLP-SG/MultiJail", split="train")
    print(f"Total samples: {len(ds)}")

    # Extract Arabic subset
    arabic_prompts = []
    english_prompts = []
    for row in ds:
        if row.get("language") == "ar" or row.get("lang") == "ar":
            arabic_prompts.append({
                "text": row.get("prompt", row.get("text", "")),
                "language": "ar",
                "original_english": row.get("english", row.get("original", "")),
                "category": row.get("category", "unknown"),
            })
        elif row.get("language") == "en" or row.get("lang") == "en":
            english_prompts.append({
                "text": row.get("prompt", row.get("text", "")),
                "language": "en",
                "category": row.get("category", "unknown"),
            })

    print(f"Arabic prompts: {len(arabic_prompts)}")
    print(f"English prompts: {len(english_prompts)}")

    return arabic_prompts, english_prompts


def download_from_github():
    """Fallback: download from GitHub repo."""
    import urllib.request

    base_url = "https://raw.githubusercontent.com/DAMO-NLP-SG/multilingual-safety-for-LLMs/main/data"
    print("Trying GitHub download...")

    # The repo structure may vary — try common paths
    for path in [
        "MultiJail/ar.jsonl",
        "multijail/ar.jsonl",
        "data/ar.jsonl",
        "ar.jsonl",
    ]:
        url = f"{base_url}/{path}"
        try:
            print(f"  Trying {url}...")
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=10)
            data = resp.read().decode("utf-8")
            prompts = [json.loads(line) for line in data.strip().split("\n") if line.strip()]
            print(f"  Found {len(prompts)} Arabic prompts")
            return prompts, []
        except Exception:
            continue

    print("  Could not find Arabic data on GitHub. Use HuggingFace method instead.")
    return None, None


def main():
    arabic, english = None, None

    try:
        arabic, english = download_from_huggingface()
    except Exception as e:
        print(f"HuggingFace download failed: {e}")

    if arabic is None:
        arabic, english = download_from_github()

    if arabic is None:
        print("\nCould not download MultiJail. Please install 'datasets' package:")
        print("  pip install datasets --break-system-packages")
        print("Then re-run this script.")
        return

    # Save Arabic subset
    out_path = OUTPUT_DIR / "multijail_arabic.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(arabic, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(arabic)} Arabic prompts to: {out_path}")

    # Save English for comparison
    if english:
        en_path = OUTPUT_DIR / "multijail_english.json"
        with open(en_path, "w", encoding="utf-8") as f:
            json.dump(english, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(english)} English prompts to: {en_path}")

    # Print sample
    print("\nSample Arabic prompts:")
    for p in arabic[:5]:
        print(f"  - {p['text'][:80]}...")


if __name__ == "__main__":
    main()
