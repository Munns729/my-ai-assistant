# app.py - Main Application File for AI Knowledge Assistant
# This file creates a web server that handles all the web pages and user interactions

# === IMPORTS: Getting all the tools we need ===

import os  # Built-in Python library to access environment variables (like our secret API keys)

from flask import Flask, request, render_template, redirect, url_for, flash
# Flask: The web framework that creates our website
# request: Gets data from forms when users submit them
# render_template: Shows HTML pages to users
# redirect: Sends users to different pages automatically
# url_for: Creates links to other pages safely
# flash: Shows temporary messages like "Success!" or "Error!"

from dotenv import load_dotenv  # Safely reads our .env file where we store secret keys

import openai  # The library that talks to OpenAI's GPT models

from datetime import datetime  # Gets current date and time for timestamps

# Import our custom functions from other files we'll create
from database import init_database, save_insight, get_all_insights, search_insights, get_insight_by_id
# init_database: Sets up our database tables
# save_insight: Saves new insights to database
# get_all_insights: Gets all saved insights from database
# search_insights: Searches through insights
# get_insight_by_id: Gets a specific insight by its ID

from insights import extract_insights_from_text, get_video_info
# extract_insights_from_text: Sends content to AI and gets back insights
# get_video_info: Gets YouTube video details (we'll use this later)

# === SETUP: Preparing everything to work ===

load_dotenv()  # Read the .env file and load all the environment variables (API keys, etc.)

app = Flask(__name__)  # Create our Flask web application - this is the foundation of our website

app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')  # Secret key for security (change this to something random!)
# This is used to encrypt flash messages and session data

# Initialize OpenAI with our API key
openai_api_key = os.getenv('OPENAI_API_KEY')  # Get the OpenAI API key from environment variables
if not openai_api_key:
    print("Warning: OPENAI_API_KEY not found in environment variables")
else:
    # Set the API key globally for the old-style API calls
    openai.api_key = openai_api_key
# os.getenv() safely gets the key from our .env file without exposing it in the code

def initialize_app():
    """Initialize the application and database"""
    try:
        init_database()  # Calls our function that sets up the SQLite database structure
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")

# Initialize database - this creates the database tables if they don't exist yet
# We'll call this when the app starts

# === ROUTES: These define what happens when users visit different web pages ===

@app.route('/')  # This decorator means "when someone visits the root URL (localhost:5000/)"
def home():  # This function runs when someone visits the home page
    """
    HOME PAGE: Shows the main interface where users can input content to analyze
    """
    try:
        recent_insights = get_all_insights(limit=5)  # Get the 5 most recent insights from database
        # This gives users a preview of their recent work
    except Exception as e:
        print(f"Error getting recent insights: {e}")
        recent_insights = []
    
    return render_template('index.html', recent_insights=recent_insights)  
    # Show the index.html template and pass the recent insights to display on the page

@app.route('/analyze', methods=['POST'])  # This handles form submissions (POST requests)
def analyze_content():  # This function processes the content analysis form
    """
    ANALYSIS HANDLER: Takes user input, sends to AI, saves results
    This is where the magic happens!
    """
    
    # Get the type of content from the form (youtube, email, etc.)
    content_type = request.form.get('content_type')  # request.form gets data from HTML form
    
    if content_type == 'youtube':  # If user is analyzing YouTube content
        
        # Get the YouTube URL from the form (optional)
        video_url = request.form.get('video_url')  # The YouTube link user provided
        
        # Get the actual content to analyze (required)
        manual_content = request.form.get('manual_content')  # The text user pasted
        
        # Check if user actually provided content to analyze
        if not manual_content:  # If the content field is empty
            flash('Please provide video content to analyze', 'error')  # Show error message to user
            return redirect(url_for('home'))  # Send them back to home page
        
        # 🤖 THE AI MAGIC HAPPENS HERE 🤖
        # Send the content to OpenAI and get back structured insights
        try:
            insights = extract_insights_from_text(manual_content, source_type='youtube')
            # This function (defined in insights.py) does the AI analysis
        except Exception as e:
            print(f"Error analyzing content: {e}")
            flash('Error analyzing content. Please try again.', 'error')
            return redirect(url_for('home'))
        
        # Save everything to our database for future reference
        try:
            insight_id = save_insight(
                source_url=video_url,  # The YouTube URL (can be empty)
                source_type='youtube',  # What type of content this is
                content=manual_content,  # The original text they pasted
                insights=insights,  # The AI-generated insights
                title=f"YouTube Video Analysis - {datetime.now().strftime('%Y-%m-%d')}"  # Auto-generated title with today's date
            )
            # save_insight() returns the ID of the newly created database record
        except Exception as e:
            print(f"Error saving insight: {e}")
            flash('Error saving insight. Please try again.', 'error')
            return redirect(url_for('home'))
        
        flash('Successfully analyzed content!')  # Show success message
        return redirect(url_for('view_insight', insight_id=insight_id))  # Go to the results page
        # This sends user to see their new insights
    
    # If we get here, something went wrong or content_type wasn't 'youtube'
    return redirect(url_for('home'))  # Send user back to home page

