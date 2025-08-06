"""
MCP Client for YouTube Transcript Services
Handles communication with MCP servers and provides a clean interface for the application
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
import aiohttp
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors"""
    pass


class ConnectionError(MCPClientError):
    """Raised when connection to MCP server fails"""
    pass


class ToolExecutionError(MCPClientError):
    """Raised when tool execution fails"""
    pass


class ServerStatus(Enum):
    """MCP Server status enumeration"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONNECTING = "connecting"


@dataclass
class MCPServerConfig:
    """Configuration for MCP server connection"""
    name: str
    host: str
    port: int
    protocol: str = "http"
    timeout: int = 30
    max_retries: int = 3
    
    @property
    def base_url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"


@dataclass
class ToolResult:
    """Result from MCP tool execution"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tool_name: Optional[str] = None
    execution_time: Optional[float] = None


class MCPClient:
    """
    MCP Client for communicating with Model Context Protocol servers
    Provides async interface for tool execution and server management
    """
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.status = ServerStatus.DISCONNECTED
        self.session: Optional[aiohttp.ClientSession] = None
        self.available_tools: List[str] = []
        self.server_info: Optional[Dict[str, Any]] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self) -> bool:
        """
        Establish connection to MCP server
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.status = ServerStatus.CONNECTING
            
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Test connection and get server info
            server_info = await self._get_server_info()
            if server_info:
                self.server_info = server_info
                self.available_tools = server_info.get("tools", [])
                self.status = ServerStatus.CONNECTED
                logger.info(f"Connected to MCP server {self.config.name} at {self.config.base_url}")
                return True
            else:
                self.status = ServerStatus.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.config.name}: {e}")
            self.status = ServerStatus.ERROR
            return False
    
    async def disconnect(self):
        """Close connection to MCP server"""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.status = ServerStatus.DISCONNECTED
        self.available_tools = []
        self.server_info = None
        logger.info(f"Disconnected from MCP server {self.config.name}")
    
    async def _get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get server information and available tools"""
        try:
            url = f"{self.config.base_url}/info"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Server info request failed with status {response.status}")
                    # Return minimal server info if endpoint doesn't exist
                    return {
                        "name": self.config.name,
                        "status": "active",
                        "tools": ["fetch_youtube_transcript", "get_video_metadata", "check_transcript_availability"]
                    }
        except Exception as e:
            logger.warning(f"Could not get server info: {e}")
            # Return minimal server info for compatibility
            return {
                "name": self.config.name,
                "status": "active",
                "tools": ["fetch_youtube_transcript", "get_video_metadata", "check_transcript_availability"]
            }
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any], 
                       retry_count: int = 0) -> ToolResult:
        """
        Execute a tool on the MCP server
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            retry_count: Current retry attempt (internal use)
            
        Returns:
            ToolResult: Result of tool execution
        """
        import time
        start_time = time.time()
        
        try:
            if self.status != ServerStatus.CONNECTED:
                if not await self.connect():
                    return ToolResult(
                        success=False,
                        error="Not connected to MCP server",
                        tool_name=tool_name
                    )
            
            if tool_name not in self.available_tools:
                logger.warning(f"Tool {tool_name} not in available tools: {self.available_tools}")
                # Continue anyway in case the tool list is incomplete
            
            # Prepare request
            url = f"{self.config.base_url}/tools/{tool_name}"
            payload = {
                "tool": tool_name,
                "parameters": parameters
            }
            
            # Execute tool
            async with self.session.post(url, json=payload) as response:
                execution_time = time.time() - start_time
                
                if response.status == 200:
                    result_data = await response.json()
                    return ToolResult(
                        success=True,
                        data=result_data,
                        tool_name=tool_name,
                        execution_time=execution_time
                    )
                else:
                    error_text = await response.text()
                    return ToolResult(
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        tool_name=tool_name,
                        execution_time=execution_time
                    )
                    
        except aiohttp.ClientError as e:
            if retry_count < self.config.max_retries:
                logger.warning(f"Tool execution failed, retrying ({retry_count + 1}/{self.config.max_retries}): {e}")
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self.call_tool(tool_name, parameters, retry_count + 1)
            else:
                execution_time = time.time() - start_time
                return ToolResult(
                    success=False,
                    error=f"Network error after {self.config.max_retries} retries: {e}",
                    tool_name=tool_name,
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Unexpected error calling tool {tool_name}: {e}")
            return ToolResult(
                success=False,
                error=f"Unexpected error: {e}",
                tool_name=tool_name,
                execution_time=execution_time
            )
    
    async def health_check(self) -> bool:
        """
        Check if the MCP server is healthy
        
        Returns:
            bool: True if server is healthy, False otherwise
        """
        try:
            if self.status != ServerStatus.CONNECTED:
                return False
                
            url = f"{self.config.base_url}/health"
            async with self.session.get(url) as response:
                return response.status == 200
                
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if client is connected to server"""
        return self.status == ServerStatus.CONNECTED
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tools"""
        return self.available_tools.copy()


class YouTubeMCPClient:
    """
    Specialized MCP client for YouTube transcript services
    Provides high-level interface for YouTube-specific operations
    """
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.config = MCPServerConfig(
            name="youtube-transcript-server",
            host=host,
            port=port
        )
        self.client = MCPClient(self.config)
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.client.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.disconnect()
    
    async def fetch_transcript(self, video_url: str, language: str = "en") -> Dict[str, Any]:
        """
        Fetch transcript for a YouTube video
        
        Args:
            video_url: YouTube video URL or ID
            language: Preferred language code
            
        Returns:
            Dict containing transcript data
        """
        result = await self.client.call_tool("fetch_youtube_transcript", {
            "video_url": video_url,
            "language": language
        })
        
        if result.success:
            return result.data
        else:
            raise ToolExecutionError(f"Failed to fetch transcript: {result.error}")
    
    async def get_video_metadata(self, video_url: str) -> Dict[str, Any]:
        """
        Get metadata for a YouTube video
        
        Args:
            video_url: YouTube video URL or ID
            
        Returns:
            Dict containing video metadata
        """
        result = await self.client.call_tool("get_video_metadata", {
            "video_url": video_url
        })
        
        if result.success:
            return result.data
        else:
            raise ToolExecutionError(f"Failed to get video metadata: {result.error}")
    
    async def check_transcript_availability(self, video_url: str) -> Dict[str, Any]:
        """
        Check transcript availability for a YouTube video
        
        Args:
            video_url: YouTube video URL or ID
            
        Returns:
            Dict containing availability information
        """
        result = await self.client.call_tool("check_transcript_availability", {
            "video_url": video_url
        })
        
        if result.success:
            return result.data
        else:
            raise ToolExecutionError(f"Failed to check transcript availability: {result.error}")
    
    async def batch_fetch_transcripts(self, video_urls: List[str], 
                                    language: str = "en", 
                                    max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch transcripts for multiple videos concurrently
        
        Args:
            video_urls: List of YouTube video URLs or IDs
            language: Preferred language code
            max_concurrent: Maximum number of concurrent requests
            
        Returns:
            List of transcript data dictionaries
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_single(url: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    return await self.fetch_transcript(url, language)
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "video_url": url
                    }
        
        tasks = [fetch_single(url) for url in video_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append({
                    "success": False,
                    "error": str(result),
                    "video_url": video_urls[i]
                })
            else:
                final_results.append(result)
        
        return final_results
    
    def is_connected(self) -> bool:
        """Check if client is connected to server"""
        return self.client.is_connected()


# Factory function for easy client creation
def create_youtube_mcp_client(host: str = "localhost", port: int = 8000) -> YouTubeMCPClient:
    """
    Factory function to create YouTube MCP client
    
    Args:
        host: MCP server host
        port: MCP server port
        
    Returns:
        YouTubeMCPClient instance
    """
    return YouTubeMCPClient(host, port)


# Example usage and testing
async def test_mcp_client():
    """Test the MCP client functionality"""
    async with create_youtube_mcp_client() as client:
        # Test connection
        if not client.is_connected():
            print("Failed to connect to MCP server")
            return
        
        print("Connected to MCP server successfully!")
        
        # Test video URL
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        try:
            # Test transcript availability
            print("\n1. Checking transcript availability...")
            availability = await client.check_transcript_availability(test_url)
            print(json.dumps(availability, indent=2))
            
            # Test metadata extraction
            print("\n2. Getting video metadata...")
            metadata = await client.get_video_metadata(test_url)
            print(json.dumps(metadata, indent=2))
            
            # Test transcript fetching
            if availability.get("transcripts_available", False):
                print("\n3. Fetching transcript...")
                transcript = await client.fetch_transcript(test_url)
                print(f"Transcript method: {transcript.get('method')}")
                print(f"Transcript length: {len(transcript.get('full_text', ''))}")
                print(f"Language: {transcript.get('language')}")
            else:
                print("\n3. Transcript not available for this video")
            
            # Test batch processing
            print("\n4. Testing batch processing...")
            test_urls = [test_url, "https://www.youtube.com/watch?v=invalid"]
            batch_results = await client.batch_fetch_transcripts(test_urls, max_concurrent=2)
            print(f"Batch results: {len(batch_results)} processed")
            for i, result in enumerate(batch_results):
                print(f"  Video {i+1}: {'Success' if result.get('success') else 'Failed'}")
            
        except Exception as e:
            print(f"Error during testing: {e}")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_mcp_client())