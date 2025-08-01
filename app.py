# app.py - Enhanced Main Application File for AI Knowledge Assistant
# Phase 2: Smart Memory - Advanced features with analytics, categorization, and export

import os
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from dotenv import load_dotenv
import openai
from datetime import datetime
import json

# Import enhanced database functions
from database import (
    init_database, save_insight, get_all_insights, search_insights, get_insight_by_id,
    get_analytics_summary, get_popular_tags, get_popular_entities, get_categories,
    get_insights_by_category, get_insights_by_entity, update_insight_favorite,
    save_entities_for_insight, export_insights
)

from insights import extract_insights_from_text, extract_entities_from_insights, get_video_info

# === SETUP: Preparing everything to work ===

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# Initialize OpenAI with our API key
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    print("Warning: OPENAI_API_KEY not found in environment variables")
else:
    openai.api_key = openai_api_key

def initialize_app():
    """Initialize the application and database"""
    try:
        init_database()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")

# === ENHANCED ROUTES: New and improved functionality ===

@app.route('/')
def home():
    """HOME PAGE: Enhanced with analytics and recent insights"""
    try:
        # Get recent insights with enhanced data
        recent_insights = get_all_insights(limit=5)
        
        # Get quick analytics for dashboard
        analytics = get_analytics_summary()
        
        # Get popular tags for sidebar
        popular_tags = get_popular_tags(limit=10)
        
        # Get categories for filtering
        categories = get_categories()
        
    except Exception as e:
        print(f"Error loading home page data: {e}")
        recent_insights = []
        analytics = {}
        popular_tags = []
        categories = []
        flash('Error loading data', 'error')
    
    return render_template('index.html',
                         recent_insights=recent_insights,
                         analytics=analytics,
                         popular_tags=popular_tags,
                         categories=categories)

@app.route('/analyze', methods=['POST'])
def analyze_content():
    """ENHANCED ANALYSIS: Now includes entity extraction and categorization"""
    
    content_type = request.form.get('content_type')
    
    if content_type == 'youtube':
        video_url = request.form.get('video_url')
        manual_content = request.form.get('manual_content')
        
        if not manual_content:
            flash('Please provide video content to analyze', 'error')
            return redirect(url_for('home'))
        
        # 🤖 ENHANCED AI ANALYSIS 🤖
        try:
            # Extract insights from content
            insights = extract_insights_from_text(manual_content, source_type='youtube')
            
            # Extract entities from insights
            entities = extract_entities_from_insights(insights)
            
        except Exception as e:
            print(f"Error analyzing content: {e}")
            flash('Error analyzing content. Please try again.', 'error')
            return redirect(url_for('home'))
        
        # Save everything to database with enhanced metadata
        try:
            # Calculate confidence score based on content length and quality
            confidence_score = min(0.9, max(0.3, len(manual_content) / 1000))
            
            insight_id = save_insight(
                source_url=video_url,
                source_type='youtube',
                content=manual_content,
                insights=insights,
                         title=f"YouTube Video Analysis - {datetime.now().strftime('%Y-%m-%d')}",
                summary=insights[:200] + "..." if len(insights) > 200 else insights,
                confidence_score=confidence_score
            )
            
            # Save extracted entities
            if entities:
                save_entities_for_insight(insight_id, entities)
            
        except Exception as e:
            print(f"Error saving insight: {e}")
            flash('Error saving insight. Please try again.', 'error')
            return redirect(url_for('home'))
        
        flash('Successfully analyzed content!', 'success')
        return redirect(url_for('view_insight', insight_id=insight_id))
    
    return redirect(url_for('home'))

@app.route('/insights')
def view_all_insights():
    """ENHANCED INSIGHTS LIBRARY: With filtering and categorization"""
    try:
        # Get filter parameters
        category = request.args.get('category')
        favorite_only = request.args.get('favorite') == 'true'
        search_query = request.args.get('q', '')
        
        if search_query:
            insights = search_insights(search_query, category=category)
        else:
            insights = get_all_insights(category=category, favorite_only=favorite_only)
        
        # Get categories for filter sidebar
        categories = get_categories()
        
        # Get popular tags for sidebar
        popular_tags = get_popular_tags(limit=15)
        
    except Exception as e:
        print(f"Error getting insights: {e}")
        insights = []
        categories = []
        popular_tags = []
        flash('Error loading insights', 'error')
    
    return render_template('insights.html', 
                         insights=insights,
                         categories=categories,
                         popular_tags=popular_tags,
                         current_category=category,
                         favorite_only=favorite_only,
                         search_query=search_query)

@app.route('/insights/<int:insight_id>')
def view_insight(insight_id):
    """ENHANCED SINGLE INSIGHT VIEW: With tags, entities, and favorite toggle"""
    try:
        insight = get_insight_by_id(insight_id)
    except Exception as e:
        print(f"Error getting insight {insight_id}: {e}")
        flash('Error loading insight', 'error')
        return redirect(url_for('home'))
    
    if not insight:
        flash('Insight not found', 'error')
        return redirect(url_for('home'))
    
    return render_template('single_insight.html', insight=insight)

