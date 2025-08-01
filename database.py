# database.py - Handles all interactions with the SQLite database
# This file manages storing, retrieving, and searching AI-generated insights

# === IMPORTS: Tools we need ===

import sqlite3  # Built-in library to work with SQLite databases (a lightweight file-based database)
from datetime import datetime  # Used to get timestamps for when things are created or updated
from typing import List, Dict, Any, Optional  
# These help us write cleaner and safer code by defining the expected types of data we work with

# === CONSTANTS: Things that don't change ===

DATABASE_NAME = 'insights.db'  
# This is the name of our SQLite database file (it will be created if it doesn’t exist)

# === DATABASE CONNECTION ===

def get_connection():
    """Get database connection"""
    # Connects to the SQLite database file (creates it if it doesn't exist)
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Allows us to treat rows like dictionaries (e.g., row['title'])
    return conn

# === SETUP: Create all necessary tables ===

def init_database():
    """Initialize database with required tables"""
    conn = get_connection()
    cursor = conn.cursor()  # Cursor allows us to run SQL commands

    # INSIGHTS TABLE: Stores the original content and AI-generated insights
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT,
            source_type TEXT NOT NULL,
            title TEXT,
            content TEXT,
            insights TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # TAGS TABLE: Allows tagging insights with keywords (like categories or topics)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight_id INTEGER,
            tag TEXT NOT NULL,
            FOREIGN KEY (insight_id) REFERENCES insights (id)
        )
    ''')

    # ENTITIES TABLE: Stores named entities like people, companies, or technologies
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight_id INTEGER,
            entity_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            FOREIGN KEY (insight_id) REFERENCES insights (id)
        )
    ''')

    conn.commit()  # Save (commit) the changes to the database
    conn.close()  # Close the connection to free up resources

# === FUNCTION: Save a new insight to the database ===

def save_insight(source_url: str, source_type: str, content: str,
                insights: str, title: str = None) -> int:
    """Save a new insight to database"""
    
    conn = get_connection()
    cursor = conn.cursor()

    # Insert a new row into the insights table with all provided values
    cursor.execute('''
        INSERT INTO insights (source_url, source_type, title, content, insights)
        VALUES (?, ?, ?, ?, ?)
    ''', (source_url, source_type, title, content, insights))

    insight_id = cursor.lastrowid  # Get the ID of the newly inserted insight
    conn.commit()
    conn.close()

    return insight_id  # Return the ID so we can link to or retrieve it later

# === FUNCTION: Get all saved insights ===

def get_all_insights(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all insights, optionally limited"""
    conn = get_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM insights ORDER BY created_at DESC'  # Show newest insights first
    if limit:
        query += f' LIMIT {limit}'  # If a limit is given, only get that many records

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]  # Convert results into list of dictionaries

# === FUNCTION: Get a specific insight by its ID ===

def get_insight_by_id(insight_id: int) -> Optional[Dict[str, Any]]:
    """Get specific insight by ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM insights WHERE id = ?', (insight_id,))
    result = cursor.fetchone()
    conn.close()

    return dict(result) if result else None  # Return result as dict, or None if not found

# === FUNCTION: Search for insights by keyword ===

def search_insights(query: str) -> List[Dict[str, Any]]:
    """Search insights by content"""
    conn = get_connection()
    cursor = conn.cursor()

    # Search title, content, and AI insights fields for anything matching the query string
    cursor.execute('''
        SELECT * FROM insights
        WHERE title LIKE ? OR content LIKE ? OR insights LIKE ?
        ORDER BY created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%'))  # % means "anything before/after" the query

    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]  # Return list of matching insights as dictionaries