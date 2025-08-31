# Expense Bot

A powerful Telegram bot that automatically logs expenses to Google Sheets with intelligent categorization, reminders, and comprehensive expense tracking features.

## ⚠️ Security Notice

**IMPORTANT**: This repository contains example configuration files only. Before using this bot, you must set up your own credentials and environment variables. See [docs/SECURITY.md](docs/SECURITY.md) for detailed security setup instructions.

## 🚀 Features

### Core Functionality
- 📊 **Automatic Expense Logging**: Direct integration with Google Sheets for real-time expense tracking
- 🤖 **Smart Categorization**: AI-powered expense categorization using fuzzy matching and keyword detection
- 📱 **Multi-format Input**: Support for single-line and multi-line expense entries
- 👥 **Multi-user Support**: Secure user authentication with configurable access control

### Expense Management
- 📅 **Daily Summaries**: Get comprehensive daily expense reports with totals
- 📊 **Visual Charts**: Generate beautiful expense breakdown charts with category-wise analysis
- 🔍 **Expense Search**: Find and analyze expenses by category, date, or description
- 💰 **Amount Calculations**: Support for mathematical expressions (e.g., "Coffee 50+25+30")

### Smart Reminders
- ⏰ **Recurring Expense Reminders**: Automated notifications for regular expenses (rent, utilities, etc.)
- 💳 **Credit Card Reminders**: Smart payment due date notifications with amount tracking
- 📆 **Date-based Alerts**: Configurable reminder periods and date ranges
- 🔔 **Daily Motivation**: Friendly nudges when no expenses are logged

### Advanced Features
- 🔄 **Auto-refresh Categories**: Dynamic learning from your expense patterns
- 📈 **Monthly Tracking**: Automatic sheet creation and month-wise organization
- 🎯 **Fuzzy Matching**: Intelligent expense recognition even with typos
- 🔐 **Secure Webhooks**: Token-based authentication for all API endpoints

## 🛠️ Setup

### Prerequisites

