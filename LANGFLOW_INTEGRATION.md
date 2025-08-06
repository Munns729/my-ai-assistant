# LangFlow Integration for Multi-Source Knowledge Graph

## Overview

LangFlow transforms your architecture from code-based workflows to visual, configurable pipelines that can be modified without programming. This is perfect for a plugin-based system where each source might need different processing logic.

## 🎯 Integration Strategy

### Current Architecture
```
Source Plugins → LangGraph Workflow → Knowledge Graph
```

### With LangFlow
```
Source Plugins → LangFlow Visual Pipelines → Knowledge Graph
                         ↓
                  (Customizable per source)
```

## 🏗️ Architecture with LangFlow

### 1. Core Plugin System with LangFlow

```python
# enhanced_source_plugin.py
from abc import ABC, abstractmethod
from typing import Dict, List, AsyncIterator, Optional
from langflow import load_flow_from_json
import aiofiles
import json

class LangFlowSourcePlugin(ABC):
    """Enhanced plugin that uses LangFlow for processing"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.langflow_pipeline = None
        self.pipeline_path = None
        
    @property
    @abstractmethod
    def source_id(self) -> str:
        pass
    
    @property
    def default_pipeline_path(self) -> str:
        """Path to default LangFlow pipeline for this source"""
        return f"langflow_pipelines/{self.source_id}_pipeline.json"
    
    async def initialize(self) -> bool:
        """Initialize plugin and load LangFlow pipeline"""
        await super().initialize()
        
        # Load source-specific LangFlow pipeline
        pipeline_path = self.config.get('pipeline_path', self.default_pipeline_path)
        self.langflow_pipeline = await self.load_langflow_pipeline(pipeline_path)
        
        return True
    
    async def load_langflow_pipeline(self, path: str):
        """Load LangFlow pipeline from JSON file"""
        try:
            async with aiofiles.open(path, 'r') as f:
                pipeline_json = await f.read()
            
            # Load the flow - this creates a callable pipeline
            flow = load_flow_from_json(pipeline_json)
            return flow
            
        except FileNotFoundError:
            # Fallback to default processing pipeline
            return await self.create_default_pipeline()
    
    async def create_default_pipeline(self):
        """Create a default LangFlow pipeline programmatically"""
        from langflow import CustomComponent, Flow
        
        # Create a simple default flow
        flow = Flow(name=f"{self.source_id}_default")
        
        # Add components
        flow.add_component("input", "TextInput")
        flow.add_component("entity_extractor", "OpenAIEntityExtractor")
        flow.add_component("output", "GraphOutput")
        
        # Connect components
        flow.connect("input", "entity_extractor")
        flow.connect("entity_extractor", "output")
        
        return flow
    
    async def process_content(self, content: ContentItem) -> Dict:
        """Process content through LangFlow pipeline"""
        if not self.langflow_pipeline:
            raise ValueError("LangFlow pipeline not initialized")
        
        # Run content through the visual pipeline
        result = await self.langflow_pipeline.arun(
            input_text=content.content,
            metadata={
                "source": self.source_id,
                "title": content.title,
                "timestamp": content.timestamp,
                "original_metadata": content.metadata
            }
        )
        
        return result
```

### 2. LangFlow Pipeline Manager

