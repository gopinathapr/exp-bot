"""
Expense Bot main module.
Handles initialization and configuration for the Telegram bot.
"""

# Standard library imports
import json
import logging
import os
import re
import secrets
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import wraps
from http import HTTPStatus
from typing import Dict, List, Optional, Union, Any, Coroutine

# Third-party imports
import pytz
from fastapi import FastAPI, Response, Request, HTTPException
from fuzzywuzzy import fuzz
from google.auth.transport.requests import Request as GoogleRequest
from google.cloud import secretmanager
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from starlette.responses import HTMLResponse
from tabulate import tabulate
from telegram import ReplyKeyboardRemove, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext

# Local imports
from expenseimage import create_image

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Constants
IST_TIMEZONE = "Asia/Kolkata"
SHEET_START_ROW = 8
SHEET_END_ROW = 200
FUZZY_MATCH_THRESHOLD = 75
REMINDER_DATE_RANGE_SEPARATOR = "-"
MAX_RESULTS_DISPLAY = 10


# Utility functions
def ist_date() -> datetime:
    """Returns current datetime in IST timezone."""
    ist = pytz.timezone(IST_TIMEZONE)
    return datetime.now(ist)


class Config:
    """Configuration management for the expense bot."""
    
    def __init__(self):
        self.token = os.environ.get("bot_token")
        if not self.token:
            raise ValueError("bot_token environment variable is required")
            
        self.secret_token = secrets.token_urlsafe(16)
        self.webhook_url = os.environ.get("webhook_url")
        self.types_data_json = os.environ.get("types_data_json", "types_data.json")
        self.reminders_json = os.environ.get("reminders_json", "reminders.json")
        self.google_sheet_id = os.environ.get("google_sheet_id")
        self.scheduler_token = os.environ.get("scheduler_token")
        self.gcp_project_id = os.environ.get("gcp_project_id")
        self.gcp_secret_id = os.environ.get("gcp_secret_id")
        self.sheets_creds = os.environ.get("sheets_creds", "{}")
        
        # User configuration
        self._load_user_configuration()

        # Google Sheets configuration
        self.scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        self.sheet_range = "!B8:E8"
        self.current_month = self._get_current_month()
        
        logger.info("Current month set to: %s", self.current_month)
    
    def _load_user_configuration(self):
        """Load user configuration from environment variables or defaults."""
        # Try to get user configuration from environment variables
        user_ids_env = os.environ.get("ALLOWED_USER_IDS", "")
        user_names_env = os.environ.get("ALLOWED_USER_NAMES", "")

        if user_ids_env and user_names_env:
            # Parse comma-separated user IDs and names
            user_ids = [int(id.strip()) for id in user_ids_env.split(",") if id.strip()]
            user_names = [name.strip() for name in user_names_env.split(",") if name.strip()]

            if len(user_ids) == len(user_names):
                self.users = [
                    {"id": user_id, "name": name}
                    for user_id, name in zip(user_ids, user_names)
                ]
            else:
                logger.warning("Mismatch between user IDs and names count. Using default configuration.")
                self.users = []
        else:
            # Default empty configuration - users must set environment variables
            self.users = []
            logger.warning("No user configuration found in environment variables. Set ALLOWED_USER_IDS and ALLOWED_USER_NAMES.")

        self.is_local = os.getenv("local", "false").lower() == "true"

        # For local development, you can still override with a single test user
        if self.is_local and os.environ.get("LOCAL_TEST_USER_ID"):
            test_user_id = int(os.environ.get("LOCAL_TEST_USER_ID"))
            test_user_name = os.environ.get("LOCAL_TEST_USER_NAME", "Test User")
            self.users = [{"id": test_user_id, "name": test_user_name}]

        self.ids_allowed_to_chat_with_bot = [
            user["id"] for user in self.users if user.get("id")
        ]

    def _get_current_month(self) -> str:
        """Get current month or 'Test' for local environment."""
        if self.is_local:
            return "Test"
        return ist_date().strftime("%B")


# Initialize configuration (only if not in test mode)
config = None
if not os.environ.get('PYTEST_CURRENT_TEST'):
    try:
        config = Config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        config = None

