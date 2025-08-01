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
    Analyze this {source_type} content as both an AI implementation consultant AND investor, prioritizing SME/MSP insights while capturing significant emerging technologies. Extract:

    **Core Focus** (Strict SME/MSP relevance):
    1. Opportunities to implement AI solutions for SMEs (<500 employees)
    2. Signals of traditional MSPs transitioning to AI service providers
    3. Emerging AI tools/services with SME product-market fit

    **Strategic Horizon Scanning** (**Looser criteria**):
    4. 🌟 **Emerging Tech Breakthroughs**: Novel capabilities, research frontiers, or disruptive technologies with future SME/MSP potential

    **Content Excerpt**:
    {content[:3000]}

    **Priority Insight Categories**:
    1. ⚙️ **SME Implementation**: Frameworks, cost barriers, ROI cases specific to small businesses
    2. 🔌 **MSP Transformation**: Upskilling initiatives, AI service launches, acquisitions
    3. 🚀 **SME-Ready Tools**: Vertical SaaS, no-code platforms under $5k/year
    4. 💰 **Investment Signals**: 
    - MSPs with >30% AI revenue growth 
    - Startups solving SME pain points
    5. 🌟 **Tech Frontiers**: (NEW)
    - Fundamental model advances
    - Novel architectures/techniques
    - Emerging capabilities with 2-5 yr horizon
    - Paradigm shifts in AI development

    **For each insight**:
    → **Headline**: Max 8 words 
    → **Relevance**: 
    - For SME/MSP: [Specific business impact]
    - For Tech Frontiers: [Why this matters for AI's future]
    → **Evidence**: Key metric/quote
    → **Action**: [Implementation/Investment/Research/Monitor]
    → **Confidence**: High/Med/Low

    **Filtering Rules**:
    - ✅ **SME/MSP Insights**: MUST include:
    • SME cost savings >20% OR 
    • MSP service expansion evidence OR 
    • Investment-grade metrics
    - ✅ **Tech Frontiers**: MUST be:
    • Fundamentally novel (not incremental)
    • Demonstrate 10x+ capability improvement
    • Show research/industry validation
    - 🚫 Exclude enterprise-only solutions without SME pathway

    **Output Format**:
    [Category Icon] **Headline**  
    • Relevance: [Concise justification]  
    • Evidence: "[excerpt]"  
    • Action: [Primary action]  
    • Confidence: High/Med/Low  

    If no insights meet criteria: "No actionable insights found."
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
    Extract entities from these insights with priority given to SME/AI-relevant entities. Follow these rules:

    **Entity Types to Extract**:
    1. 🏢 **Companies**: 
    - AI tool vendors (especially SME-focused)
    - MSPs/MSSPs with AI services
    - Startups with under $20M funding
    2. 👥 **People**:
    - CTOs/Founders of SME AI companies
    - Key researchers behind emerging tech
    - MSP transformation leaders
    3. ⚙️ **Technologies**:
    - SME-implementable tools (no-code, <$10k)
    - Emerging architectures (e.g., MoE, SSMs)
    - AI capabilities with consulting relevance
    4. 📚 **Research Institutions** (NEW):
    - Labs publishing breakthrough papers
    - University tech transfer programs
    5. 📈 **Products/Services** (NEW):
    - Commercial AI products mentioned
    - MSP service offerings

    **Special Handling**:
    - **Boost confidence** for:
    • Companies with "SME", "SMB", or "mid-market" in context
    • Technologies under $10k/year licensing
    • MSPs offering AI migration
    - **Suppress**:
    • Enterprise-only solution providers
    • Generic executive titles without name (e.g., "a Google VP")
    • Overly broad technologies ("AI", "machine learning")

    **Output Rules**:
    - Use normalized names (e.g., "GPT-4" not "new GPT model")
    - **Confidence scoring**:
    • 0.9-1.0: Explicitly named + SME/MSP context
    • 0.7-0.8: Explicitly named + no context
    • 0.5-0.6: Implied but unambiguous
    - Deduplicate entities (keep highest confidence)
    - Include parent companies for products (e.g., "Gemini (Google)")

    **JSON Format**:
    [
    {{
        "name": "OpenAI",
        "type": "company",
        "subtype": "AI vendor",  # NEW FIELD
        "confidence": 0.95,
        "sme_relevance": true  # NEW FIELD
    }},
    {{
        "name": "Retrieval-Augmented Generation",
        "type": "technology",
        "subtype": "NLP technique",
        "confidence": 0.85,
        "sme_relevance": false
    }}
    ]

    Insights:
    {insights}
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