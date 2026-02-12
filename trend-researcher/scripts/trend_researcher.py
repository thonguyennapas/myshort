#!/usr/bin/env python3
"""
🔍 Agent 1: Trend Researcher
Chuyên gia phân tích xu hướng YouTube Kids (2-8 tuổi).

Tìm kiếm và phân tích:
- Xu hướng âm nhạc/vũ điệu đang viral
- Chủ đề giáo dục thịnh hành
- Từ khóa có lượt tìm kiếm cao

Usage:
    python3 trend_researcher.py                          # Tìm mặc định 10 xu hướng
    python3 trend_researcher.py --max 5 --age-range 2-5  # Lọc theo độ tuổi
    python3 trend_researcher.py --category music         # Lọc theo loại
    python3 trend_researcher.py --dry-run                # Test không lưu file
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add shared/ dir to path (myshort/shared/)
MYSHORT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MYSHORT_ROOT / "shared"))
from utils import (
    setup_logging, get_config, ensure_output_dirs, save_json,
    load_safety_keywords, print_header, print_step, print_success,
    print_warning, print_error, safe_filename, get_output_dir,
    send_telegram
)

logger = setup_logging("TrendResearcher")

# ── Search Queries ──
TREND_QUERIES = {
    "music_dance": [
        "YouTube Kids trending songs {year}",
        "viral nursery rhymes kids {year}",
        "children dance songs popular {year}",
        "cocomelon style songs trending",
        "baby shark style viral kids songs",
        "kids pop music dance videos trending",
    ],
    "education": [
        "learning videos for toddlers trending {year}",
        "educational kids YouTube viral {year}",
        "counting colors shapes kids popular videos",
        "alphabet songs trending kids {year}",
        "STEM kids videos popular {year}",
    ],
    "characters": [
        "popular kids cartoon characters {year}",
        "animated kids shows trending YouTube",
        "cute animal characters kids videos viral",
    ],
    "general": [
        "YouTube Kids most viewed this week",
        "kids content trends {year} analysis",
        "children video viral formula {year}",
    ]
}

def run_search(query, max_results=5, search_type="text"):
    """Tìm kiếm trực tiếp qua Tavily API (self-contained, không phụ thuộc search.py)."""
    config = get_config()
    api_key = config.get("tavily_api_key", "")

    if not api_key:
        logger.warning("TAVILY_API_KEY chưa set — bỏ qua query: " + query)
        return []

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
    }

    if search_type == "news":
        payload["topic"] = "news"

    try:
        import requests
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
            })
        return results

    except Exception as e:
        logger.warning(f"Tavily search failed for '{query[:40]}': {e}")
        return []

def analyze_trends(search_results, category, age_range):
    """Phân tích kết quả tìm kiếm thành xu hướng cấu trúc."""
    trends = []
    safety = load_safety_keywords()
    blocked = [kw.lower() for kw in safety.get("blocked_keywords", [])]
    
    for result in search_results:
        if isinstance(result, dict):
            title = result.get("title", result.get("raw", ""))
            url = result.get("url", result.get("href", ""))
            snippet = result.get("snippet", result.get("body", ""))
        else:
            title = str(result)
            url = ""
            snippet = ""
        
        # Safety check
        content_lower = f"{title} {snippet}".lower()
        if any(kw in content_lower for kw in blocked):
            logger.debug(f"Blocked unsafe content: {title[:50]}")
            continue
        
        trend = {
            "name": title[:100] if title else "Unknown Trend",
            "category": category,
            "target_age": age_range,
            "url": url,
            "snippet": snippet[:200] if snippet else "",
            "keywords": extract_keywords(title, snippet),
            "relevance": calculate_relevance(title, snippet, category),
        }
        trends.append(trend)
    
    # Sort by relevance
    trends.sort(key=lambda t: t["relevance"], reverse=True)
    return trends

def extract_keywords(title, snippet):
    """Trích xuất từ khóa chính từ title và snippet."""
    import re
    text = f"{title} {snippet}".lower()
    # Từ khóa phổ biến trong lĩnh vực kids content
    kids_keywords = [
        "nursery rhyme", "kids song", "children", "toddler", "baby",
        "dance", "sing", "learn", "count", "color", "shape", "alphabet",
        "cartoon", "animation", "cocomelon", "pinkfong", "baby shark",
        "educational", "fun", "play", "game", "story", "fairy tale",
        "animal", "dinosaur", "vehicle", "truck", "train",
        "rainbow", "music", "lullaby", "bedtime"
    ]
    
    found = [kw for kw in kids_keywords if kw in text]
    return found[:5]  # Top 5 keywords

def calculate_relevance(title, snippet, category):
    """Tính điểm relevance (0-100) dựa trên nội dung."""
    score = 50  # Base score
    text = f"{title} {snippet}".lower()
    
    # Boost for viral indicators
    viral_words = ["viral", "trending", "popular", "million views", "top", "best", "hit"]
    for word in viral_words:
        if word in text:
            score += 10
    
    # Boost for kids-specific content
    kids_words = ["kids", "children", "toddler", "baby", "nursery", "learn"]
    for word in kids_words:
        if word in text:
            score += 5
    
    # Boost for category match
    if category.replace("_", " ") in text:
        score += 10
    
    return min(score, 100)

def research_trends(categories=None, max_per_category=5, age_range="2-8", dry_run=False):
    """Quy trình chính: nghiên cứu xu hướng."""
    year = datetime.now().year
    
    if categories is None:
        categories = list(TREND_QUERIES.keys())
    
    all_trends = []
    total_queries = sum(len(TREND_QUERIES.get(cat, [])) for cat in categories)
    query_count = 0
    
    print_header("Agent 1: Trend Researcher", "🔍")
    print(f"  📅 Ngày: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  👶 Độ tuổi: {age_range}")
    print(f"  📂 Categories: {', '.join(categories)}")
    print(f"  🔎 Tổng queries: {total_queries}\n")
    
    for category in categories:
        queries = TREND_QUERIES.get(category, [])
        print(f"\n  📁 Category: {category}")
        
        category_trends = []
        for query_template in queries:
            query = query_template.format(year=year)
            query_count += 1
            print_step(query_count, total_queries, f"Searching: {query[:60]}...")
            
            if dry_run:
                # Fake results for dry-run
                category_trends.append({
                    "name": f"[DRY-RUN] Sample trend for: {query[:40]}",
                    "category": category,
                    "target_age": age_range,
                    "url": "https://example.com",
                    "snippet": "This is a dry-run sample result",
                    "keywords": ["sample", "dry-run"],
                    "relevance": 70,
                })
                continue
            
            results = run_search(query, max_results=max_per_category)
            trends = analyze_trends(results, category, age_range)
            category_trends.extend(trends)
        
        # Deduplicate and take top N
        seen = set()
        unique = []
        for t in category_trends:
            key = t["name"][:50].lower()
            if key not in seen:
                seen.add(key)
                unique.append(t)
        
        all_trends.extend(unique[:max_per_category])
        print_success(f"  Tìm được {len(unique)} xu hướng trong {category}")
    
    # Pick recommended topic
    recommended = None
    if all_trends:
        all_trends.sort(key=lambda t: t["relevance"], reverse=True)
        recommended = all_trends[0]
    
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "age_range": age_range,
        "categories": categories,
        "total_trends": len(all_trends),
        "trends": all_trends,
        "recommended_topic": recommended,
    }

def main():
    parser = argparse.ArgumentParser(
        description="🔍 Agent 1: Trend Researcher — Tìm xu hướng YouTube Kids"
    )
    parser.add_argument("--max", type=int, default=5,
                       help="Số xu hướng tối đa mỗi category (mặc định: 5)")
    parser.add_argument("--age-range", default="2-8",
                       help="Độ tuổi mục tiêu (mặc định: 2-8)")
    parser.add_argument("--category", choices=["music_dance", "education", "characters", "general"],
                       help="Lọc 1 category cụ thể")
    parser.add_argument("--dry-run", action="store_true",
                       help="Test workflow không gọi search thật")
    parser.add_argument("--output", help="Đường dẫn file output (mặc định: auto)")
    parser.add_argument("--json", action="store_true",
                       help="In kết quả ra stdout dạng JSON")
    args = parser.parse_args()
    
    categories = [args.category] if args.category else None
    
    # Run research
    result = research_trends(
        categories=categories,
        max_per_category=args.max,
        age_range=args.age_range,
        dry_run=args.dry_run,
    )
    
    # Output
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    # Save to file
    output_dir = ensure_output_dirs()
    output_path = args.output or str(
        output_dir / "trends" / f"trend-{datetime.now().strftime('%Y%m%d')}.json"
    )
    save_json(result, output_path)
    
    # Summary
    print(f"\n{'━' * 50}")
    print(f"📊 KẾT QUẢ: {result['total_trends']} xu hướng tìm được")
    print(f"📁 File: {output_path}")
    
    if result["recommended_topic"]:
        rec = result["recommended_topic"]
        print(f"\n🏆 TOP RECOMMENDATION:")
        print(f"   Tên: {rec['name'][:80]}")
        print(f"   Category: {rec['category']}")
        print(f"   Keywords: {', '.join(rec.get('keywords', []))}")
        print(f"   Relevance: {rec['relevance']}/100")
    
    print(f"{'━' * 50}\n")
    
    # ── Telegram Notification ──
    msg_lines = ["🔍 *Agent 1: Trend Researcher*", ""]
    msg_lines.append(f"📅 Ngày: {result.get('date', 'N/A')}")
    msg_lines.append(f"📊 Tìm được: {result['total_trends']} xu hướng\n")
    
    for i, t in enumerate(result.get('trends', [])[:8]):
        name = t.get('name', '?')[:60]
        cat = t.get('category', '?')
        score = t.get('relevance', 0)
        kwords = ', '.join(t.get('keywords', [])[:5])
        msg_lines.append(f"{i+1}. [{cat}] *{name}*")
        msg_lines.append(f"   Score: {score} | {kwords}")
    
    if result.get('recommended_topic'):
        rec = result['recommended_topic']
        msg_lines.append(f"\n🏆 *GỢI Ý:* {rec.get('name', '?')[:80]}")
        msg_lines.append(f"Keywords: {', '.join(rec.get('keywords', []))}")
    
    if not result.get('trends'):
        msg_lines.append("⚠️ Không tìm được xu hướng nào.")
    
    send_telegram("\n".join(msg_lines))
    print_success("Đã gửi kết quả qua Telegram")

if __name__ == "__main__":
    main()