# Build the Telegram Bot application
bot_builder = None
if config:
    bot_builder = (
        Application.builder()
        .token(config.token)
        .updater(None)
        .build()
    )

_data_cache: Dict[str, Dict[str, str]] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Sets the webhook for the Telegram Bot and manages its lifecycle (start/stop)."""
    if not config or not bot_builder:
        yield
        return
        
    url = config.webhook_url + "/bot"
    await bot_builder.bot.setWebhook(url=url, secret_token=config.secret_token)
    async with bot_builder:
        await bot_builder.start()
        yield
        await bot_builder.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/bot", response_class=HTMLResponse)
async def read_items():
    html_content = """
    <html>
        <head>
            <title>Some HTML in here</title>
        </head>
        <body>
            <h1>Hello, You are here!</h1>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


class ExpenseItem:
    """Represents an expense item with all its properties."""
    
    def __init__(
        self, 
        row_id: int, 
        date: str, 
        desc: str, 
        amount: str, 
        main_type: Optional[str] = None, 
        sub_type: Optional[str] = None, 
        user: str = "", 
        bot_identified: str = "No"
    ):
        self.row_id = row_id
        self.date = date
        self.desc = desc
        self.amount = amount
        self.main_type = main_type
        self.sub_type = sub_type
        self.user = user
        self.bot_identified = bot_identified

    def __repr__(self) -> str:
        return (
            f"ExpenseItem(date='{self.date}', desc='{self.desc}', "
            f"amount='{self.amount}', main_type='{self.main_type}', "
            f"sub_type='{self.sub_type}', user='{self.user}', "
            f"bot_identified='{self.bot_identified}')"
        )
    
    @property
    def numeric_amount(self) -> float:
        """Convert amount string to float, removing commas."""
        try:
            return float(self.amount.replace(",", "")) if self.amount else 0.0
        except (ValueError, AttributeError):
            return 0.0


def get_expense_data() -> Union[List[ExpenseItem], str]:
    """Fetch expense data from Google Sheets."""
    creds = get_creds()
    try:
        service = build("sheets", "v4", credentials=creds)
        range_to_fetch = f"{config.current_month}!B8:J200"
        result = (
            service.spreadsheets()
            .values().get(spreadsheetId=config.google_sheet_id, range=range_to_fetch, alt="json").execute()
        )
        row_id = SHEET_START_ROW
        exp_list = []
        values = result.get("values", [])
        if not values:
            return []
        for item in values:
            exp_list.append(ExpenseItem(
                row_id=row_id,
                date=item[0] if len(item) > 0 else "",
                desc=item[1] if len(item) > 1 else "",
                amount=item[2] if len(item) > 2 else "",
                main_type=item[3] if len(item) > 3 else "",
                sub_type=item[4] if len(item) > 4 else "",
                user=item[5] if len(item) > 5 else "",
                bot_identified=item[6] if len(item) > 6 else "No",
            ))
            row_id += 1
        return exp_list
    except HttpError as e:
        logger.error(f"HTTP error occurred while fetching expenses: {e}")
        return f"Google Sheets API Error: {e}"
    except Exception as e:
        traceback.print_exc()
        logger.error(f"An error occurred while fetching expenses: {e}")
        return f"Error! {e}"


def applicable_reminders() -> List[Dict[str, Any]]:
    """Get reminders that are applicable for today based on date range."""
    today_reminders = []
    try:
        with open(config.reminders_json, "r") as file:
            reminders = json.load(file)
            today = int(ist_date().strftime("%d"))
            for rem in reminders:
                date_range = rem.get("date_range", "")
                if REMINDER_DATE_RANGE_SEPARATOR in date_range:
                    _start, _end = map(int, date_range.split(REMINDER_DATE_RANGE_SEPARATOR))
                    if _start <= today <= _end:
                        today_reminders.append(rem)
    except FileNotFoundError:
        logger.warning(f"Reminders file not found: {config.reminders_json}")
    except (ValueError, KeyError) as e:
        logger.error(f"Error parsing reminders file: {e}")
    except Exception as e:
        logger.error(f"Unexpected error reading reminders: {e}")
    return today_reminders