- **Python 3.8+** (Recommended: Python 3.10+)
- **Google Cloud Platform account** (for production deployment)
- **Telegram Bot Token** from [@BotFather](https://t.me/botfather)
- **Google Sheets API credentials**
- **ngrok** (for local development) or cloud hosting platform

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone <your-repo-url>
cd expense_bot

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Security Setup (CRITICAL)

**⚠️ You MUST complete this step before running the bot:**

1. Read the [docs/SECURITY.md](docs/SECURITY.md) guide thoroughly
2. Set up your own Telegram bot with [@BotFather](https://t.me/botfather)
3. Configure Google API credentials and enable Google Sheets API
4. Set up environment variables as described below

### 3. Google Sheets Setup

1. **Create a Google Sheet** for your expenses with the following structure:
   ```
   Column B: Date (DD/MM/YYYY)
   Column C: Description  
   Column D: Amount
   Column E: Main Category
   Column F: Sub Category
   Column G: User
   Column H: Bot Identified (Yes/No)
   ```

2. **Share the sheet** with your service account email or ensure OAuth access
3. **Note the Sheet ID** from the URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`

### 4. Environment Configuration

#### For Local Development:

```bash
# Copy the example configuration
cp config.env.example config.env

# Edit config.env with your actual values:
local=true
bot_token=YOUR_TELEGRAM_BOT_TOKEN_HERE
webhook_url=YOUR_NGROK_URL  # e.g., https://abc123.ngrok-free.app
google_sheet_id=YOUR_GOOGLE_SHEET_ID
gcp_project_id=YOUR_GCP_PROJECT_ID
scheduler_token=YOUR_RANDOM_SECRET_TOKEN
ALLOWED_USER_IDS=123456789,987654321  # Your Telegram user IDs
ALLOWED_USER_NAMES=Alice,Bob          # Corresponding names
```

#### For Cloud Deployment:

```bash
# Copy and configure cloud environment
cp config_cloud.env.example config_cloud.env
# Set environment variables in your cloud platform
```

### 5. User Configuration

Find your Telegram User ID:
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Add your ID to `ALLOWED_USER_IDS` in the configuration

### 6. Running the Bot

#### Local Development with ngrok:

```bash
# Terminal 1: Start ngrok
ngrok http 8080

# Terminal 2: Run the bot
uvicorn bot:app --reload --host 0.0.0.0 --port 8080 --env-file config.env
```

#### Production Deployment:

Deploy to Google Cloud Run, Heroku, or your preferred platform with environment variables configured.

## 📱 Usage

### Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot interaction | `/start` |
| `/expense` | Start logging a new expense | `/expense` |
| `/summary` | Get today's expense summary | `/summary` |
| `/today` | Visual expense chart for today | `/today` |
| `/reminders` | Check active reminders | `/reminders` |
| `/refresh` | Update expense categories | `/refresh` |
| `/cancel` | Cancel current operation | `/cancel` |

### Expense Input Formats

#### Single Expense:
```
Coffee 150
Uber ride 350
Groceries from store 2500
```

#### Multiple Expenses:
```
Coffee 50
Lunch 200  
Bus fare 25
```

#### Mathematical Expressions:
```
Restaurant bill 500+50+75
Shopping 1200+300
```

### Smart Categorization Examples

The bot automatically categorizes expenses based on:

- **Keywords**: "coffee", "uber", "groceries" → Auto-categorized
- **Previous Patterns**: Similar descriptions from your history
- **Fuzzy Matching**: Handles typos and variations

Examples:
- "Starbucks coffee" → Food > Outside Food/Dining/Snacks
- "Big Bazaar groceries" → Household > Groceries  
- "Zomato order" → Food > Outside Food/Dining/Snacks

## 🔧 Configuration Files

### Core Files:
- `config.env.example` - Local development template
- `config_cloud.env.example` - Cloud deployment template
- `token.json.example` - OAuth token structure example

### Data Files:
- `types_data.json` - Learned expense categories
- `reminders.json` - Recurring expense reminders
- `keywords.json` - Keyword-based categorization rules

### Example Reminder Configuration (`reminders.json`):

```json
[
  {
    "desc": "House Rent",
    "main_type": "Household", 
    "sub_type": "Rent",
    "date_range": "1-5"
  },
  {
    "desc": "Internet Bill",
    "main_type": "Utilities",
    "sub_type": "Internet", 
    "date_range": "10-15"
  }
]
```

## 🎯 Advanced Features

### Webhook Endpoints:

- `GET /bot` - Bot status page
- `POST /bot` - Telegram webhook handler  
- `GET /reminders` - Trigger reminder notifications
- `GET /types_refresh` - Refresh expense categories

### Scheduled Jobs:

Set up cron jobs or cloud schedulers to call:
- `/reminders` - Daily at 6 PM for expense reminders
- `/types_refresh` - Daily at 11 PM for category updates

### Credit Card Tracking:

Configure credit card due dates in your Google Sheet:
- Sheet columns T-W for card details
- Automatic payment reminders 1 day before due date
- Status tracking (Paid/Unpaid)

## 🧪 Testing

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=html

# Run specific test file  
python -m pytest test_bot.py -v
```

## 🐳 Docker Deployment

```bash
# Build Docker image
docker build -t expense-bot .

# Run container
docker run -p 8080:8080 --env-file config.env expense-bot
```

## 📊 Google Sheets Integration

### Sheet Structure:
- Each month gets its own sheet (January, February, etc.)
- Automatic sheet creation on the 28th of each month
- Data starts from row 8 to accommodate headers and summaries

### Permissions:
- Service Account: Share sheet with service account email
- OAuth: Grant access during first run

## 🔐 Security Features

- ✅ **User Authentication**: Telegram User ID-based access control
- ✅ **Environment Variables**: No hardcoded credentials
- ✅ **Webhook Security**: Secret token validation
- ✅ **Google Cloud Integration**: Secret Manager support
- ✅ **Input Validation**: Sanitized user inputs
- ✅ **Error Handling**: Comprehensive error logging

## 🚀 Deployment Platforms

### Supported Platforms:
- **Google Cloud Run** (Recommended)
- **Heroku**
- **Railway**
- **DigitalOcean App Platform**
- **AWS Lambda** (with minor modifications)

### Environment Variables for Production:
```bash
bot_token=your_telegram_bot_token
google_sheet_id=your_sheet_id
webhook_url=your_production_url
gcp_project_id=your_gcp_project
scheduler_token=your_secret_token
ALLOWED_USER_IDS=comma_separated_user_ids
ALLOWED_USER_NAMES=comma_separated_names
```

## 📈 Monitoring and Logs

- **Application Logs**: Comprehensive logging for debugging
- **Error Tracking**: Automatic error reporting and handling
- **Usage Analytics**: Track bot usage patterns
- **Performance Monitoring**: Response time and reliability metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`python -m pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Security Setup**: See [docs/SECURITY.md](docs/SECURITY.md)
- **Testing Guide**: See [docs/TESTING.md](docs/TESTING.md)
- **Issues**: Open an issue on GitHub
- **Documentation**: Check the `docs/` directory for detailed guides

## 🎉 Acknowledgments

- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- Google Sheets API integration
- FastAPI for webhook handling
- Fuzzy string matching with fuzzywuzzy

---

**🔒 Remember**: Never commit actual configuration files (`config.env`, `token.json`) to version control!
