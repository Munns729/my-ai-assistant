# insights.py - AI Analysis and Entity Extraction Logic
# This file uses OpenAI's API to extract structured insights and entities from user content

# === IMPORTS: Bring in external libraries and typing tools ===

import openai  # The OpenAI Python library to access GPT models
import json  # Built-in Python module for working with JSON data (structured data)
import re  # Regular expressions (not used yet, but often used for pattern matching)
import traceback  # For detailed error reporting
from typing import Dict, List, Any  # Type hints for clarity and better error checking

# === FUNCTION: Extract structured insights from raw content ===

def extract_insights_from_text(content: str, source_type: str = 'general') -> str:
    """
    Extract structured insights from text content using OpenAI

    Args:
        content (str): The raw input text to analyze (e.g., from YouTube, email, article)
        source_type (str): A label describing the source (used in the prompt)

    Returns:
        str: AI-generated structured insights or an error message
    """

    # Build the prompt to send to the AI model
    prompt = f"""
    You are analyzing {source_type} content as an AI implementation consultant AND investor focused on SME/MSP opportunities. Extract ONLY high-value, actionable insights with specific business metrics.

    **STRICT FILTERING CRITERIA - REJECT insights unless they include:**

    **For SME/MSP insights - AT LEAST ONE of:**
    - Specific cost figures ($X/month, $X implementation, $X savings)
    - ROI percentages or time-to-value metrics
    - Named tools/vendors with SME pricing tiers
    - Concrete implementation timelines (weeks/months)
    - Evidence of MSPs already offering these services
    - Client case studies with quantified results

    **For Tech Frontiers - AT LEAST ONE of:**
    - Performance benchmarks (X% improvement, X speedup)
    - Research paper citations or breakthrough claims
    - New capabilities that didn't exist 6 months ago
    - Technical specifications that enable new use cases
    - Evidence of commercial viability within 2-5 years

    **Content to Analyze:**
    {content[:3000]}

    **INSIGHT CATEGORIES (Extract 1-3 maximum per category):**

    1. ⚙️ **SME Implementation**: 
    - Focus: Specific tools, costs, implementation strategies
    - Reject: Vague "AI can help" statements without specifics

    2. 🔌 **MSP Transformation**: 
    - Focus: Named MSPs, service offerings, revenue data, client wins
    - Reject: Generic "MSPs should consider AI" advice

    3. 🚀 **SME-Ready Tools**: 
    - Focus: Named products, pricing tiers, specific features for <500 employees
    - Reject: Enterprise tools without clear SME pathway

    4. 💰 **Investment Signals**: 
    - Focus: Funding rounds, revenue growth %, specific company metrics
    - Reject: Market size predictions without concrete data

    5. 🌟 **Tech Frontiers**: 
    - Focus: Novel capabilities, breakthrough performance, new research
    - Reject: Incremental improvements or well-known techniques

    **ENHANCED OUTPUT FORMAT:**
    [Category Icon] **[Specific Company/Tool/Technique Name]: [Concrete Outcome]**  
    - **Business Impact**: [Quantified benefit - $X saved, Y% improvement, Z hours reduced]  
    - **Evidence**: "[SPECIFIC quote with numbers/names/metrics]"  
    - **Implementation**: [Concrete next steps with timeframe]  
    - **Investment Thesis**: [Why this matters for SME/MSP market - be specific]
    - **Confidence**: High/Med/Low

    **QUALITY EXAMPLES:**

    ✅ GOOD:
    [🚀 SME-Ready Tools] **Zapier Central: 40% Admin Time Reduction**  
    - Business Impact: SMEs save 15-20 hours/week on manual data entry tasks
    - Evidence: "Customer case study showed 40% reduction in administrative overhead"
    - Implementation: 2-week pilot with 3 core workflows, $99/month tier
    - Investment Thesis: Addresses #1 SME pain point (manual processes) with proven ROI
    - Confidence: High

    ❌ BAD (like your current output):
    [⚙️ SME Implementation] **Opportunities in Knowledge Graph Implementation for SMEs**  
    - Relevance: Potential for improved data retrieval and knowledge organization.  
    - Evidence: "Knowledge graphs are starting to be used as well..."  

    **STRICT REJECTION CRITERIA:**
    - No specific company/product names mentioned
    - No quantified benefits or costs
    - Generic statements about "potential" or "opportunities"
    - Evidence quotes under 10 words or purely definitional
    - Insights that could apply to any technology (not AI-specific)

    **If content doesn't meet these criteria, respond exactly:**
    "No actionable insights found. Content lacks specific metrics, named vendors, or quantified business outcomes required for SME/MSP analysis."

    Analyze the content and extract insights following these enhanced criteria.
    """
    try:
        # Create a client with explicit httpx configuration to avoid proxies issue
        import httpx
        client = openai.OpenAI(
            http_client=httpx.Client(
                timeout=httpx.Timeout(30.0),
                # Don't pass proxies parameter to avoid the error
            )
        )
        
        # Call OpenAI's ChatCompletion API with the formatted prompt
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # The specific GPT model to use
            messages=[
                {"role": "system", "content": "You are an expert analyst specializing in AI, technology, and business intelligence. Extract only the most valuable and actionable insights."},
                {"role": "user", "content": prompt}
            ],
                         max_tokens=800,  # Limit the response length
            temperature=0.3  # Low temperature = more factual and less creative output
        )

        # Get the AI's text response and remove leading/trailing whitespace
        return response.choices[0].message.content.strip()

    except Exception as e:
        # If anything goes wrong, return a detailed error message
        tb = traceback.format_exc()
        print(f"Full exception traceback in extract_insights_from_text:\n{tb}")
        return f"Error analyzing content: {str(e)}\n\nTraceback:\n{tb}"