@app.get("/types_refresh")
async def refresh_types_data_api(request: Request):
    """API endpoint to refresh types data."""
    my_header = request.headers.get("X-Secret-Token")
    if my_header != config.scheduler_token:
        logger.error("Invalid secret token: %s", my_header)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Unauthorized")
    
    await refresh_types_data()
    return Response(status_code=HTTPStatus.OK)


async def refresh_types_data() -> Dict[str, str]:
    """Refresh types data cache and send user reminders."""
    global _data_cache
    try:
        # types refresh
        expense_list = get_expense_data()
        if isinstance(expense_list, str):  # Error case
            return {"status": "error", "message": expense_list}
            
        filtered_list = [exp for exp in expense_list if exp.main_type and exp.sub_type and exp.bot_identified != "Yes"]
        new_types = [{"desc": exp.desc, "main_type": exp.main_type, "sub_type": exp.sub_type} for exp in filtered_list]
        
        if os.path.exists(config.types_data_json):
            with open(config.types_data_json, 'r') as file:
                json_file = json.load(file)
                existing_descs = {item.get('desc').lower() for item in json_file}
                new_types = [item for item in new_types if item.get('desc').lower() not in existing_descs]
                json_file.extend(new_types)
                with open(config.types_data_json, 'w') as append_file:
                    json.dump(json_file, append_file, indent=4)
        else:
            json_file = new_types
            with open(config.types_data_json, 'w') as new_file:
                json.dump(json_file, new_file, indent=4)

        json_file = [item for item in json_file if item.get('main_type') and item.get('sub_type')]
        for item in json_file:
            _data_cache[item.get('desc').lower()] = item
        logger.info("Types data refreshed & loaded successfully.")

        # user reminder to log expenses
        today = ist_date().strftime("%d/%m")
        today_exp = [exp for exp in expense_list if exp.date == today]
        for user in config.users:
            user_exp = [exp for exp in today_exp if user["name"].lower() in exp.user.lower()]
            if not user_exp:
                await bot_builder.bot.send_message(
                    chat_id=user["id"],
                    text=f"<b>Hello {user['name']}, You haven't logged any expense today! \n Saving money staying indoors or just lazy to log expenses??</b>",
                    parse_mode="HTML"
                )

        if ist_date().day == 28:
            await bot_builder.bot.send_message(
                chat_id=config.ids_allowed_to_chat_with_bot[0],
                text=f"<b>\n\n Hello {config.users[0]['name']}, A new sheet has been created for this month!</b>\n"
                     f"<b>You can now log your expenses and update your credit card due amount and date details.</b>",
                parse_mode="HTML"
            )
        return {"status": "success", "message": "Types data refreshed successfully."}
    except FileNotFoundError as e:
        logger.error(f"File not found while refreshing types data: {e}")
        return {"status": "error", "message": f"File not found: {e}"}
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error while refreshing types data: {e}")
        return {"status": "error", "message": f"JSON error: {e}"}
    except Exception as e:
        logger.error(f"An error occurred while refreshing types data: {e}")
        return {"status": "error", "message": str(e)}


