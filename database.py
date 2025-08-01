# database.py - Enhanced Database Management for AI Knowledge Assistant
# Phase 2: Smart Memory - Advanced database features with categorization, analytics, and search

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import json

DATABASE_NAME = 'insights.db'

# Predefined categories with emojis and keywords for auto-categorization
CATEGORIES = {
    'Technical Breakthroughs 🚀': ['breakthrough', 'innovation', 'novel', 'advancement', 'discovery', 'research', 'technology', 'AI', 'machine learning', 'algorithm'],
    'Market Trends 📈': ['market', 'trend', 'growth', 'adoption', 'demand', 'industry', 'sector', 'business', 'commercial', 'revenue'],
    'Investment/M&A 💰': ['investment', 'funding', 'acquisition', 'merger', 'venture', 'capital', 'IPO', 'valuation', 'financial', 'money'],
    'Regulatory 🏛️': ['regulation', 'policy', 'law', 'compliance', 'government', 'legal', 'regulatory', 'oversight', 'standards'],
    'Company Intelligence 🏢': ['company', 'startup', 'enterprise', 'organization', 'business', 'corporate', 'firm', 'vendor'],
    'Future Predictions 🔮': ['future', 'prediction', 'forecast', 'vision', 'roadmap', 'planning', 'strategy', 'outlook']
}

def get_connection():
    """Get database connection with proper configuration"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database with enhanced table structure"""
    conn = get_connection()
    cursor = conn.cursor()

    # Enhanced INSIGHTS table with new fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT,
            source_type TEXT NOT NULL,
            title TEXT,
            content TEXT,
            insights TEXT NOT NULL,
            summary TEXT,
            confidence_score REAL DEFAULT 0.5,
            word_count INTEGER DEFAULT 0,
            is_favorite BOOLEAN DEFAULT 0,
            is_archived BOOLEAN DEFAULT 0,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # CATEGORIES table for predefined categories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            emoji TEXT,
            description TEXT,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Enhanced TAGS table with confidence scores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight_id INTEGER,
            tag TEXT NOT NULL,
            confidence_score REAL DEFAULT 0.5,
            is_auto_generated BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY (insight_id) REFERENCES insights (id) ON DELETE CASCADE
        )
    ''')

    # Enhanced ENTITIES table with more detailed information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight_id INTEGER,
            entity_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_subtype TEXT,
            confidence_score REAL DEFAULT 0.5,
            sme_relevance BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY (insight_id) REFERENCES insights (id) ON DELETE CASCADE
        )
    ''')

    # ANALYTICS table for storing computed statistics
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            metric_value TEXT,
                         computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migrate existing database if needed
    migrate_database(cursor)

    # Insert predefined categories
    for category_name, keywords in CATEGORIES.items():
        emoji = category_name.split()[0]  # Extract emoji
        name = ' '.join(category_name.split()[1:])  # Extract name without emoji
        cursor.execute('''
            INSERT OR IGNORE INTO categories (name, emoji, description)
            VALUES (?, ?, ?)
        ''', (name, emoji, f"Auto-categorized insights related to {name.lower()}"))

    conn.commit()
    conn.close()