```python
# langflow_pipeline_manager.py
from typing import Dict, List, Optional
from langflow import Flow
import os
import json

class LangFlowPipelineManager:
    """Manages LangFlow pipelines for different sources"""
    
    def __init__(self, pipeline_dir: str = "langflow_pipelines"):
        self.pipeline_dir = pipeline_dir
        self.pipelines: Dict[str, Flow] = {}
        self.ensure_pipeline_directory()
    
    def ensure_pipeline_directory(self):
        """Create pipeline directory if it doesn't exist"""
        os.makedirs(self.pipeline_dir, exist_ok=True)
        
        # Create subdirectories for organization
        os.makedirs(f"{self.pipeline_dir}/sources", exist_ok=True)
        os.makedirs(f"{self.pipeline_dir}/processors", exist_ok=True)
        os.makedirs(f"{self.pipeline_dir}/templates", exist_ok=True)
    
    async def create_source_pipeline(self, source_id: str, template: str = "default"):
        """Create a new LangFlow pipeline for a source"""
        
        # LangFlow pipeline structure for knowledge graph
        pipeline_config = {
            "name": f"{source_id}_knowledge_pipeline",
            "description": f"Knowledge extraction pipeline for {source_id}",
            "components": [
                {
                    "id": "content_input",
                    "type": "TextLoader",
                    "config": {
                        "input_type": "content_item"
                    }
                },
                {
                    "id": "source_preprocessor",
                    "type": "CustomProcessor",
                    "config": {
                        "source_type": source_id,
                        "preprocessing_steps": self.get_source_preprocessing(source_id)
                    }
                },
                {
                    "id": "entity_extractor",
                    "type": "LLMChain",
                    "config": {
                        "llm": "gpt-4",
                        "prompt_template": self.get_entity_prompt(source_id),
                        "output_parser": "entity_parser"
                    }
                },
                {
                    "id": "entity_deduplicator",
                    "type": "VectorSimilarity",
                    "config": {
                        "embedding_model": "text-embedding-ada-002",
                        "similarity_threshold": 0.85
                    }
                },
                {
                    "id": "relationship_extractor",
                    "type": "LLMChain",
                    "config": {
                        "llm": "gpt-4",
                        "prompt_template": self.get_relationship_prompt(source_id)
                    }
                },
                {
                    "id": "graph_builder",
                    "type": "KnowledgeGraphBuilder",
                    "config": {
                        "graph_type": "networkx",
                        "merge_strategy": "embedding_similarity"
                    }
                },
                {
                    "id": "quality_checker",
                    "type": "QualityAssurance",
                    "config": {
                        "min_confidence": 0.7,
                        "require_evidence": True
                    }
                },
                {
                    "id": "output_formatter",
                    "type": "GraphFormatter",
                    "config": {
                        "format": "knowledge_graph",
                        "include_metadata": True
                    }
                }
            ],
            "connections": [
                ["content_input", "source_preprocessor"],
                ["source_preprocessor", "entity_extractor"],
                ["entity_extractor", "entity_deduplicator"],
                ["entity_deduplicator", "relationship_extractor"],
                ["relationship_extractor", "graph_builder"],
                ["graph_builder", "quality_checker"],
                ["quality_checker", "output_formatter"]
            ],
            "source_specific_config": self.get_source_specific_config(source_id)
        }
        
        # Save pipeline configuration
        pipeline_path = f"{self.pipeline_dir}/sources/{source_id}_pipeline.json"
        with open(pipeline_path, 'w') as f:
            json.dump(pipeline_config, f, indent=2)
        
        return pipeline_path
    
    def get_source_preprocessing(self, source_id: str) -> List[Dict]:
        """Get source-specific preprocessing steps"""
        preprocessing_map = {
            "reddit": [
                {"step": "extract_thread_structure", "preserve_hierarchy": True},
                {"step": "filter_deleted_content", "replace_with": "[deleted]"},
                {"step": "extract_vote_signals", "weight_by_score": True}
            ],
            "youtube": [
                {"step": "segment_by_timestamps", "chunk_size": 300},
                {"step": "extract_speaker_segments", "identify_speakers": True},
                {"step": "clean_auto_captions", "fix_punctuation": True}
            ],
            "linkedin": [
                {"step": "extract_professional_context", "focus": ["roles", "companies"]},
                {"step": "identify_post_type", "categories": ["article", "post", "job"]},
                {"step": "extract_engagement_metrics", "normalize": True}
            ],
            "substack": [
                {"step": "extract_article_structure", "preserve_sections": True},
                {"step": "identify_key_themes", "use_nlp": True},
                {"step": "extract_author_context", "include_bio": True}
            ]
        }
        
        return preprocessing_map.get(source_id, [
            {"step": "basic_cleaning", "remove_html": True},
            {"step": "sentence_segmentation", "min_length": 10}
        ])
    
    def get_entity_prompt(self, source_id: str) -> str:
        """Get source-specific entity extraction prompt"""
        base_prompt = """Extract entities from this {source_type} content.
        
Focus on:
- People (with roles/titles)
- Organizations
- Technologies/Products
- Concepts/Topics
- Events
- Locations

{source_specific_instructions}

Content: {content}

Return JSON array of entities with confidence scores.
"""
        
        source_instructions = {
            "reddit": "Pay special attention to: mentioned subreddits, user flairs, and technical discussions",
            "youtube": "Focus on: speakers, companies mentioned, and key topics discussed",
            "linkedin": "Emphasize: professional roles, companies, skills, and industry terms",
            "substack": "Extract: author insights, referenced works, and key arguments"
        }
        
        return base_prompt.format(
            source_type=source_id,
            source_specific_instructions=source_instructions.get(source_id, "")
        )
```