async def types_refresh_by_command(update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("User %s requested types data refresh.", user.first_name)
    response = await refresh_types_data()
    if response.get("status") == "success":
        await update.message.reply_text(response.get("message"))
    else:
        await update.message.reply_text(f"Error: {response.get('message')}")
    return ConversationHandler.END


def get_credit_card_data() -> List[Dict[str, str]]:
    """Fetch credit card data from Google Sheets."""
    try:
        service = build("sheets", "v4", credentials=get_creds())
        range_to_fetch = f"{config.current_month}!T8:W13"
        result = (
            service.spreadsheets()
            .values().get(spreadsheetId=config.google_sheet_id, range=range_to_fetch, alt="json").execute()
        )
        values = result.get("values", [])
        card_list = []
        for row in values:
            if len(row) >= 4:  # Ensure we have all required fields
                card_list.append({
                    "name": row[1],
                    "due_date": row[0],
                    "amount": row[2],
                    "status": row[3],
                })
        return card_list
    except HttpError as e:
        logger.error(f"HTTP error occurred while fetching credit card data: {e}")
        return []
    except Exception as e:
        logger.error(f"An error occurred while fetching credit card data: {e}")
        return []


@app.get("/reminders")
async def process_reminders_job(request: Request):
    """Process and send reminders to users."""
    if request:
        my_header = request.headers.get("X-Secret-Token")
        if my_header != config.scheduler_token:
            logger.error("Invalid secret token: %s", my_header)
            raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Unauthorized")

    logger.info("Processing reminders job.")
    open_reminders = await active_reminders()
    if open_reminders:
        for user in config.ids_allowed_to_chat_with_bot:
            logger.info("Sending reminders to user %s", user)
            await bot_builder.bot.send_message(
                chat_id=user,
                text=f"<b>Hello, Gentle Reminder for the below expenses:</b> \n" + tabulate([[rem.get("desc")] for rem in open_reminders], tablefmt="plain"),
                parse_mode="HTML"
            )
            logger.info("Reminders processed and sent to the user.")
    else:
        logger.info("No active reminders found.")

    await handle_credit_card_reminders(update=None)
    return Response(status_code=HTTPStatus.OK)


async def reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("User %s requested reminders.", user.first_name)
    reminders_list = await active_reminders()
    if reminders_list:
        await update.message.reply_text(text=f"<b>Today's Reminders:</b>\n" + tabulate([[rem.get("desc")] for rem in reminders_list], tablefmt="plain"),
                                        parse_mode="HTML"
                                        )
    else:
        await update.message.reply_text("No reminders for today for any fixed expenses. Enjoy your day!")

    await handle_credit_card_reminders(update)
    return ConversationHandler.END


async def handle_credit_card_reminders(update: Optional[Update]):
    """Handle credit card payment reminders."""
    # credit card payment reminders
    card_list = get_credit_card_data()
    logger.info("Processing credit card payment reminders." + str(card_list))
    for card in card_list:
        if card.get("status", "").lower() == "paid":
            logger.info("Skipping card %s as it is already paid. with status: %s ", card.get("name"), card.get("status"))
            continue
        card["amount"] = card.get("amount", "0").strip().replace(",", "")
        card["amount"] = "0" if card["amount"] == "" else card["amount"]
        if card.get("due_date") is None or float(card.get("amount")) == 0:
            logger.error("Due date is missing for card: %s", card.get("name"))
            continue
        due_date_str = card.get("due_date")
        today = ist_date().strftime("%d/%m")
        tomorrow = (ist_date() + timedelta(days=1)).strftime("%d/%m")
        due_dates = {
            today: f"<b>Reminder: Your credit card payment for {card.get('name')} is due today - {today}, with amount {card.get('amount')}</b>",
            tomorrow: f"<b>Reminder: Your credit card payment for {card.get('name')} is due tomorrow - {tomorrow}.</b>"
        }
        logger.info("Due dates for card %s: %s", card.get("name"), due_date_str)
        if due_date_str in due_dates:
            if update:
                await update.message.reply_text(text=due_dates[due_date_str],
                                                parse_mode="HTML")
                continue
            for user in config.ids_allowed_to_chat_with_bot:
                logger.info("Sending reminders to user %s", user)
                await bot_builder.bot.send_message(
                    chat_id=user,
                    text=due_dates[due_date_str],
                    parse_mode="HTML"
                )
                logger.info("Credit card payment reminder sent for card: %s", card.get("name"))
        else:
            logger.info("No reminder needed for card %s, due date: %s", card.get("name"), card.get("due_date"))


async def active_reminders() -> list:
    """
    Returns a list of reminders that are applicable for today and have not yet been logged as expenses.
    Avoids modifying the reminder list while iterating.
    """
    reminders_list = applicable_reminders()
    if reminders_list:
        exp_list = get_expense_data()
        valid_expenses = [exp for exp in exp_list if exp.main_type != "" and exp.sub_type != ""]
        logger.info("Valid expenses found: %s", valid_expenses)
        filtered_reminders = []
        for rem in reminders_list:
            found = False
            for exp in valid_expenses:
                if exp.main_type == rem["main_type"] and exp.sub_type == rem["sub_type"]:
                    logger.info("Expense already logged for reminder: %s", rem["desc"])
                    found = True
                    break
            if not found:
                logger.info("Reminder found: %s", rem)
                filtered_reminders.append(rem)
        reminders_list = filtered_reminders
    else:
        logger.info("No applicable reminders found.")
        reminders_list = []
    return reminders_list


@app.post("/bot")
async def process_update(request: Request):
    """Process incoming Telegram updates."""
    my_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if config.secret_token != my_header:
        logger.error("Invalid secret token: %s", my_header)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Unauthorized")
    
    logger.info("Valid secret token: %s", my_header)
    message = await request.json()
    update = Update.de_json(data=message, bot=bot_builder.bot)
    await bot_builder.process_update(update)
    return Response(status_code=HTTPStatus.OK)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("User %s sent a message: %s", user.first_name, update.message.text)
    if update.message.text.lower() == "cancel":
        await cancel(update, context)
    else:
        await update.message.reply_text(
            "I dint get u? Please use the menu!",
            reply_markup=ReplyKeyboardRemove(),
        )
    return ConversationHandler.END


# Format the data into a table
def format_expenses_as_table(expenses: List[ExpenseItem]) -> str:
    """Format expenses as a readable table."""
    if not expenses:
        return "No expenses to display."
    
    table_data = [
        [exp.desc, exp.amount]
        for exp in expenses
    ]
    return tabulate(table_data, headers=["Description", "Amount"], tablefmt="plain")


async def expense_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's expense summary."""
    user = update.message.from_user
    logger.info("User %s requested summary.", user.first_name)
    try:
        exp_list = get_expense_data()
        if isinstance(exp_list, str):  # Error case
            await update.message.reply_text(f"An error occurred while fetching expenses! {exp_list}")
            return ConversationHandler.END
            
        today = ist_date().strftime("%d/%m")
        today_expenses = [exp for exp in exp_list if exp.date == today]
        
        if not today_expenses:
            logger.info("No expenses found for today.")
            await update.message.reply_text("No expenses found for today.")
            return ConversationHandler.END
            
        # get total expenses for today
        total_expenses = sum(exp.numeric_amount for exp in today_expenses)
        
        await update.message.reply_text(
            "<b>Today's Expenses:</b> \n\n" + format_expenses_as_table(today_expenses) + 
            f"\n\n <b>Today's Total:</b> {total_expenses:.2f}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"An error occurred while fetching expenses: {e}")
        await update.message.reply_text(f"An error occurred while fetching expenses! {e}")
    
    return ConversationHandler.END


async def expense_summary_with_types(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's expense summary with visual chart."""
    user = update.message.from_user
    logger.info("User %s requested summary with types.", user.first_name)
    try:
        exp_list = get_expense_data()
        if isinstance(exp_list, str):  # Error case
            await update.message.reply_text(f"An error occurred while fetching expenses! {exp_list}")
            return ConversationHandler.END
            
        today = ist_date().strftime("%d/%m")
        today_expenses = [exp for exp in exp_list if exp.date == today]
        
        if not today_expenses:
            logger.info("No expenses found for today.")
            await update.message.reply_text("No expenses found for today.")
            return ConversationHandler.END

        img_name = create_image(today_expenses)
        with open(img_name, "rb") as img_file:
            await update.message.reply_document(document=img_file)
    except Exception as e:
        logger.error(f"An error occurred while creating expense summary: {e}")
        await update.message.reply_text(f"An error occurred while creating summary! {e}")
    
    return ConversationHandler.END


def get_creds():
    """Get Google Sheets API credentials."""
    if config.is_local:
        return get_local_creds()
    
    if not config.gcp_project_id or not config.gcp_secret_id:
        raise ValueError("GCP project ID and secret ID are required for non-local environments")
    
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{config.gcp_project_id}/secrets/{config.gcp_secret_id}/versions/2"
    response = client.access_secret_version(request={"name": name})
    creds_info = json.loads(response.payload.data.decode("UTF-8"))
    credentials = service_account.Credentials.from_service_account_info(
        creds_info, scopes=config.scopes
    )
    return credentials


def get_local_creds():
    """Get local credentials for development."""
    if os.path.exists("token.json"):
        print("Token file found, loading credentials from it.")
        creds = Credentials.from_authorized_user_file("token.json", config.scopes)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
    else:
        flow = InstalledAppFlow.from_client_config(
            json.loads(config.sheets_creds), config.scopes
        )
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as auth_token:
            auth_token.write(creds.to_json())
    return creds


def update_google_sheet(amount: str, description: str, user: str) -> Union[Dict[str, Any], str]:
    """Update Google Sheet with new expense entry."""
    creds = get_creds()
    try:
        service = build("sheets", "v4", credentials=creds)
        range_to_update = f"{config.current_month}{config.sheet_range}"
        date_string = ist_date().strftime("%d/%m/%Y")
        main_type, sub_type = detect_types(description)
        bot_identified = "Yes" if main_type else "No"
        values = [date_string, description, amount, main_type, sub_type, user, bot_identified],
        body = {"values": values}
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=config.google_sheet_id,
                range=range_to_update,
                valueInputOption="USER_ENTERED",
                body=body,
            )
            .execute()
        )
        logger.info(f"{result.get('updates').get('updatedRange')} cells updated.")
        return result
    except HttpError as e:
        logger.error(f"HTTP error occurred while updating sheet: {e}")
        return f"Google Sheets API Error: {e}"
    except Exception as e:
        logger.error(f"An error occurred while updating sheet: {e}")
        return f"Error! {e}"


def restricted(func):
    """Decorator to restrict access to authorized users only."""
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        name = update.effective_user.first_name
        if user_id not in config.ids_allowed_to_chat_with_bot:
            logger.error("Unauthorized! access denied for user {} with id {}.".format(name, user_id))
            return
        return func(update, context, *args, **kwargs)

    return wrapped


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s cancelled the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )
    return -1


