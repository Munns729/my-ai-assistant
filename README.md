# 🤖 AI Knowledge Assistant

A powerful Flask web application that uses OpenAI's GPT models to analyze content and extract valuable insights from AI Engineer videos, articles, and other sources.

## ✨ Features

- **AI-Powered Analysis**: Uses OpenAI GPT-3.5-turbo to extract structured insights
- **Content Processing**: Analyzes YouTube videos, articles, emails, and general content
- **Insight Categories**: 
  - 🚀 Technical Breakthroughs
  - 📈 Market Trends
  - 💰 Investment/M&A Opportunities
  - 🏛️ Regulatory Insights
  - 🏢 Company Intelligence
  - 🔮 Future Predictions
- **Database Storage**: SQLite database to save and search insights
- **Modern UI**: Clean, responsive interface with Tailwind CSS
- **Search Functionality**: Find insights by keywords
- **Error Handling**: Comprehensive error reporting and user feedback

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Munns729/my-ai-assistant.git
   cd my-ai-assistant
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   SECRET_KEY=your_secret_key_here
   DATABASE_URL=sqlite:///ai_assistant.db
   DEBUG=True
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open your browser**
   Navigate to `http://127.0.0.1:5000`

## 🎯 How to Use

### Basic Workflow
1. **Find Content**: Locate an AI Engineer video or article
2. **Copy Key Points**: Extract important content from description/comments
3. **Paste & Analyze**: Paste content into the web interface
4. **Get Insights**: Click "🤖 Analyze with AI" to generate insights
5. **Review Results**: View structured insights and save for later

### Example Use Cases
- **YouTube Analysis**: Copy video descriptions and comments for AI insights
- **Article Processing**: Analyze tech articles for business opportunities
- **Email Analysis**: Extract insights from industry newsletters
- **Research Synthesis**: Combine multiple sources for comprehensive analysis

## 🏗️ Project Structure

```
my-ai-assistant/
├── app.py                 # Main Flask application
├── database.py            # Database operations and models
├── insights.py            # AI analysis functions
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in repo)
├── .gitignore            # Git ignore rules
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Main page
│   ├── insights.html     # All insights view
│   ├── single_insight.html # Individual insight view
│   └── search_results.html # Search results
└── static/               # CSS and static files
    └── style.css         # Custom styles
```

## 🔧 Configuration

### Environment Variables
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `SECRET_KEY`: Flask secret key for sessions
- `DATABASE_URL`: Database connection string
- `DEBUG`: Enable debug mode (True/False)

### Database
The application uses SQLite by default. The database file (`insights.db`) is created automatically on first run.

## 🛠️ Development

### Running in Development Mode
```bash
python app.py
```
The app will run on `http://127.0.0.1:5000` with auto-reload enabled.

### Making Changes
1. Edit the code
2. Flask will auto-reload
3. Test your changes
4. Commit to Git: `git add . && git commit -m "Description"`

### Process Hygiene
Before starting development:
```bash
# Check for existing processes
tasklist | findstr python

# Kill if needed
taskkill /f /im python.exe

# Start fresh
python app.py
```

## 🐛 Troubleshooting

### Common Issues

**"Client.__init__() got an unexpected keyword argument 'proxies'"**
- Solution: Kill all Python processes and restart
- Root cause: Multiple Flask instances running

**"OpenAI API key not found"**
- Solution: Check your `.env` file has the correct API key

**"Database error"**
- Solution: Delete `insights.db` and restart (database will be recreated)

### Error Reporting
The application includes detailed error reporting:
- Full tracebacks in terminal
- User-friendly error messages on web interface
- Red error bars for failures, green for success

## 📊 Features in Detail

### AI Analysis
- **Content Processing**: Handles text up to 3000 characters
- **Structured Output**: Categorizes insights by type
- **Confidence Scoring**: High/Medium/Low confidence levels
- **Action Items**: Implementation/Investment/Research/Monitor recommendations

### Database Features
- **Insight Storage**: Save all analyses with metadata
- **Search Functionality**: Find insights by keywords
- **Recent Insights**: Show latest analyses on home page
- **Source Tracking**: Link insights to original content

### Web Interface
- **Responsive Design**: Works on desktop and mobile
- **Real-time Feedback**: Immediate success/error messages
- **Navigation**: Easy access to all features
- **Search**: Find specific insights quickly

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Commit: `git commit -m "Add feature"`
5. Push: `git push origin feature-name`
6. Create a Pull Request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- **OpenAI** for providing the GPT API
- **Flask** for the web framework
- **Tailwind CSS** for styling
- **AI Engineer** community for inspiration

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the error messages in your terminal
3. Ensure all dependencies are installed
4. Verify your OpenAI API key is valid

---

**Happy analyzing! 🚀** 