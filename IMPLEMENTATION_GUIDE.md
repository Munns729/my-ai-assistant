# Implementation Guide: Refactoring to Plugin Architecture

## Quick Start Implementation

Here's a practical guide to refactor your current architecture for unlimited source scalability.

## Step 1: Create the Plugin System

### 1.1 Base Plugin Interface

```python
# source_plugin_base.py
from abc import ABC, abstractmethod
from typing import Dict, List, AsyncIterator, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio

@dataclass
class ContentItem:
    """Unified content representation (keep your existing one)"""
    id: str
    source: str  # Changed from Enum to str for flexibility
    title: str
    content: str
    timestamp: str
    metadata: Dict
    entities: List = None
    processed: bool = False

class SourceCapability(Enum):
    """Capabilities that sources can support"""
    SEARCH = "search"
    STREAM = "stream"
    HISTORICAL = "historical"
    REAL_TIME = "real_time"
    BATCH = "batch"

class SourcePlugin(ABC):
    """Base class for all source plugins"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.initialized = False
        
    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique identifier for this source"""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[SourceCapability]:
        """List of capabilities this source supports"""
        pass
    
    @property
    def requires_auth(self) -> bool:
        """Whether this source requires authentication"""
        return False
    
    async def initialize(self) -> bool:
        """Initialize the plugin (connect to APIs, authenticate, etc.)"""
        if self.requires_auth and not self.validate_config():
            raise ValueError(f"Invalid configuration for {self.source_id}")
        self.initialized = True
        return True
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the configuration"""
        pass
    
    @abstractmethod
    async def fetch_content(self, params: Dict) -> AsyncIterator[ContentItem]:
        """Main method to fetch content from the source"""
        pass
    
    async def search_content(self, query: str, filters: Dict = None) -> List[ContentItem]:
        """Search capability (optional)"""
        if SourceCapability.SEARCH not in self.capabilities:
            raise NotImplementedError(f"{self.source_id} does not support search")
        return []
    
    async def stream_content(self) -> AsyncIterator[ContentItem]:
        """Real-time streaming capability (optional)"""
        if SourceCapability.STREAM not in self.capabilities:
            raise NotImplementedError(f"{self.source_id} does not support streaming")
        yield
    
    def get_rate_limit_info(self) -> Dict:
        """Get rate limiting information"""
        return {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "concurrent_requests": 5
        }
```

### 1.2 Plugin Registry

```python
# plugin_registry.py
import importlib
import os
import json
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PluginRegistry:
    """Manages all source plugins"""
    
    def __init__(self, config_path: str = "config/sources.json"):
        self.plugins: Dict[str, SourcePlugin] = {}
        self.configs: Dict[str, Dict] = {}
        self.config_path = config_path
        self.load_configs()
    
    def load_configs(self):
        """Load source configurations from file"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.configs = json.load(f)
    
    def save_configs(self):
        """Save configurations to file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.configs, f, indent=2)
    
    async def register_plugin(self, plugin_class: type, config: Optional[Dict] = None):
        """Register a plugin with optional configuration"""
        try:
            # Use provided config or load from saved configs
            plugin_config = config or self.configs.get(plugin_class.__name__, {})
            
            # Create plugin instance
            plugin = plugin_class(plugin_config)
            
            # Initialize plugin
            await plugin.initialize()
            
            # Register
            self.plugins[plugin.source_id] = plugin
            self.configs[plugin.source_id] = plugin_config
            
            logger.info(f"Successfully registered plugin: {plugin.source_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register plugin {plugin_class.__name__}: {e}")
            return False
    
    def discover_plugins(self, plugin_dir: str = "plugins"):
        """Auto-discover plugins in a directory"""
        plugin_path = Path(plugin_dir)
        if not plugin_path.exists():
            logger.warning(f"Plugin directory {plugin_dir} does not exist")
            return
        
        # Add plugin directory to Python path
        import sys
        sys.path.insert(0, str(plugin_path.parent))
        
        discovered = []
        for file_path in plugin_path.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
                
            module_name = file_path.stem
            try:
                module = importlib.import_module(f"{plugin_dir}.{module_name}")
                
                # Find all SourcePlugin subclasses in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, SourcePlugin) and 
                        attr != SourcePlugin):
                        discovered.append(attr)
                        
            except Exception as e:
                logger.error(f"Failed to import plugin module {module_name}: {e}")
        
        return discovered
    
    def get_plugin(self, source_id: str) -> Optional[SourcePlugin]:
        """Get a plugin by source ID"""
        return self.plugins.get(source_id)
    
    def list_sources(self) -> List[str]:
        """List all registered source IDs"""
        return list(self.plugins.keys())
    
    def get_source_info(self, source_id: str) -> Dict:
        """Get information about a source"""
        plugin = self.get_plugin(source_id)
        if not plugin:
            return {}
        
        return {
            "id": plugin.source_id,
            "capabilities": [cap.value for cap in plugin.capabilities],
            "requires_auth": plugin.requires_auth,
            "rate_limits": plugin.get_rate_limit_info(),
            "initialized": plugin.initialized
        }
```