### 3. Visual Pipeline Examples

#### 3.1 Reddit Pipeline (Visual LangFlow)
```yaml
# langflow_pipelines/sources/reddit_pipeline.yaml
name: Reddit Knowledge Extraction
components:
  - RedditContentLoader:
      filters:
        - min_score: 10
        - include_comments: true
        - max_depth: 3
  
  - ThreadAnalyzer:
      extract:
        - sentiment
        - controversy_score
        - expertise_signals
  
  - RedditEntityExtractor:
      focus:
        - technical_terms
        - mentioned_projects
        - user_expertise
      confidence_boost:
        - high_karma_users: 0.2
        - verified_flairs: 0.3
  
  - CommunityContextEnricher:
      add_context:
        - subreddit_description
        - related_posts
        - user_history_summary
  
  - GraphBuilder:
      relationship_types:
        - discusses
        - recommends
        - contradicts
        - builds_upon
```

#### 3.2 YouTube Pipeline (Visual LangFlow)
```yaml
# langflow_pipelines/sources/youtube_pipeline.yaml
name: YouTube Knowledge Extraction
components:
  - YouTubeTranscriptLoader:
      include:
        - auto_captions: true
        - timestamps: true
        - speaker_detection: true
  
  - VideoSegmenter:
      strategy: topic_based
      min_segment_length: 30s
      max_segment_length: 5m
  
  - MultiModalAnalyzer:
      analyze:
        - transcript_text
        - video_title
        - description
        - comments_sample
  
  - YouTubeEntityExtractor:
      boost_confidence_for:
        - repeated_mentions: 0.3
        - title_entities: 0.4
        - speaker_emphasis: 0.2
  
  - TemporalRelationshipExtractor:
      track:
        - concept_evolution
        - topic_transitions
        - reference_timing
```

### 4. Integration with Existing Workflow

```python
# enhanced_workflow_with_langflow.py
from typing import Dict, List
from plugin_registry import PluginRegistry
from langflow_pipeline_manager import LangFlowPipelineManager
import asyncio

class LangFlowKnowledgeWorkflow:
    """Enhanced workflow using LangFlow for visual pipeline configuration"""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.plugin_registry = PluginRegistry()
        self.pipeline_manager = LangFlowPipelineManager()
        
    async def initialize(self):
        """Initialize plugins and their LangFlow pipelines"""
        # Discover plugins
        plugins = self.plugin_registry.discover_plugins()
        
        # Initialize each plugin with its LangFlow pipeline
        for plugin_class in plugins:
            plugin = plugin_class()
            
            # Create or load LangFlow pipeline for this source
            pipeline_path = await self.pipeline_manager.create_source_pipeline(
                plugin.source_id
            )
            
            # Configure plugin with pipeline
            plugin.config['pipeline_path'] = pipeline_path
            
            # Register configured plugin
            await self.plugin_registry.register_plugin(plugin)
    
    async def process_sources(self, source_configs: Dict) -> Dict:
        """Process multiple sources through their LangFlow pipelines"""
        tasks = []
        
        for source_id, config in source_configs.items():
            plugin = self.plugin_registry.get_plugin(source_id)
            if plugin:
                task = self.process_with_langflow(plugin, config)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge results into unified knowledge graph
        return self.merge_knowledge_graphs(results)
    
    async def process_with_langflow(self, plugin, config):
        """Process source content through its LangFlow pipeline"""
        # Fetch content
        content_items = []
        async for item in plugin.fetch_content(config):
            content_items.append(item)
        
        # Process each item through LangFlow pipeline
        processed_items = []
        for item in content_items:
            result = await plugin.process_content(item)
            processed_items.append(result)
        
        return {
            'source': plugin.source_id,
            'items': processed_items,
            'graph': self.build_subgraph(processed_items)
        }
```