# === FUNCTION: Extract named entities like companies or technologies from insights ===

def extract_entities_from_insights(insights: str) -> List[Dict[str, Any]]:
    """
    Extract companies, people, and technologies mentioned in insights

    Args:
        insights (str): The full block of structured insights from the AI

    Returns:
        List[Dict[str, Any]]: A list of extracted entities with type and confidence score
    """

    # Build the prompt asking GPT to extract named entities from the insights
    prompt = f"""
    Extract ONLY explicitly named entities from these insights. Focus on actionable business intelligence.

    **STRICT EXTRACTION RULES:**

    **ONLY Extract if EXPLICITLY NAMED in the insights:**
    - Company names with specific context (not just "companies are...")
    - Product names with version numbers or specific features
    - People with titles and company affiliations
    - Technologies with specific implementations (not generic terms)
    - Research institutions with specific projects/papers

    **Entity Types - REQUIRE SPECIFIC NAMES:**

    1. 🏢 **Companies**: 
    - ✅ Extract: "Zapier", "Microsoft Copilot", "OpenAI GPT-4"
    - ❌ Skip: "AI companies", "major tech firms", "startups"

    2. 👥 **People**:
    - ✅ Extract: "John Smith, CTO of TechCorp"
    - ❌ Skip: "executives", "researchers", "industry leaders"

    3. ⚙️ **Technologies/Products**:
    - ✅ Extract: "Claude 3.5", "GPT-4 Turbo", "Anthropic Constitutional AI"
    - ❌ Skip: "large language models", "AI tools", "machine learning"

    4. 📚 **Research/Institutions**:
    - ✅ Extract: "Stanford HAI", "DeepMind", "MIT CSAIL"
    - ❌ Skip: "research shows", "studies indicate"

    **Enhanced Confidence Scoring:**
    - **0.95-1.0**: Named + quantified context (pricing, metrics, timelines)
    - **0.8-0.9**: Named + business context (use case, industry)
    - **0.6-0.7**: Named + minimal context
    - **<0.6**: Don't include (too vague)

    **SME Relevance Scoring:**
    - **true**: <$10k annual cost, <500 employee focus, MSP-deliverable
    - **false**: Enterprise-only, >$50k cost, requires specialized teams

    **OUTPUT FORMAT (JSON only):**
    [
    {{
        "name": "EXACT NAME from text",
        "type": "company/person/technology/institution/product",
        "subtype": "specific category like AI vendor, no-code platform",
        "confidence": 0.6-1.0,
        "sme_relevance": true/false,
        "context": "Brief context from insights - what makes this relevant"
    }}
    ]

    **QUALITY CONTROL:**
    - If no specific entities are named in insights, return: []
    - Deduplicate entities (keep highest confidence version)
    - Normalize names (e.g., "OpenAI's GPT-4" → "GPT-4")
    - Include parent company context where relevant

    **Insights to analyze:**
    {insights}

    Extract entities following these strict criteria. Return empty array [] if no specifically named entities found.
    """

    try:
        # Create a client with explicit httpx configuration to avoid proxies issue
        import httpx
        client = openai.OpenAI(
            http_client=httpx.Client(
                timeout=httpx.Timeout(30.0),
                # Don't pass proxies parameter to avoid the error
            )
        )
        
        # Send the prompt to OpenAI's GPT model to extract structured entity data
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
                         max_tokens=400,  # Keep response short and structured
            temperature=0.1  # Very low temperature for reliable, factual output
        )

        # The response is expected to be a JSON string - try to parse it
        entities_json = response.choices[0].message.content.strip()
        return json.loads(entities_json)  # Convert JSON string to Python list of dictionaries

    except Exception as e:
        # If parsing fails or something goes wrong, print detailed error and return empty list
        tb = traceback.format_exc()
        print(f"Full exception traceback in extract_entities_from_insights:\n{tb}")
        return []

# === FUNCTION: Placeholder to get YouTube video info ===

def get_video_info(video_url: str) -> Dict[str, Any]:
    """
    Extract video information from a YouTube URL

    Args:
        video_url (str): The URL of the video (not currently used)

    Returns:
        Dict[str, Any]: Placeholder dictionary with fake/default data

    Note:
        This is currently a placeholder and does not use the actual YouTube API.
        You can later implement this using the YouTube Data API if needed.
    """

    # Returning default placeholder info for now
    return {
        'title': 'Manual Entry',  # Default title
        'description': '',  # Empty description
        'duration': '0:00',  # Default duration
        'channel': 'Unknown'  # Placeholder channel name
    }