## Step 2: Convert Existing Sources to Plugins

### 2.1 YouTube Plugin (Refactored from your MCP client)

```python
# plugins/youtube_plugin.py
from source_plugin_base import SourcePlugin, ContentItem, SourceCapability
from typing import Dict, AsyncIterator, List
import yt_dlp
import asyncio

class YouTubePlugin(SourcePlugin):
    """YouTube source plugin"""
    
    @property
    def source_id(self) -> str:
        return "youtube"
    
    @property
    def capabilities(self) -> List[SourceCapability]:
        return [SourceCapability.SEARCH, SourceCapability.BATCH]
    
    def validate_config(self) -> bool:
        # YouTube doesn't require auth for basic operations
        return True
    
    async def fetch_content(self, params: Dict) -> AsyncIterator[ContentItem]:
        """Fetch YouTube video transcripts"""
        video_urls = params.get("urls", [])
        
        for url in video_urls:
            try:
                content_item = await self._fetch_single_video(url)
                if content_item:
                    yield content_item
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                continue
    
    async def _fetch_single_video(self, url: str) -> ContentItem:
        """Fetch a single video's transcript and metadata"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'skip_download': True,
        }
        
        loop = asyncio.get_event_loop()
        
        def extract_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        # Run in executor to avoid blocking
        info = await loop.run_in_executor(None, extract_info)
        
        # Extract transcript
        transcript = ""
        if 'subtitles' in info:
            # Process subtitles to get transcript
            # This is simplified - you'd need to parse the subtitle file
            transcript = self._parse_subtitles(info['subtitles'])
        
        return ContentItem(
            id=f"youtube_{info['id']}",
            source="youtube",
            title=info.get('title', 'Unknown'),
            content=transcript or info.get('description', ''),
            timestamp=str(info.get('upload_date', '')),
            metadata={
                'url': url,
                'channel': info.get('channel', ''),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'tags': info.get('tags', [])
            }
        )
    
    async def search_content(self, query: str, filters: Dict = None) -> List[ContentItem]:
        """Search YouTube for videos"""
        max_results = filters.get('max_results', 10) if filters else 10
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'default_search': 'ytsearch',
            'max_downloads': max_results
        }
        
        loop = asyncio.get_event_loop()
        
        def search():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        
        results = await loop.run_in_executor(None, search)
        
        content_items = []
        for entry in results.get('entries', []):
            content_items.append(ContentItem(
                id=f"youtube_{entry['id']}",
                source="youtube",
                title=entry.get('title', ''),
                content=entry.get('description', ''),
                timestamp="",
                metadata={
                    'url': entry.get('url', ''),
                    'channel': entry.get('channel', ''),
                    'duration': entry.get('duration', 0)
                }
            ))
        
        return content_items
```

### 2.2 Reddit Plugin