### 5. LangFlow UI Benefits

#### 5.1 Visual Pipeline Builder
```python
# langflow_ui_integration.py
class LangFlowUIIntegration:
    """Integration with LangFlow UI for visual editing"""
    
    def __init__(self, ui_port: int = 7860):
        self.ui_port = ui_port
        self.flows = {}
    
    def launch_editor(self, source_id: str):
        """Launch LangFlow UI for editing source pipeline"""
        import webbrowser
        
        # Start LangFlow server if not running
        self.ensure_langflow_server()
        
        # Open browser to source pipeline
        url = f"http://localhost:{self.ui_port}/flow/{source_id}_pipeline"
        webbrowser.open(url)
    
    def register_custom_components(self):
        """Register custom components for knowledge graph building"""
        from langflow import CustomComponent
        
        components = [
            EntityExtractorComponent,
            RelationshipExtractorComponent,
            KnowledgeGraphBuilderComponent,
            SourcePreprocessorComponent,
            DeduplicationComponent
        ]
        
        for component in components:
            self.register_component(component)
```

## 🎯 Key Advantages of LangFlow Integration

### 1. **Visual Configuration**
- Non-developers can modify extraction logic
- See data flow through the pipeline
- Test changes immediately

### 2. **Source-Specific Pipelines**
- Each source gets its own visual pipeline
- Easy A/B testing of different approaches
- Version control for pipeline configurations

### 3. **Reusable Components**
```python
# Create library of reusable LangFlow components
- EntityExtractor
- RelationshipDetector  
- QualityChecker
- SourceSpecificPreprocessor
- GraphMerger
```

### 4. **Dynamic Pipeline Loading**
```python
# Switch pipelines based on content type
if content.metadata.get('content_type') == 'technical':
    pipeline = 'technical_extraction_pipeline'
else:
    pipeline = 'general_extraction_pipeline'
```

## 📋 Implementation Steps

### Week 1: LangFlow Setup
1. Install LangFlow
2. Create custom knowledge graph components
3. Build first visual pipeline (YouTube)

### Week 2: Plugin Integration
1. Modify plugin base to support LangFlow
2. Create pipeline manager
3. Test with existing sources

### Week 3: Visual Pipelines
1. Create visual pipelines for each source
2. Add source-specific components
3. Implement pipeline versioning

### Week 4: Advanced Features
1. Add conditional logic in pipelines
2. Implement A/B testing
3. Create pipeline templates

## 🔧 Configuration Example

```yaml
# config/langflow_config.yaml
langflow:
  ui_enabled: true
  ui_port: 7860
  
  component_library:
    path: ./langflow_components
    auto_discover: true
  
  pipelines:
    directory: ./langflow_pipelines
    
    defaults:
      llm_model: gpt-4
      embedding_model: text-embedding-ada-002
      
    source_overrides:
      reddit:
        llm_model: gpt-3.5-turbo  # Cheaper for high volume
        preprocessing:
          - remove_deleted_content
          - extract_vote_signals
      
      youtube:
        llm_model: gpt-4
        chunk_strategy: timestamp_based
        
  monitoring:
    track_performance: true
    log_errors: true
    export_metrics: prometheus
```

## 🚀 Advanced LangFlow Features

### 1. **Conditional Processing**
```python
# In LangFlow pipeline
if source == "reddit" and score > 100:
    use_detailed_extraction
else:
    use_quick_extraction
```

### 2. **Pipeline Composition**
```python
# Combine multiple pipelines
base_pipeline + source_specific_pipeline + quality_check_pipeline
```

### 3. **Real-time Monitoring**
- See entities being extracted in real-time
- Monitor performance bottlenecks
- Track extraction quality metrics

## Summary

LangFlow integration transforms your architecture from:
- **Static** code-based pipelines → **Dynamic** visual pipelines
- **Developer-only** modifications → **Anyone** can adjust
- **Hidden** processing logic → **Transparent** visual flows
- **Fixed** pipelines → **A/B testable** variations

This makes your unlimited-source architecture even more powerful by allowing rapid experimentation and source-specific optimization without touching code.