@app.route('/search')
def search():
    """ENHANCED SEARCH: With advanced filtering options"""
    query = request.args.get('q', '')
    category = request.args.get('category')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    entity = request.args.get('entity')
    
    results = []
    
    if query or category or date_from or date_to or entity:
        try:
            results = search_insights(query, category=category, 
                         date_from=date_from, date_to=date_to, entity=entity)
        except Exception as e:
            print(f"Error searching insights: {e}")
            flash('Error searching insights', 'error')
    
    # Get filter options
    try:
        categories = get_categories()
        popular_entities = get_popular_entities(limit=20)
    except Exception as e:
        print(f"Error loading search filters: {e}")
        categories = []
        popular_entities = []
    
    return render_template('search_results.html', 
                         query=query,
                         results=results,
                         categories=categories,
                         popular_entities=popular_entities,
                         current_filters={
                             'category': category,
                             'date_from': date_from,
                             'date_to': date_to,
                         'entity': entity
                         })

# === NEW ROUTES: Phase 2 enhancements ===

@app.route('/analytics')
def analytics():
    """ANALYTICS DASHBOARD: Comprehensive insights and statistics"""
    try:
        # Get comprehensive analytics
        analytics_data = get_analytics_summary()
        
        # Get popular tags and entities
        popular_tags = get_popular_tags(limit=20)
        popular_entities = get_popular_entities(limit=20)
        
        # Get category distribution
        categories = get_categories()
        
        # Get recent insights for the activity section
        recent_insights = get_all_insights(limit=5)
        
    except Exception as e:
        print(f"Error loading analytics: {e}")
        analytics_data = {}
        popular_tags = []
        popular_entities = []
        categories = []
        recent_insights = []
        flash('Error loading analytics', 'error')
    
    return render_template('analytics.html',
                         analytics=analytics_data,
                         popular_tags=popular_tags,
                         popular_entities=popular_entities,
                         categories=categories,
                         recent_insights=recent_insights)

@app.route('/categories/<category_name>')
def category_insights(category_name):
    """CATEGORY VIEW: Show all insights in a specific category"""
    try:
        insights = get_insights_by_category(category_name)
        categories = get_categories()
        
        # Find current category details
        current_category = next((cat for cat in categories if cat['name'] == category_name), None)
        
    except Exception as e:
        print(f"Error loading category insights: {e}")
        insights = []
        categories = []
        current_category = None
        flash('Error loading category insights', 'error')
    
    return render_template('category_insights.html',
                         insights=insights,
                         category=current_category,
                         categories=categories)

@app.route('/entities/<entity_name>')
def entity_insights(entity_name):
    """ENTITY VIEW: Show all insights mentioning a specific entity"""
    try:
        insights = get_insights_by_entity(entity_name)
        popular_entities = get_popular_entities(limit=20)
        
    except Exception as e:
        print(f"Error loading entity insights: {e}")
        insights = []
        popular_entities = []
        flash('Error loading entity insights', 'error')
    
    return render_template('entity_insights.html',
                         insights=insights,
                         entity_name=entity_name,
                         popular_entities=popular_entities)

@app.route('/export')
def export_page():
    """EXPORT PAGE: Interface for exporting insights with filters"""
    try:
        categories = get_categories()
        popular_tags = get_popular_tags(limit=15)
    except Exception as e:
        print(f"Error loading export page data: {e}")
        categories = []
        popular_tags = []
    
    return render_template('export.html',
                         categories=categories,
                         popular_tags=popular_tags)

@app.route('/api/insights/<int:insight_id>/favorite', methods=['POST'])
def toggle_favorite(insight_id):
    """AJAX ENDPOINT: Toggle favorite status of an insight"""
    try:
        data = request.get_json()
        is_favorite = data.get('is_favorite', False)
        
        success = update_insight_favorite(insight_id, is_favorite)
        
        if success:
            return jsonify({
                'success': True,
                'is_favorite': is_favorite,
                         'message': 'Favorite status updated'
            })
        else:
            return jsonify({
                'success': False,
                         'message': 'Error updating favorite status'
            }), 500
            
    except Exception as e:
        print(f"Error toggling favorite: {e}")
        return jsonify({
            'success': False,
                         'message': 'Server error'
        }), 500

@app.route('/api/export', methods=['POST'])
def api_export():
    """API ENDPOINT: Export insights in specified format"""
    try:
        data = request.get_json()
        export_format = data.get('format', 'json')
        filters = data.get('filters', {})
        
        # Validate format
        if export_format not in ['json', 'csv']:
            return jsonify({'error': 'Invalid format'}), 400
        
        # Export insights
        exported_data = export_insights(format=export_format, filters=filters)
        
        return jsonify({
            'success': True,
            'data': exported_data,
                         'format': export_format
        })
        
    except Exception as e:
        print(f"Error exporting insights: {e}")
        return jsonify({
            'success': False,
                         'message': 'Error exporting insights'
        }), 500

# === START THE SERVER ===

if __name__ == '__main__':
    initialize_app()
    app.run(debug=True, host='127.0.0.1', port=5000)