```python
# plugins/reddit_plugin.py
import asyncpraw
from source_plugin_base import SourcePlugin, ContentItem, SourceCapability
from typing import Dict, AsyncIterator, List

class RedditPlugin(SourcePlugin):
    """Reddit source plugin using asyncpraw"""
    
    @property
    def source_id(self) -> str:
        return "reddit"
    
    @property
    def capabilities(self) -> List[SourceCapability]:
        return [SourceCapability.SEARCH, SourceCapability.STREAM, SourceCapability.HISTORICAL]
    
    @property
    def requires_auth(self) -> bool:
        return True
    
    def validate_config(self) -> bool:
        required = ['client_id', 'client_secret', 'user_agent']
        return all(key in self.config for key in required)
    
    async def initialize(self) -> bool:
        """Initialize Reddit client"""
        await super().initialize()
        
        self.reddit = asyncpraw.Reddit(
            client_id=self.config['client_id'],
            client_secret=self.config['client_secret'],
            user_agent=self.config['user_agent']
        )
        
        return True
    
    async def fetch_content(self, params: Dict) -> AsyncIterator[ContentItem]:
        """Fetch Reddit content"""
        subreddit_name = params.get('subreddit', 'all')
        sort_by = params.get('sort', 'hot')  # hot, new, top
        time_filter = params.get('time_filter', 'day')  # hour, day, week, month, year, all
        limit = params.get('limit', 25)
        
        subreddit = await self.reddit.subreddit(subreddit_name)
        
        # Get submissions based on sort method
        if sort_by == 'hot':
            submissions = subreddit.hot(limit=limit)
        elif sort_by == 'new':
            submissions = subreddit.new(limit=limit)
        elif sort_by == 'top':
            submissions = subreddit.top(time_filter=time_filter, limit=limit)
        else:
            submissions = subreddit.hot(limit=limit)
        
        async for submission in submissions:
            # Fetch some comments
            await submission.load()
            await submission.comments.replace_more(limit=0)
            
            # Build content with post and top comments
            content_parts = [
                f"Title: {submission.title}",
                f"Author: {submission.author.name if submission.author else '[deleted]'}",
                f"Score: {submission.score}",
                f"\nPost Content:\n{submission.selftext}"
            ]
            
            # Add top 5 comments
            content_parts.append("\nTop Comments:")
            for comment in submission.comments[:5]:
                if hasattr(comment, 'body'):
                    content_parts.append(f"- {comment.body[:500]}")
            
            content = "\n".join(content_parts)
            
            yield ContentItem(
                id=f"reddit_{submission.id}",
                source="reddit",
                title=submission.title,
                content=content,
                timestamp=str(submission.created_utc),
                metadata={
                    'subreddit': subreddit_name,
                    'author': submission.author.name if submission.author else '[deleted]',
                    'score': submission.score,
                    'num_comments': submission.num_comments,
                    'url': f"https://reddit.com{submission.permalink}",
                    'is_video': submission.is_video,
                    'is_self': submission.is_self,
                    'awards': len(submission.all_awardings) if hasattr(submission, 'all_awardings') else 0
                }
            )
    
    async def stream_content(self) -> AsyncIterator[ContentItem]:
        """Stream new submissions in real-time"""
        subreddit = await self.reddit.subreddit("all")
        
        async for submission in subreddit.stream.submissions():
            yield ContentItem(
                id=f"reddit_{submission.id}",
                source="reddit",
                title=submission.title,
                content=submission.selftext or "",
                timestamp=str(submission.created_utc),
                metadata={
                    'subreddit': submission.subreddit.display_name,
                    'author': submission.author.name if submission.author else '[deleted]',
                    'url': f"https://reddit.com{submission.permalink}"
                }
            )
```

## Step 3: Integrate with Your Workflow

### 3.1 Enhanced Workflow Integration