def migrate_database(cursor):
    """Migrate existing database to new schema"""
    try:
        # Check if insights table has new columns
        cursor.execute("PRAGMA table_info(insights)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add missing columns to insights table
        if 'summary' not in columns:
            cursor.execute('ALTER TABLE insights ADD COLUMN summary TEXT')
        
        if 'confidence_score' not in columns:
            cursor.execute('ALTER TABLE insights ADD COLUMN confidence_score REAL DEFAULT 0.5')
        
        if 'word_count' not in columns:
            cursor.execute('ALTER TABLE insights ADD COLUMN word_count INTEGER DEFAULT 0')
        
        if 'is_favorite' not in columns:
            cursor.execute('ALTER TABLE insights ADD COLUMN is_favorite BOOLEAN DEFAULT 0')
        
        if 'is_archived' not in columns:
            cursor.execute('ALTER TABLE insights ADD COLUMN is_archived BOOLEAN DEFAULT 0')
        
        if 'category' not in columns:
            cursor.execute('ALTER TABLE insights ADD COLUMN category TEXT')
        
        # Check if tags table has new columns
        cursor.execute("PRAGMA table_info(tags)")
        tag_columns = [row[1] for row in cursor.fetchall()]
        
        if 'confidence_score' not in tag_columns:
            cursor.execute('ALTER TABLE tags ADD COLUMN confidence_score REAL DEFAULT 0.5')
        
        if 'is_auto_generated' not in tag_columns:
            cursor.execute('ALTER TABLE tags ADD COLUMN is_auto_generated BOOLEAN DEFAULT 0')
        
        if 'created_at' not in tag_columns:
            cursor.execute('ALTER TABLE tags ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        
        # Check if entities table has new columns
        cursor.execute("PRAGMA table_info(entities)")
        entity_columns = [row[1] for row in cursor.fetchall()]
        
        if 'entity_subtype' not in entity_columns:
            cursor.execute('ALTER TABLE entities ADD COLUMN entity_subtype TEXT')
        
        if 'confidence_score' not in entity_columns:
            cursor.execute('ALTER TABLE entities ADD COLUMN confidence_score REAL DEFAULT 0.5')
        
        if 'sme_relevance' not in entity_columns:
            cursor.execute('ALTER TABLE entities ADD COLUMN sme_relevance BOOLEAN DEFAULT 0')
        
        if 'created_at' not in entity_columns:
            cursor.execute('ALTER TABLE entities ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        
        print("Database migration completed successfully")
        
    except Exception as e:
        print(f"Migration error: {e}")
        # Continue anyway, the new tables will be created

def save_insight(source_url: str, source_type: str, content: str, insights: str, 
                         title: str = None, summary: str = None, confidence_score: float = 0.5) -> int:
    """Save a new insight with enhanced metadata"""
    
    conn = get_connection()
    cursor = conn.cursor()

    # Calculate word count
    word_count = len(content.split()) if content else 0

    # Insert insight with new fields
    cursor.execute('''
        INSERT INTO insights (source_url, source_type, title, content, insights, 
                         summary, confidence_score, word_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (source_url, source_type, title, content, insights, summary, confidence_score, word_count))

    insight_id = cursor.lastrowid

    # Auto-categorize the insight
    if insights:
        auto_categorize_insight(cursor, insight_id, insights)

    conn.commit()
    conn.close()

    return insight_id

def auto_categorize_insight(cursor, insight_id: int, insights_text: str):
    """Auto-categorize insight based on keyword matching"""
    insights_lower = insights_text.lower()
    
    best_category = None
    best_score = 0
    
    for category_name, keywords in CATEGORIES.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in insights_lower:
                score += 1
        
        if score > best_score:
            best_score = score
            best_category = category_name.split()[1:]  # Remove emoji
            best_category = ' '.join(best_category)
    
    if best_category and best_score > 0:
        cursor.execute('''
            UPDATE insights SET category = ? WHERE id = ?
        ''', (best_category, insight_id))

def get_all_insights(limit: Optional[int] = None, category: Optional[str] = None, 
                         favorite_only: bool = False, archived: bool = False) -> List[Dict[str, Any]]:
    """Get insights with advanced filtering"""
    # Input validation for limit parameter
    if limit is not None:
        try:
            limit = int(limit)
            if limit < 0:
                limit = 20  # Default to safe limit
        except (ValueError, TypeError):
            limit = 20  # Default to safe limit
    
    conn = get_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM insights WHERE 1=1'
    params = []

    if category:
        query += ' AND category = ?'
        params.append(category)
    
    if favorite_only:
        query += ' AND is_favorite = 1'
    
    if not archived:
        query += ' AND is_archived = 0'

    query += ' ORDER BY created_at DESC'
    
    if limit:
        query += ' LIMIT ?'
        params.append(limit)

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]

def get_insight_by_id(insight_id: int) -> Optional[Dict[str, Any]]:
    """Get specific insight by ID with related data"""
    # Input validation for insight_id parameter
    try:
        insight_id = int(insight_id)
        if insight_id < 0:
            return None
    except (ValueError, TypeError):
        return None
    
    conn = get_connection()
    cursor = conn.cursor()

    # Get insight
    cursor.execute('SELECT * FROM insights WHERE id = ?', (insight_id,))
    insight = cursor.fetchone()

    if not insight:
        conn.close()
        return None

    insight_dict = dict(insight)

    # Get tags
    cursor.execute('SELECT tag, confidence_score, is_auto_generated FROM tags WHERE insight_id = ?', (insight_id,))
    tags = [dict(row) for row in cursor.fetchall()]
    insight_dict['tags'] = tags

    # Get entities
    cursor.execute('SELECT entity_name, entity_type, entity_subtype, confidence_score, sme_relevance FROM entities WHERE insight_id = ?', (insight_id,))
    entities = [dict(row) for row in cursor.fetchall()]
    insight_dict['entities'] = entities

    conn.close()
    return insight_dict

def search_insights(query: str, category: Optional[str] = None, 
                   date_from: Optional[str] = None, date_to: Optional[str] = None,
                         entity: Optional[str] = None) -> List[Dict[str, Any]]:
    """Advanced search with multiple filters"""
    conn = get_connection()
    cursor = conn.cursor()

    # Build complex search query
    search_query = '''
        SELECT DISTINCT i.* FROM insights i
        LEFT JOIN tags t ON i.id = t.insight_id
        LEFT JOIN entities e ON i.id = e.insight_id
        WHERE (i.title LIKE ? OR i.content LIKE ? OR i.insights LIKE ? 
               OR t.tag LIKE ? OR e.entity_name LIKE ?)
    '''
    params = [f'%{query}%'] * 5

    if category:
        search_query += ' AND i.category = ?'
        params.append(category)

    if date_from:
        search_query += ' AND DATE(i.created_at) >= ?'
        params.append(date_from)

    if date_to:
        search_query += ' AND DATE(i.created_at) <= ?'
        params.append(date_to)

    if entity:
        search_query += ' AND e.entity_name = ?'
        params.append(entity)

    search_query += ' ORDER BY i.created_at DESC'

    cursor.execute(search_query, params)
    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]

def get_insights_by_category(category_name: str) -> List[Dict[str, Any]]:
    """Get all insights in a specific category"""
    return get_all_insights(category=category_name)

def get_insights_by_entity(entity_name: str) -> List[Dict[str, Any]]:
    """Get all insights mentioning a specific entity"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT i.* FROM insights i
        JOIN entities e ON i.id = e.insight_id
        WHERE e.entity_name = ?
        ORDER BY i.created_at DESC
    ''', (entity_name,))

    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]

def update_insight_favorite(insight_id: int, is_favorite: bool) -> bool:
    """Toggle favorite status of an insight"""
    # Input validation for insight_id parameter
    try:
        insight_id = int(insight_id)
        if insight_id < 0:
            return False
    except (ValueError, TypeError):
        return False
    
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE insights SET is_favorite = ? WHERE id = ?
        ''', (1 if is_favorite else 0, insight_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating favorite status: {e}")
        conn.close()
        return False

def add_tag_to_insight(insight_id: int, tag: str, confidence_score: float = 0.5, 
                         is_auto_generated: bool = False) -> bool:
    """Add a tag to an insight"""
    # Input validation
    try:
        insight_id = int(insight_id)
        if insight_id < 0:
            return False
    except (ValueError, TypeError):
        return False
    
    # Validate tag input
    if not tag or len(tag.strip()) == 0 or len(tag) > 100:
        return False
    
    # Validate confidence score
    try:
        confidence_score = float(confidence_score)
        if confidence_score < 0 or confidence_score > 1:
            confidence_score = 0.5
    except (ValueError, TypeError):
        confidence_score = 0.5
    
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO tags (insight_id, tag, confidence_score, is_auto_generated)
            VALUES (?, ?, ?, ?)
        ''', (insight_id, tag, confidence_score, is_auto_generated))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding tag: {e}")
        conn.close()
        return False

def save_entities_for_insight(insight_id: int, entities: List[Dict[str, Any]]) -> bool:
    """Save extracted entities for an insight"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        for entity in entities:
            cursor.execute('''
                INSERT INTO entities (insight_id, entity_name, entity_type, entity_subtype, 
                         confidence_score, sme_relevance)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                insight_id,
                entity.get('name', ''),
                entity.get('type', ''),
                entity.get('subtype', ''),
                entity.get('confidence', 0.5),
                entity.get('sme_relevance', False)
            ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving entities: {e}")
        conn.close()
        return False

def get_analytics_summary() -> Dict[str, Any]:
    """Get comprehensive analytics summary"""
    conn = get_connection()
    cursor = conn.cursor()

    analytics = {}

    # Total insights
    cursor.execute('SELECT COUNT(*) FROM insights')
    analytics['total_insights'] = cursor.fetchone()[0]

    # Insights this week
    week_ago = datetime.now() - timedelta(days=7)
    cursor.execute('SELECT COUNT(*) FROM insights WHERE created_at >= ?', (week_ago,))
    analytics['insights_this_week'] = cursor.fetchone()[0]

    # Category distribution
    cursor.execute('''
        SELECT category, COUNT(*) as count 
        FROM insights 
        WHERE category IS NOT NULL 
        GROUP BY category 
        ORDER BY count DESC
    ''')
    analytics['category_distribution'] = [dict(row) for row in cursor.fetchall()]

    # Popular tags
    cursor.execute('''
        SELECT tag, COUNT(*) as count 
        FROM tags 
        GROUP BY tag 
        ORDER BY count DESC 
        LIMIT 10
    ''')
    analytics['popular_tags'] = [dict(row) for row in cursor.fetchall()]

    # Popular entities
    cursor.execute('''
        SELECT entity_name, entity_type, COUNT(*) as count 
        FROM entities 
        GROUP BY entity_name 
        ORDER BY count DESC 
        LIMIT 10
    ''')
    analytics['popular_entities'] = [dict(row) for row in cursor.fetchall()]

    # Average confidence score
    cursor.execute('SELECT AVG(confidence_score) FROM insights')
    avg_confidence = cursor.fetchone()[0]
    analytics['avg_confidence'] = round(avg_confidence, 2) if avg_confidence else 0

    conn.close()
    return analytics

def get_popular_tags(limit: int = 20) -> List[Dict[str, Any]]:
    """Get most popular tags"""
    # Input validation for limit parameter
    try:
        limit = int(limit)
        if limit < 0 or limit > 1000:  # Reasonable upper bound
            limit = 20
    except (ValueError, TypeError):
        limit = 20
    
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT tag, COUNT(*) as count 
        FROM tags 
        GROUP BY tag 
        ORDER BY count DESC 
        LIMIT ?
    ''', (limit,))

    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]

def get_popular_entities(limit: int = 20) -> List[Dict[str, Any]]:
    """Get most popular entities"""
    # Input validation for limit parameter
    try:
        limit = int(limit)
        if limit < 0 or limit > 1000:  # Reasonable upper bound
            limit = 20
    except (ValueError, TypeError):
        limit = 20
    
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT entity_name, entity_type, COUNT(*) as count 
        FROM entities 
        GROUP BY entity_name 
        ORDER BY count DESC 
        LIMIT ?
    ''', (limit,))

    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]

def get_categories() -> List[Dict[str, Any]]:
    """Get all available categories"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM categories ORDER BY name')
    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]

def export_insights(format: str = 'json', filters: Dict[str, Any] = None) -> str:
    """Export insights in specified format with optional filters"""
    conn = get_connection()
    cursor = conn.cursor()

    # Build query based on filters
    query = 'SELECT * FROM insights WHERE 1=1'
    params = []

    if filters:
        if filters.get('category'):
            query += ' AND category = ?'
            params.append(filters['category'])
        
        if filters.get('date_from'):
            query += ' AND DATE(created_at) >= ?'
            params.append(filters['date_from'])
        
        if filters.get('date_to'):
            query += ' AND DATE(created_at) <= ?'
            params.append(filters['date_to'])
        
        if filters.get('favorite_only'):
            query += ' AND is_favorite = 1'

    query += ' ORDER BY created_at DESC'

    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if format.lower() == 'json':
        return json.dumps(results, indent=2, default=str)
    elif format.lower() == 'csv':
        if not results:
            return ''
        
        # Create CSV header
        headers = list(results[0].keys())
        csv_content = ','.join(headers) + '\n'
        
        # Add data rows
        for row in results:
            csv_content += ','.join([str(row.get(header, '')) for header in headers]) + '\n'
        
        return csv_content
    
    return ''