# Expense Bot

A Telegram bot that automatically logs expenses to Google Sheets with smart categorization and reminders.

## ⚠️ Security Notice

**IMPORTANT**: This repository contains example configuration files only. Before using this bot, you must set up your own credentials and environment variables. See [SECURITY.md](SECURITY.md) for detailed security setup instructions.

## Features

- 📊 Automatic expense logging to Google Sheets
- 🤖 Smart expense categorization using fuzzy matching
- 📅 Daily expense summaries and visual charts
- ⏰ Automated reminders for recurring expenses
- 💳 Credit card payment reminders
- 🔐 User authentication and access control

## Setup

### Prerequisites

- Python 3.8+
- Google Cloud Platform account (for production)
- Telegram Bot Token
- Google Sheets API credentials

### 1. Clone and Install Dependencies

```bash
git clone <your-repo-url>
cd expense_bot
pip install -r requirements.txt
```

### 2. Security Setup (CRITICAL)

**⚠️ You MUST complete this step before running the bot:**

1. Read the [SECURITY.md](SECURITY.md) guide thoroughly
2. Set up your own Telegram bot and Google API credentials
3. Configure environment variables as described below

### 3. Environment Configuration

#### For Local Development:

```bash
# Copy the example configuration
cp config.env.example config.env

# Edit config.env with your actual values:
# - bot_token: Your Telegram bot token from @BotFather
# - google_sheet_id: Your Google Sheet ID
# - webhook_url: Your ngrok or local webhook URL
# - ALLOWED_USER_IDS: Comma-separated Telegram user IDs
# - ALLOWED_USER_NAMES: Comma-separated user names
# - And other required values...
```

#### For Cloud Deployment:

```bash
# Copy the cloud example configuration
cp config_cloud.env.example config_cloud.env

# Configure cloud environment variables in your deployment platform
```

### 4. Google Sheets Setup

1. Create a new Google Sheet for your expenses
2. Set up the sheet with proper headers (see example structure)
3. Enable Google Sheets API in Google Cloud Console
4. Create service account credentials or OAuth credentials
5. Share your sheet with the service account email

### 5. User Configuration

Find your Telegram User ID by messaging [@userinfobot](https://t.me/userinfobot), then set:

```bash
ALLOWED_USER_IDS=123456789,987654321
ALLOWED_USER_NAMES=Alice,Bob
```

## Running the Bot

### Local Development

```bash
uvicorn bot:app --reload --host 0.0.0.0 --port 8080 --env-file config.env
```

### Cloud Deployment

Deploy to Google Cloud Run or your preferred platform with the environment variables configured.

## Usage

### Bot Commands

- `/expense` - Start logging a new expense
- `/summary` - Get today's expense summary  
- `/today` - Get visual expense summary with charts
- `/reminders` - Check today's reminders
- `/refresh` - Refresh expense categorization data
- `/cancel` - Cancel current operation

### Expense Format

Send expenses in the format: `Description Amount`

Examples:
- `Coffee 150`
- `Groceries 2500`
- `Uber ride 350`

## Features Detail

### Smart Categorization
The bot automatically categorizes expenses based on:
- Previous expense patterns
- Keyword matching
- Fuzzy string matching

### Reminders
Set up recurring expense reminders in `reminders.json` with date ranges.

### Credit Card Tracking
Track credit card due dates and amounts with automatic payment reminders.

## Testing

```bash
# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=html
```

## Security Features

- ✅ User authentication via Telegram User IDs
- ✅ Environment variable based configuration
- ✅ No hardcoded credentials
- ✅ Secure webhook token validation
- ✅ Google Cloud Secret Manager integration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license here]

## Support

For security setup help, see [SECURITY.md](SECURITY.md).

For other questions, please open an issue.

---

**🔒 Remember**: Never commit actual configuration files (`config.env`, `token.json`) to version control!