```python
# enhanced_knowledge_workflow.py
from typing import Dict, List, Any, Optional
from langgraph import StateGraph
from plugin_registry import PluginRegistry
import asyncio
import logging

logger = logging.getLogger(__name__)

class EnhancedKnowledgeWorkflow:
    """Workflow that dynamically works with any registered plugins"""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.registry = PluginRegistry()
        self.workflow = None
        
    async def initialize(self):
        """Initialize the workflow and discover plugins"""
        # Discover and register all available plugins
        plugin_classes = self.registry.discover_plugins()
        
        for plugin_class in plugin_classes:
            try:
                await self.registry.register_plugin(plugin_class)
            except Exception as e:
                logger.error(f"Failed to register {plugin_class.__name__}: {e}")
        
        # Create workflow with registered plugins
        self.workflow = self._create_workflow()
        
        logger.info(f"Initialized with sources: {self.registry.list_sources()}")
    
    def _create_workflow(self) -> StateGraph:
        """Create dynamic workflow based on available plugins"""
        workflow = StateGraph(Dict)
        
        # Add universal nodes
        workflow.add_node("collect", self._collect_node)
        workflow.add_node("process", self._process_node)
        workflow.add_node("extract_entities", self._extract_entities_node)
        workflow.add_node("build_graph", self._build_graph_node)
        
        # Add edges
        workflow.set_entry_point("collect")
        workflow.add_edge("collect", "process")
        workflow.add_edge("process", "extract_entities")
        workflow.add_edge("extract_entities", "build_graph")
        workflow.add_edge("build_graph", END)
        
        return workflow.compile()
    
    async def _collect_node(self, state: Dict) -> Dict:
        """Collect from all requested sources in parallel"""
        source_configs = state.get('sources', {})
        all_content = []
        
        # Create collection tasks for each source
        tasks = []
        for source_id, params in source_configs.items():
            plugin = self.registry.get_plugin(source_id)
            if plugin:
                tasks.append(self._collect_from_plugin(plugin, params))
            else:
                logger.warning(f"Unknown source: {source_id}")
        
        # Run all collections in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Collection error: {result}")
                else:
                    all_content.extend(result)
        
        state['content_items'] = all_content
        state['total_collected'] = len(all_content)
        
        return state
    
    async def _collect_from_plugin(self, plugin: SourcePlugin, params: Dict) -> List[ContentItem]:
        """Collect content from a single plugin"""
        items = []
        
        try:
            async for item in plugin.fetch_content(params):
                items.append(item)
                
                # Add batching limit
                if len(items) >= params.get('max_items', 100):
                    break
                    
        except Exception as e:
            logger.error(f"Error collecting from {plugin.source_id}: {e}")
        
        return items
    
    async def run(self, source_configs: Dict) -> Dict:
        """Run the workflow with specified source configurations"""
        if not self.workflow:
            await self.initialize()
        
        initial_state = {
            'sources': source_configs,
            'content_items': [],
            'entities': [],
            'graph': {}
        }
        
        result = await self.workflow.ainvoke(initial_state)
        return result
```

### 3.2 Usage Example

```python
# example_usage.py
import asyncio
from enhanced_knowledge_workflow import EnhancedKnowledgeWorkflow

async def main():
    # Initialize workflow
    workflow = EnhancedKnowledgeWorkflow(openai_api_key="your-key")
    await workflow.initialize()
    
    # Configure sources to fetch from
    source_configs = {
        'youtube': {
            'urls': [
                'https://www.youtube.com/watch?v=...',
                'https://www.youtube.com/watch?v=...'
            ]
        },
        'reddit': {
            'subreddit': 'MachineLearning',
            'sort': 'top',
            'time_filter': 'week',
            'limit': 50
        },
        'linkedin': {
            'search_query': 'artificial intelligence SME',
            'max_results': 25
        }
    }
    
    # Run workflow
    result = await workflow.run(source_configs)
    
    print(f"Collected {result['total_collected']} items")
    print(f"Extracted {len(result['entities'])} entities")
    print(f"Built graph with {len(result['graph'].get('nodes', []))} nodes")

if __name__ == "__main__":
    asyncio.run(main())
```

## Step 4: Add New Sources Easily

### 4.1 Template for New Source

```python
# plugins/custom_source_plugin.py
from source_plugin_base import SourcePlugin, ContentItem, SourceCapability
from typing import Dict, AsyncIterator, List

class CustomSourcePlugin(SourcePlugin):
    """Template for creating new source plugins"""
    
    @property
    def source_id(self) -> str:
        return "custom_source_name"
    
    @property
    def capabilities(self) -> List[SourceCapability]:
        return [SourceCapability.BATCH]
    
    @property
    def requires_auth(self) -> bool:
        return False  # Change based on your source
    
    def validate_config(self) -> bool:
        # Add validation logic
        return True
    
    async def fetch_content(self, params: Dict) -> AsyncIterator[ContentItem]:
        """Implement your content fetching logic here"""
        
        # Example: Fetch from an API
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Your API calls here
            pass
        
        # Yield ContentItem objects
        yield ContentItem(
            id="unique_id",
            source=self.source_id,
            title="Content Title",
            content="Content body",
            timestamp="2024-01-01",
            metadata={}
        )
```

### 4.2 LinkedIn Plugin Example

