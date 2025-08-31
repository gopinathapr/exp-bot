# Security Setup Guide

## ⚠️ IMPORTANT: Complete This Setup Before Making Repository Public

This guide helps you secure your expense bot before deployment or sharing the code.

## 🔒 Security Checklist

### 1. Remove Sensitive Files from Git History

Before making your repository public, you MUST remove sensitive files that contain secrets:

```bash
# Remove sensitive files from git tracking
git rm --cached config.env config_cloud.env token.json

# Add them to .gitignore (already done)
# Commit the removal
git commit -m "Remove sensitive configuration files"

# Optional: Clean git history (if you've already committed secrets)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch config.env config_cloud.env token.json' \
  --prune-empty --tag-name-filter cat -- --all
```

### 2. Revoke and Regenerate All Credentials

#### Telegram Bot Token
1. Go to [@BotFather](https://t.me/botfather) on Telegram
2. Send `/revoke` and select your bot
3. Generate a new token with `/newtoken`

#### Google OAuth Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to APIs & Services > Credentials
3. Delete the existing OAuth 2.0 client
4. Create a new OAuth 2.0 client ID
5. Download the new credentials

#### Google Sheets Access
1. Revoke existing tokens in [Google Account Security](https://myaccount.google.com/permissions)
2. Delete the `token.json` file
3. Re-authenticate when you run the bot locally

### 3. Environment Variable Setup

Create your actual configuration files based on the examples:

#### For Local Development:
```bash
cp config.env.example config.env
# Edit config.env with your actual values
```

#### For Cloud Deployment:
```bash
cp config_cloud.env.example config_cloud.env
# Edit config_cloud.env with your actual values
```

### 4. User Configuration

Set up authorized users using environment variables:

```bash
# In your config.env or cloud environment
ALLOWED_USER_IDS=123456789,987654321
ALLOWED_USER_NAMES=Alice,Bob

# For local testing (optional)
LOCAL_TEST_USER_ID=123456789
LOCAL_TEST_USER_NAME=Test User
```

To find your Telegram User ID:
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your user ID

## 🚀 Deployment Security

### Local Development
- Use `config.env` for local environment variables
- Never commit this file to git
- Use the `local=true` setting

### Cloud Deployment
- Use environment variables or secret management services
- For Google Cloud Run, set environment variables in the service configuration
- Use Google Secret Manager for sensitive data

### Google Cloud Secret Manager Setup
```bash
# Store your Google Sheets API credentials in Secret Manager
gcloud secrets create sheets_api_creds --data-file=path/to/service-account-key.json

# Set the secret version in your environment
gcp_secret_id=sheets_api_creds
```

## 🛡️ Additional Security Measures

1. **Enable 2FA** on all your Google and Telegram accounts
2. **Use strong, unique passwords** for all services
3. **Regularly rotate credentials** (monthly recommended)
4. **Monitor access logs** in Google Cloud Console
5. **Use least-privilege permissions** for service accounts

## 🚫 What NOT to Include in Public Repository

- `config.env` or `config_cloud.env` (actual files)
- `token.json` (actual file)
- Any files containing API keys, tokens, or credentials
- User IDs or personal information
- Google Sheet IDs or project IDs
- Webhook URLs with secrets

## ✅ What's Safe to Include

- `*.example` files with placeholder values
- Source code without hardcoded credentials
- Documentation and setup instructions
- Test files with mock data
- Requirements and dependency files

## 🔍 Pre-Publication Security Scan

Run this checklist before making your repository public:

- [ ] All sensitive files are in `.gitignore`
- [ ] No hardcoded credentials in source code
- [ ] All tokens and keys have been revoked and regenerated
- [ ] Example configuration files contain only placeholders
- [ ] README includes security setup instructions
- [ ] User IDs and personal information removed from code

## 🆘 If You've Already Exposed Secrets

If you've accidentally committed secrets to a public repository:

1. **Immediately revoke all exposed credentials**
2. **Change all passwords and tokens**
3. **Clean git history** using the commands above
4. **Force push** the cleaned repository
5. **Monitor for unauthorized access**

## 📞 Support

If you need help with security setup, consider:
- Consulting with a security professional
- Using managed services for credential storage
- Implementing additional monitoring and alerting