@app.route('/insights')  # When someone visits /insights
def view_all_insights():  # This function shows all saved insights
    """
    INSIGHTS LIBRARY: Shows all the insights user has collected over time
    Like a personal knowledge base
    """
    try:
        insights = get_all_insights()  # Get ALL insights from database (no limit)
    except Exception as e:
        print(f"Error getting all insights: {e}")
        insights = []
        flash('Error loading insights', 'error')
    
    return render_template('insights.html', insights=insights)  # Show the insights page with all data

@app.route('/insights/<int:insight_id>')  # Dynamic URL - <int:insight_id> captures a number from URL
def view_insight(insight_id):  # This function shows one specific insight in detail
    """
    SINGLE INSIGHT VIEW: Shows detailed view of one insight
    URL example: /insights/123 (where 123 is the insight_id)
    """
    try:
        insight = get_insight_by_id(insight_id)  # Look up this specific insight in database
    except Exception as e:
        print(f"Error getting insight {insight_id}: {e}")
        flash('Error loading insight', 'error')
        return redirect(url_for('home'))
    
    if not insight:  # If insight doesn't exist (maybe wrong ID or deleted)
        flash('Insight not found', 'error')  # Show error message
        return redirect(url_for('home'))  # Send back to home page
    
    return render_template('single_insight.html', insight=insight)  # Show detailed insight page

@app.route('/search')  # When someone visits /search (usually with ?q=searchterm)
def search():  # This function handles searching through insights
    """
    SEARCH FUNCTIONALITY: Lets users search through all their saved insights
    URL example: /search?q=OpenAI (searches for "OpenAI")
    """
    query = request.args.get('q', '')  # Get search term from URL parameters
    # request.args gets data from URL (like ?q=OpenAI)
    # The '' means if no 'q' parameter exists, use empty string
    
    results = []  # Start with empty results list
    
    if query:  # Only search if user actually entered something
        try:
            results = search_insights(query)  # Search database for matching insights
        except Exception as e:
            print(f"Error searching insights: {e}")
            flash('Error searching insights', 'error')
    
    return render_template('search_results.html', query=query, results=results)
    # Show search results page, passing both the search term and results
# === START THE SERVER ===

if __name__ == '__main__':  # This only runs if we execute this file directly (not if imported)
    # This is Python's way of saying "only run this if this is the main program"
    
    # Initialize the application
    initialize_app()
    
    app.run(debug=True, host='127.0.0.1', port=5000)
    # Start the Flask web server
    # debug=True: Shows detailed errors and auto-restarts when code changes
    # host='127.0.0.1': Only accessible from this computer (localhost)
    # port=5000: The server runs on port 5000 (so URL is http://127.0.0.1:5000)

# === HOW THIS ALL WORKS TOGETHER ===
#
# 1. User visits http://127.0.0.1:5000 → home() function runs → shows main page
# 2. User pastes content and clicks submit → analyze_content() runs → AI analyzes → saves to DB
# 3. User clicks "View Insights" → view_all_insights() runs → shows all saved insights
# 4. User clicks on specific insight → view_insight() runs → shows detailed view
# 5. User searches for something → search() runs → finds and shows matching insights
#
# Each function is like a different "page" or "action" on your website!

# === WHAT YOU'LL SEE WHEN RUNNING ===
#
# In terminal: 
# * Running on http://127.0.0.1:5000
# * Debug mode: on
#
# In browser:
# - Main page with form to paste content
# - After submitting: Success message and your AI insights!
# - Navigation to see all your insights
# - Search functionality to find specific topics
#
# This creates a complete web application for your personal AI knowledge assistant!