```python
# plugins/linkedin_plugin.py
from source_plugin_base import SourcePlugin, ContentItem, SourceCapability
from typing import Dict, AsyncIterator, List
from linkedin_api import Linkedin  # Third-party library

class LinkedInPlugin(SourcePlugin):
    """LinkedIn source plugin"""
    
    @property
    def source_id(self) -> str:
        return "linkedin"
    
    @property
    def capabilities(self) -> List[SourceCapability]:
        return [SourceCapability.SEARCH, SourceCapability.BATCH]
    
    @property
    def requires_auth(self) -> bool:
        return True
    
    def validate_config(self) -> bool:
        return 'username' in self.config and 'password' in self.config
    
    async def initialize(self) -> bool:
        await super().initialize()
        
        # Initialize LinkedIn API client
        self.api = Linkedin(
            self.config['username'],
            self.config['password']
        )
        
        return True
    
    async def fetch_content(self, params: Dict) -> AsyncIterator[ContentItem]:
        """Fetch LinkedIn posts and articles"""
        
        # Get feed posts
        feed = self.api.get_feed_posts(limit=params.get('limit', 10))
        
        for post in feed:
            content = self._extract_post_content(post)
            
            yield ContentItem(
                id=f"linkedin_{post.get('id', '')}",
                source="linkedin",
                title=content['title'],
                content=content['body'],
                timestamp=str(post.get('created', '')),
                metadata={
                    'author': post.get('author', {}).get('name', ''),
                    'author_headline': post.get('author', {}).get('headline', ''),
                    'likes': post.get('numLikes', 0),
                    'comments': post.get('numComments', 0),
                    'shares': post.get('numShares', 0),
                    'post_type': post.get('type', '')
                }
            )
    
    def _extract_post_content(self, post: Dict) -> Dict:
        """Extract content from LinkedIn post structure"""
        title = post.get('title', '')
        
        # Handle different post types
        if 'article' in post:
            title = post['article'].get('title', title)
            body = post['article'].get('description', '')
        elif 'video' in post:
            title = post['video'].get('title', title)
            body = post['video'].get('description', '')
        else:
            body = post.get('commentary', '') or post.get('description', '')
        
        return {'title': title or 'LinkedIn Post', 'body': body}
```

## Step 5: Configuration Management

### 5.1 Source Configuration File

```json
// config/sources.json
{
  "youtube": {
    "enabled": true,
    "rate_limit": {
      "requests_per_minute": 100
    }
  },
  "reddit": {
    "enabled": true,
    "client_id": "${REDDIT_CLIENT_ID}",
    "client_secret": "${REDDIT_CLIENT_SECRET}",
    "user_agent": "KnowledgeGraphBot/1.0"
  },
  "linkedin": {
    "enabled": true,
    "username": "${LINKEDIN_USERNAME}",
    "password": "${LINKEDIN_PASSWORD}"
  },
  "substack": {
    "enabled": true,
    "newsletters": [
      "https://newsletter1.substack.com",
      "https://newsletter2.substack.com"
    ]
  },
  "custom_rss": {
    "enabled": true,
    "feeds": [
      {
        "url": "https://example.com/feed.xml",
        "name": "Example Blog"
      }
    ]
  }
}
```

### 5.2 Environment Variables

```bash
# .env
OPENAI_API_KEY=your-openai-key
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
LINKEDIN_USERNAME=your-linkedin-email
LINKEDIN_PASSWORD=your-linkedin-password
```

## Key Benefits of This Architecture

1. **Zero Code Changes for New Sources**: Just drop a new plugin file in the `plugins/` directory
2. **Parallel Processing**: All sources are fetched concurrently
3. **Failure Isolation**: One source failing doesn't affect others
4. **Configuration-Driven**: All settings in config files, not code
5. **Testable**: Each plugin can be tested independently
6. **Scalable**: Can handle hundreds of sources without architectural changes

## Migration Path from Current Code

1. **Week 1**: Create plugin base classes and registry
2. **Week 2**: Convert YouTube MCP client to plugin
3. **Week 3**: Add Reddit and LinkedIn plugins
4. **Week 4**: Refactor workflow to use plugin system
5. **Week 5**: Add configuration management
6. **Week 6**: Testing and optimization

This refactored architecture will allow you to add any new source by simply creating a new plugin file, without touching the core system.