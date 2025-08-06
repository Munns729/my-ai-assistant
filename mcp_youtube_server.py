"""
MCP Server for YouTube Transcript Access
Provides robust YouTube transcript fetching with multiple fallback methods
"""

import asyncio
import re
import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs

from mcp import Server, Tool
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)
from playwright.async_api import async_playwright
import aiohttp

logger = logging.getLogger(__name__)


class YouTubeTranscriptError(Exception):
    """Custom exception for YouTube transcript access errors"""
    pass


class YouTubeMCPServer:
    """MCP Server for YouTube transcript access with multiple fallback methods"""
    
    def __init__(self, name: str = "youtube-transcript-server"):
        self.server = Server(name)
        self.setup_tools()
        
    def extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from various URL formats"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/v\/([^&\n?#]+)',
            r'youtube\.com\/shorts\/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If it's already a video ID
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
            
        raise YouTubeTranscriptError(f"Could not extract video ID from URL: {url}")
    
    def setup_tools(self):
        """Setup MCP tools for YouTube transcript access"""
        
        @self.server.tool()
        async def fetch_youtube_transcript(video_url: str, language: str = "en") -> Dict[str, Any]:
            """
            Fetch transcript from YouTube video using multiple methods
            
            Args:
                video_url: YouTube video URL or video ID
                language: Preferred language code (default: "en")
                
            Returns:
                Dict containing transcript data, metadata, and method used
            """
            try:
                video_id = self.extract_video_id(video_url)
                
                # Method 1: Try youtube-transcript-api first
                try:
                    transcript_data = await self._fetch_via_api(video_id, language)
                    transcript_data["method"] = "youtube_transcript_api"
                    transcript_data["video_id"] = video_id
                    return transcript_data
                    
                except Exception as api_error:
                    logger.warning(f"API method failed for {video_id}: {api_error}")
                    
                    # Method 2: Playwright fallback
                    try:
                        playwright_data = await self._fetch_via_playwright(video_url, language)
                        playwright_data["method"] = "playwright"
                        playwright_data["video_id"] = video_id
                        return playwright_data
                        
                    except Exception as playwright_error:
                        logger.error(f"Playwright method failed for {video_id}: {playwright_error}")
                        
                        # Method 3: Manual extraction fallback
                        manual_data = await self._fetch_manual_extraction(video_url)
                        manual_data["method"] = "manual_extraction"
                        manual_data["video_id"] = video_id
                        return manual_data
                        
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "video_url": video_url,
                    "method": "failed_all_methods"
                }
        
        @self.server.tool()
        async def get_video_metadata(video_url: str) -> Dict[str, Any]:
            """
            Extract comprehensive video metadata including title, description, duration
            
            Args:
                video_url: YouTube video URL or video ID
                
            Returns:
                Dict containing video metadata
            """
            try:
                video_id = self.extract_video_id(video_url)
                
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    
                    try:
                        await page.goto(f"https://www.youtube.com/watch?v={video_id}", 
                                      wait_until="domcontentloaded", timeout=30000)
                        
                        # Wait for page to load
                        await page.wait_for_selector('h1.ytd-watch-metadata', timeout=10000)
                        
                        # Extract metadata
                        title = await page.locator('h1.ytd-watch-metadata').inner_text()
                        
                        # Channel name
                        channel = ""
                        try:
                            channel = await page.locator('ytd-channel-name a').inner_text()
                        except:
                            pass
                        
                        # Description
                        description = ""
                        try:
                            description = await page.locator('#description-text').inner_text()
                        except:
                            pass
                        
                        # Duration
                        duration = ""
                        try:
                            duration = await page.locator('.ytp-time-duration').inner_text()
                        except:
                            pass
                        
                        # View count
                        views = ""
                        try:
                            views = await page.locator('#count .view-count').inner_text()
                        except:
                            pass
                        
                        return {
                            "success": True,
                            "video_id": video_id,
                            "title": title,
                            "channel": channel,
                            "description": description,
                            "duration": duration,
                            "views": views,
                            "url": video_url
                        }
                        
                    finally:
                        await browser.close()
                        
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "video_url": video_url
                }
        
        @self.server.tool()
        async def check_transcript_availability(video_url: str) -> Dict[str, Any]:
            """
            Check if transcripts are available for a video and list available languages
            
            Args:
                video_url: YouTube video URL or video ID
                
            Returns:
                Dict containing availability status and available languages
            """
            try:
                video_id = self.extract_video_id(video_url)
                
                try:
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    available_languages = []
                    
                    for transcript in transcript_list:
                        available_languages.append({
                            "language": transcript.language,
                            "language_code": transcript.language_code,
                            "is_generated": transcript.is_generated,
                            "is_translatable": transcript.is_translatable
                        })
                    
                    return {
                        "success": True,
                        "video_id": video_id,
                        "transcripts_available": True,
                        "available_languages": available_languages,
                        "total_languages": len(available_languages)
                    }
                    
                except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
                    return {
                        "success": True,
                        "video_id": video_id,
                        "transcripts_available": False,
                        "error": str(e),
                        "available_languages": []
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "video_url": video_url
                }
    
    async def _fetch_via_api(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """Fetch transcript using youtube-transcript-api"""
        try:
            # Try to get transcript in requested language
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
            
            # Format transcript text
            full_text = " ".join([entry['text'] for entry in transcript])
            
            return {
                "success": True,
                "transcript": transcript,
                "full_text": full_text,
                "language": language,
                "total_segments": len(transcript),
                "duration": transcript[-1]['start'] + transcript[-1]['duration'] if transcript else 0
            }
            
        except Exception as e:
            # Try English if requested language fails
            if language != "en":
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
                full_text = " ".join([entry['text'] for entry in transcript])
                
                return {
                    "success": True,
                    "transcript": transcript,
                    "full_text": full_text,
                    "language": "en",
                    "total_segments": len(transcript),
                    "duration": transcript[-1]['start'] + transcript[-1]['duration'] if transcript else 0,
                    "fallback_language": True
                }
            else:
                raise e
    
    async def _fetch_via_playwright(self, video_url: str, language: str = "en") -> Dict[str, Any]:
        """Fetch transcript using Playwright as fallback"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait for video to load
                await page.wait_for_selector('#movie_player', timeout=15000)
                
                # Look for transcript button
                transcript_button = None
                
                # Try different selectors for transcript button
                selectors = [
                    'button[aria-label*="transcript"]',
                    'button[aria-label*="Show transcript"]',
                    '[aria-label*="Open transcript"]',
                    'ytd-transcript-section-renderer'
                ]
                
                for selector in selectors:
                    try:
                        transcript_button = page.locator(selector).first
                        if await transcript_button.count() > 0:
                            break
                    except:
                        continue
                
                if not transcript_button or await transcript_button.count() == 0:
                    raise YouTubeTranscriptError("No transcript button found")
                
                # Click transcript button
                await transcript_button.click()
                await page.wait_for_timeout(2000)
                
                # Wait for transcript to load
                await page.wait_for_selector('ytd-transcript-segment-renderer', timeout=10000)
                
                # Extract transcript segments
                segments = []
                transcript_elements = page.locator('ytd-transcript-segment-renderer')
                
                count = await transcript_elements.count()
                for i in range(count):
                    element = transcript_elements.nth(i)
                    
                    try:
                        # Get timestamp
                        timestamp_elem = element.locator('.ytd-transcript-segment-renderer[role="button"]')
                        timestamp = await timestamp_elem.get_attribute('aria-label') or ""
                        
                        # Get text
                        text_elem = element.locator('.segment-text')
                        text = await text_elem.inner_text()
                        
                        # Parse timestamp to seconds
                        start_time = self._parse_timestamp(timestamp)
                        
                        segments.append({
                            "text": text.strip(),
                            "start": start_time,
                            "duration": 0  # Playwright doesn't provide duration
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error extracting segment {i}: {e}")
                        continue
                
                if not segments:
                    raise YouTubeTranscriptError("No transcript segments found")
                
                full_text = " ".join([seg['text'] for seg in segments])
                
                return {
                    "success": True,
                    "transcript": segments,
                    "full_text": full_text,
                    "language": language,
                    "total_segments": len(segments),
                    "duration": segments[-1]['start'] if segments else 0
                }
                
            finally:
                await browser.close()
    
    async def _fetch_manual_extraction(self, video_url: str) -> Dict[str, Any]:
        """Manual extraction fallback method"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
                
                # Extract any available text content from the page
                # This is a last resort method
                
                # Get video title and description as fallback content
                title = ""
                description = ""
                
                try:
                    title = await page.locator('h1.ytd-watch-metadata').inner_text()
                except:
                    pass
                
                try:
                    description = await page.locator('#description-text').inner_text()
                except:
                    pass
                
                fallback_content = f"Title: {title}\n\nDescription: {description}"
                
                return {
                    "success": True,
                    "transcript": [{"text": fallback_content, "start": 0, "duration": 0}],
                    "full_text": fallback_content,
                    "language": "unknown",
                    "total_segments": 1,
                    "duration": 0,
                    "fallback_content": True,
                    "note": "This is fallback content from video title and description, not actual transcript"
                }
                
            finally:
                await browser.close()
    
    def _parse_timestamp(self, timestamp_str: str) -> float:
        """Parse timestamp string to seconds"""
        try:
            # Extract time pattern from aria-label
            time_match = re.search(r'(\d+):(\d+)', timestamp_str)
            if time_match:
                minutes, seconds = map(int, time_match.groups())
                return minutes * 60 + seconds
            return 0.0
        except:
            return 0.0
    
    def run(self, host: str = "localhost", port: int = 8000):
        """Run the MCP server"""
        logger.info(f"Starting YouTube MCP Server on {host}:{port}")
        self.server.run(host=host, port=port)


# Example usage and testing
async def test_mcp_server():
    """Test the MCP server functionality"""
    server = YouTubeMCPServer()
    
    # Test video URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll video
    
    print("Testing transcript fetch...")
    result = await server.server._tools["fetch_youtube_transcript"].func(test_url)
    print(json.dumps(result, indent=2))
    
    print("\nTesting metadata extraction...")
    metadata = await server.server._tools["get_video_metadata"].func(test_url)
    print(json.dumps(metadata, indent=2))
    
    print("\nTesting transcript availability...")
    availability = await server.server._tools["check_transcript_availability"].func(test_url)
    print(json.dumps(availability, indent=2))


if __name__ == "__main__":
    # Run the server
    server = YouTubeMCPServer()
    server.run()