@restricted
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'Hey {update.effective_user.first_name}!' + "\n"
                                    + "Menu here: \n "
                                    + "/expense for logging your expenses.\n"
                                    + "/summary for expense summary of the day(TBD).\n"
                                    + "/cancel for aborting chat anytime.\n")
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler."""
    chat_id = update.message.chat.id
    if chat_id not in config.ids_allowed_to_chat_with_bot:
        logger.error(f"Message from chat ID {chat_id} ignored.")
        await update.message.reply_text(
            "You are not allowed to chat with me! Please contact the bot owner."
        )
        return ConversationHandler.END
    context.user_data['show_markup'] = True
    await update.message.reply_text(
        "Hi! My name is Expense Bot. I will note down your expense for you. "
        "Send /cancel to stop talking to me.\n\n"
        "What is your expense?"
    )
    return 0


def get_types_data() -> None:
    """Load types data into cache if not already loaded."""
    global _data_cache
    if not _data_cache:
        try:
            with open(config.types_data_json, 'r') as file:
                json_file = json.load(file)
                json_file = [item for item in json_file if item.get('main_type') and item.get('sub_type')]
                for item in json_file:
                    _data_cache[item.get('desc').lower()] = item
        except FileNotFoundError:
            logger.warning(f"Types data file not found: {config.types_data_json}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing types data file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading types data: {e}")


def match_keywords(description: str, keywords: List[str]) -> bool:
    """Check if description contains any of the given keywords."""
    words = description.lower().split()
    keywords_set = set(k.lower() for k in keywords)
    matches = [word for word in words if word in keywords_set]
    return len(matches) > 0


def detect_types(desc: str) -> tuple[str, str]:
    """Detect main_type and sub_type for a given description."""
    try:
        desc_lower = desc.lower()
        
        # Load keywords for quick detection
        try:
            with open("keywords.json", 'r') as file:
                keywords = json.load(file)
            
            if match_keywords(desc_lower, keywords.get("food", [])):
                return "Food", "Outside Food/Dining/Snacks"
            if match_keywords(desc_lower, keywords.get("groceries", [])):
                return "Household", "Groceries"
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Keywords file error: {e}")
        
        # Load types data cache
        get_types_data()
        
        # Exact match
        if desc_lower in _data_cache:
            item = _data_cache.get(desc_lower)
            return item.get("main_type", ""), item.get("sub_type", "")
        
        # Fuzzy match
        for cached_desc, item in _data_cache.items():
            if fuzz.ratio(cached_desc, desc_lower) > FUZZY_MATCH_THRESHOLD:
                return item.get("main_type", ""), item.get("sub_type", "")
        
        return "", ""
    except Exception as e:
        logger.error(f"An error occurred while detecting types: {e}")
        return "", ""


@restricted
async def end_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    show_markup = context.user_data.get('show_markup', False)
    user = update.message.from_user
    text = update.message.text
    pattern = r'^([a-zA-Z0-9 ]+?)\s+((?:\d+(?:\.\d+)?\s*)+)$'

    if show_markup:
        # Conversation flow: single line only
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            description = match.group(1)
            numbers = match.group(2).split()
            amount = "=" + "+".join(numbers)
        else:
            logger.error("not a valid format so repeating the question")
            await update.message.reply_text(
                "Invalid format. Try again!"
            )
            return 0
        result = update_google_sheet(amount, description, user.first_name)
        if result.__contains__("Error!"):
            await update.message.reply_text(
                result, reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END
        logger.info("Google Sheet Update Result: %s", result)
        keyboard = [
            [InlineKeyboardButton("Add more", callback_data="add_more"),
             InlineKeyboardButton("Done", callback_data="done")
             ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Okay! I have noted down your expense. Enjoy your day 😊 ", reply_markup=reply_markup)
        return 1
    else:
        # Direct input: support multiple lines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            await update.message.reply_text(
                "If you are trying to log an expense, your input is invalid. Try again! "
                "\n\n If not, /cancel to stop otherwise, I will be stuck in a loop 🙁 "
            )
            return 0
        results = []
        errors = []
        for line in lines:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                description = match.group(1)
                numbers = match.group(2).split()
                amount = "=" + "+".join(numbers)
                result = update_google_sheet(amount, description, user.first_name)
                if isinstance(result, str) and result.__contains__("Error!"):
                    errors.append(f"{description}: {result}")
                else:
                    results.append(description)
            else:
                errors.append(f"Invalid format: {line}")
        if results:
            await update.message.reply_text(
                f"Okay! I have noted down your expenses: {', '.join(results)}. Enjoy your day 😊 ", reply_markup=ReplyKeyboardRemove()
            )
        if errors:
            await update.message.reply_text(
                "Some items could not be added:\n" + "\n".join(errors), reply_markup=ReplyKeyboardRemove()
            )
        chat_id = update.effective_chat.id
        await context.bot.send_message(
            chat_id=chat_id,
            text="👍" + "\u200B",
            reply_to_message_id=update.message.message_id
        )
        return ConversationHandler.END


async def handle_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("Conversation timed out for user %s.", user.first_name)
    await update.message.reply_text(
        "You seem to be busy! Catch up later?")
    return ConversationHandler.END


async def button(update: Update, context: CallbackContext) -> int | None:
    query = update.callback_query
    await query.answer()

    if query.data == "add_more":
        await query.edit_message_text(text="Okay, I am listening!: ")
        return 0
    elif query.data == "done":
        await query.edit_message_text(text="Okay! until we meet again!")
        context.user_data.pop('show_markup', None)
        return ConversationHandler.END
    return None


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("expense", start), MessageHandler(filters.TEXT & ~filters.COMMAND, end_conv)],
    states={
        0: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_conv)],
        1: [CallbackQueryHandler(button)],
        ConversationHandler.TIMEOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_timeout)],
    },
    fallbacks=[CommandHandler("cancel", cancel),
               MessageHandler(filters.COMMAND, handle_text)])

if bot_builder:
    bot_builder.add_handler(conv_handler)
    bot_builder.add_handler(CommandHandler("start", hello))
    bot_builder.add_handler(CommandHandler("summary", expense_summary))
    bot_builder.add_handler(CommandHandler("reminders", reminders_command))
    bot_builder.add_handler(CommandHandler("refresh", types_refresh_by_command))
    bot_builder.add_handler(CommandHandler("today", expense_summary_with_types))

# if __name__ == "__main__":
#    import uvicorn

#    uvicorn.run(app="bot:app", host="0.0.0.0", port=8080)
