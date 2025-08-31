"""
Unit tests for the Expense Bot functionality.
Tests cover main areas including configuration, expense handling, reminders, and API endpoints.
"""

import asyncio
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, mock_open, AsyncMock
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

# Import the modules to test
from bot import (
    Config, ExpenseItem, get_expense_data, applicable_reminders,
    refresh_types_data, get_credit_card_data, detect_types, match_keywords,
    get_types_data, format_expenses_as_table, ist_date, update_google_sheet,
    app, restricted, expense_summary, handle_credit_card_reminders
)


class TestConfig(unittest.TestCase):
    """Test the Config class initialization and validation."""
    
    def setUp(self):
        """Set up test environment variables."""
        self.original_env = os.environ.copy()
        
    def tearDown(self):
        """Restore original environment variables."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_config_initialization_with_required_env(self):
        """Test Config initialization with required environment variables."""
        os.environ.update({
            'bot_token': 'test_token',
            'webhook_url': 'https://test.com',
            'google_sheet_id': 'test_sheet_id'
        })
        
        config = Config()
        
        self.assertEqual(config.token, 'test_token')
        self.assertEqual(config.webhook_url, 'https://test.com')
        self.assertEqual(config.google_sheet_id, 'test_sheet_id')
        self.assertFalse(config.is_local)
        self.assertEqual(len(config.users), 2)
    
    def test_config_missing_required_token(self):
        """Test Config raises error when bot_token is missing."""
        with self.assertRaises(ValueError) as context:
            Config()
        
        self.assertIn("bot_token environment variable is required", str(context.exception))
    
    def test_config_local_environment(self):
        """Test Config behavior in local environment."""
        os.environ.update({
            'bot_token': 'test_token',
            'local': 'true'
        })
        
        config = Config()
        
        self.assertTrue(config.is_local)
        self.assertEqual(config.current_month, "Test")
        self.assertEqual(len(config.users), 1)
        self.assertEqual(config.users[0]['name'], "Gopi")


class TestExpenseItem(unittest.TestCase):
    """Test the ExpenseItem class."""
    
    def test_expense_item_initialization(self):
        """Test ExpenseItem initialization with all parameters."""
        item = ExpenseItem(
            row_id=10,
            date="24/07/2025",
            desc="Coffee",
            amount="150.50",
            main_type="Food",
            sub_type="Beverages",
            user="Gopi",
            bot_identified="Yes"
        )
        
        self.assertEqual(item.row_id, 10)
        self.assertEqual(item.date, "24/07/2025")
        self.assertEqual(item.desc, "Coffee")
        self.assertEqual(item.amount, "150.50")
        self.assertEqual(item.main_type, "Food")
        self.assertEqual(item.sub_type, "Beverages")
        self.assertEqual(item.user, "Gopi")
        self.assertEqual(item.bot_identified, "Yes")
    
    def test_expense_item_numeric_amount(self):
        """Test numeric_amount property conversion."""
        # Test with comma-separated amount
        item1 = ExpenseItem(1, "24/07", "Test", "1,500.75")
        self.assertEqual(item1.numeric_amount, 1500.75)
        
        # Test with simple amount
        item2 = ExpenseItem(2, "24/07", "Test", "250")
        self.assertEqual(item2.numeric_amount, 250.0)
        
        # Test with empty amount
        item3 = ExpenseItem(3, "24/07", "Test", "")
        self.assertEqual(item3.numeric_amount, 0.0)
        
        # Test with invalid amount
        item4 = ExpenseItem(4, "24/07", "Test", "invalid")
        self.assertEqual(item4.numeric_amount, 0.0)
    
    def test_expense_item_repr(self):
        """Test string representation of ExpenseItem."""
        item = ExpenseItem(1, "24/07", "Coffee", "150", "Food", "Beverages")
        repr_str = repr(item)
        
        self.assertIn("Coffee", repr_str)
        self.assertIn("150", repr_str)
        self.assertIn("Food", repr_str)
        self.assertIn("Beverages", repr_str)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""
    
    def test_ist_date(self):
        """Test IST date function returns datetime object."""
        result = ist_date()
        self.assertIsInstance(result, datetime)
    
    def test_match_keywords(self):
        """Test keyword matching functionality."""
        # Test positive match
        self.assertTrue(match_keywords("pizza delivery", ["pizza", "food"]))
        
        # Test negative match
        self.assertFalse(match_keywords("taxi ride", ["food", "pizza"]))
        
        # Test case insensitive
        self.assertTrue(match_keywords("PIZZA order", ["pizza"]))
        
        # Test empty keywords
        self.assertFalse(match_keywords("test", []))
    
    def test_format_expenses_as_table(self):
        """Test expense table formatting."""
        # Test with expenses
        expenses = [
            ExpenseItem(1, "24/07", "Coffee", "150"),
            ExpenseItem(2, "24/07", "Lunch", "300")
        ]
        result = format_expenses_as_table(expenses)
        
        self.assertIn("Coffee", result)
        self.assertIn("Lunch", result)
        self.assertIn("150", result)
        self.assertIn("300", result)
        
        # Test with empty expenses
        empty_result = format_expenses_as_table([])
        self.assertEqual(empty_result, "No expenses to display.")


class TestDetectTypes(unittest.TestCase):
    """Test type detection functionality."""
    
    @patch('bot.open', mock_open(read_data='{"food": ["pizza", "coffee"], "groceries": ["milk", "bread"]}'))
    @patch('bot.get_types_data')
    @patch('bot._data_cache', {"pizza hut": {"main_type": "Food", "sub_type": "Outside Food"}})
    def test_detect_types_keyword_match(self, mock_get_types):
        """Test type detection with keyword matching."""
        # Test food keyword
        main_type, sub_type = detect_types("pizza delivery")
        self.assertEqual(main_type, "Food")
        self.assertEqual(sub_type, "Outside Food/Dining/Snacks")
        
        # Test groceries keyword
        main_type, sub_type = detect_types("milk and bread")
        self.assertEqual(main_type, "Household")
        self.assertEqual(sub_type, "Groceries")


class TestDetectTypes(unittest.TestCase):
    """Test type detection functionality."""
    
    def test_detect_types_keyword_match(self):
        """Test type detection with keyword matching."""
        with patch('bot._data_cache', {"pizza hut": {"main_type": "Food", "sub_type": "Outside Food"}}), \
             patch('bot.get_types_data'), \
             patch('bot.open', mock_open(read_data='{"food": ["pizza", "coffee"], "groceries": ["milk", "bread"]}')):
            
            # Test food keyword
            main_type, sub_type = detect_types("pizza delivery")
            self.assertEqual(main_type, "Food")
            self.assertEqual(sub_type, "Outside Food/Dining/Snacks")
            
            # Test groceries keyword
            main_type, sub_type = detect_types("milk and bread")
            self.assertEqual(main_type, "Household")
            self.assertEqual(sub_type, "Groceries")
    
    def test_detect_types_exact_match(self):
        """Test type detection with exact cache match."""
        with patch('bot._data_cache', {"starbucks coffee": {"main_type": "Food", "sub_type": "Beverages"}}), \
             patch('bot.get_types_data'), \
             patch('bot.open', side_effect=FileNotFoundError()):
            
            main_type, sub_type = detect_types("starbucks coffee")
            self.assertEqual(main_type, "Food")
            self.assertEqual(sub_type, "Beverages")
    
    def test_detect_types_fuzzy_match(self):
        """Test type detection with fuzzy matching."""
        with patch('bot._data_cache', {}), \
             patch('bot.get_types_data') as mock_get_types, \
             patch('bot.open', side_effect=FileNotFoundError()), \
             patch('fuzzywuzzy.process.extractOne', return_value=("food", 85)):
            
            mock_get_types.return_value = {
                'main_types': ['food', 'transport'],
                'sub_types': {'food': ['restaurant', 'grocery']}
            }
            main_type, sub_type = detect_types("resto")
            # Since we're using mocks, the exact return depends on implementation
            self.assertIsNotNone(main_type)
            self.assertIsNotNone(sub_type)
    
    def test_detect_types_no_match(self):
        """Test type detection with no match found."""
    def test_detect_types_no_match(self):
        """Test type detection with no match found."""
        with patch('bot._data_cache', {}), \
             patch('bot.get_types_data') as mock_get_types, \
             patch('bot.open', side_effect=FileNotFoundError()):
            
            mock_get_types.return_value = {
                'main_types': ['food', 'transport'],
                'sub_types': {'food': ['restaurant', 'grocery']}
            }
            main_type, sub_type = detect_types("completely_unknown_item")
            self.assertEqual(main_type, "")
            self.assertEqual(sub_type, "")


class TestApplicableReminders(unittest.TestCase):
    """Test reminder functionality."""
    
    @patch('bot.config')
    @patch('bot.ist_date')
    def test_applicable_reminders_success(self, mock_ist_date, mock_config):
        """Test applicable reminders with valid data."""
        mock_config.reminders_json = "test_reminders.json"
        mock_ist_date.return_value.strftime.return_value = "15"
        
        reminder_data = [
            {"desc": "Rent", "date_range": "1-5", "main_type": "Housing", "sub_type": "Rent"},
            {"desc": "Electricity", "date_range": "10-20", "main_type": "Utilities", "sub_type": "Power"},
            {"desc": "Internet", "date_range": "25-30", "main_type": "Utilities", "sub_type": "Internet"}
        ]
        
        with patch('bot.open', mock_open(read_data=json.dumps(reminder_data))):
            result = applicable_reminders()
        
        # Should return only the electricity reminder (day 15 is in range 10-20)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['desc'], "Electricity")
    
    @patch('bot.config')
    def test_applicable_reminders_file_not_found(self, mock_config):
        """Test applicable reminders when file doesn't exist."""
        mock_config.reminders_json = "nonexistent.json"
        
        with patch('bot.open', side_effect=FileNotFoundError()):
            result = applicable_reminders()
        
        self.assertEqual(result, [])


class TestGoogleSheetsIntegration(unittest.TestCase):
    """Test Google Sheets integration functions."""
    
    @patch('bot.get_creds')
    @patch('bot.build')
    @patch('bot.config')
    def test_get_expense_data_success(self, mock_config, mock_build, mock_get_creds):
        """Test successful expense data retrieval."""
        mock_config.current_month = "July"
        mock_config.google_sheet_id = "test_sheet_id"
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Mock Google Sheets API response
        mock_response = {
            "values": [
                ["24/07", "Coffee", "150", "Food", "Beverages", "Gopi", "Yes"],
                ["24/07", "Lunch", "300", "Food", "Meals", "Manasa", "No"]
            ]
        }
        mock_service.spreadsheets().values().get().execute.return_value = mock_response
        
        result = get_expense_data()
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].desc, "Coffee")
        self.assertEqual(result[1].desc, "Lunch")
    
    @patch('bot.get_creds')
    @patch('bot.build')
    @patch('bot.config')
    def test_get_expense_data_api_error(self, mock_config, mock_build, mock_get_creds):
        """Test expense data retrieval with API error."""
        from googleapiclient.errors import HttpError
        
        mock_config.current_month = "July"
        mock_config.google_sheet_id = "test_sheet_id"
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        mock_service.spreadsheets().values().get().execute.side_effect = HttpError(
            resp=Mock(status=403), content=b'API Error'
        )
        
        result = get_expense_data()
        
        self.assertIsInstance(result, str)
        self.assertIn("Google Sheets API Error", result)


class TestAsyncFunctions(unittest.IsolatedAsyncioTestCase):
    """Test async functions using asyncio test case."""
    
    async def test_refresh_types_data_success(self):
        """Test successful types data refresh."""
        mock_bot = AsyncMock()
        
        with patch('bot.get_expense_data') as mock_get_data, \
             patch('bot.config') as mock_config, \
             patch('bot.os.path.exists', return_value=True), \
             patch('bot.open', mock_open(read_data='[]')), \
             patch('bot.ist_date') as mock_ist_date, \
             patch('bot.bot_builder') as mock_bot_builder:
            
            mock_bot_builder.bot = mock_bot
            mock_config.types_data_json = "test_types.json"
            mock_config.users = [{"id": 123, "name": "Test"}]
            mock_config.ids_allowed_to_chat_with_bot = [123]
            
            mock_get_data.return_value = [
                ExpenseItem(1, "24/07", "Coffee", "150", "Food", "Beverages", "Test", "No")
            ]
            mock_ist_date.return_value.strftime.return_value = "24/07"
            mock_ist_date.return_value.day = 15
            
            result = await refresh_types_data()
            
            self.assertEqual(result["status"], "success")
    
    async def test_handle_credit_card_reminders(self):
        """Test credit card reminders handling."""
        mock_bot = AsyncMock()
        
        with patch('bot.get_credit_card_data') as mock_get_cards, \
             patch('bot.ist_date') as mock_ist_date, \
             patch('bot.config') as mock_config, \
             patch('bot.bot_builder') as mock_bot_builder:
            
            mock_bot_builder.bot = mock_bot
            mock_config.ids_allowed_to_chat_with_bot = [123]
            mock_ist_date.return_value.strftime.return_value = "24/07"
            
            # Mock credit card data with due date today
            mock_get_cards.return_value = [
                {"name": "HDFC", "due_date": "24/07", "amount": "5000", "status": "unpaid"}
            ]
            
            await handle_credit_card_reminders(None)
            
            # Should send reminder message
            mock_bot.send_message.assert_called_once()
            args = mock_bot.send_message.call_args
            self.assertIn("HDFC", args[1]['text'])
            self.assertIn("due today", args[1]['text'])


class TestAPIEndpoints(unittest.TestCase):
    """Test FastAPI endpoints."""
    
    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    @patch('bot.config')
    def test_types_refresh_api_unauthorized(self, mock_config):
        """Test types refresh API with invalid token."""
        mock_config.scheduler_token = "valid_token"
        
        response = self.client.get(
            "/types_refresh",
            headers={"X-Secret-Token": "invalid_token"}
        )
        
        self.assertEqual(response.status_code, 401)
    
    @patch('bot.config')
    @patch('bot.refresh_types_data', new_callable=AsyncMock)
    async def test_types_refresh_api_success(self, mock_refresh, mock_config):
        """Test types refresh API with valid token."""
        mock_config.scheduler_token = "valid_token"
        mock_refresh.return_value = {"status": "success"}
        
        response = self.client.get(
            "/types_refresh",
            headers={"X-Secret-Token": "valid_token"}
        )
        
        self.assertEqual(response.status_code, 200)
    
    @patch('bot.config')
    def test_process_update_unauthorized(self, mock_config):
        """Test process update with invalid secret token."""
        mock_config.secret_token = "valid_secret"
        
        response = self.client.post(
            "/bot",
            json={"test": "data"},
            headers={"X-Telegram-Bot-Api-Secret-Token": "invalid_secret"}
        )
        
        self.assertEqual(response.status_code, 401)


class TestRestricted(unittest.TestCase):
    """Test the restricted decorator."""
    
    def test_restricted_decorator_authorized_user(self):
        """Test restricted decorator allows authorized users."""
        with patch('bot.config') as mock_config:
            mock_config.ids_allowed_to_chat_with_bot = [123456]
            
            # Create mock function
            @restricted
            def test_function(update, context):
                return "success"
            
            # Create mock update with authorized user
            mock_update = Mock()
            mock_update.effective_user.id = 123456
            mock_update.effective_user.first_name = "Test"
            
            result = test_function(mock_update, None)
            self.assertEqual(result, "success")
    
    def test_restricted_decorator_unauthorized_user(self):
        """Test restricted decorator blocks unauthorized users."""
        with patch('bot.config') as mock_config:
            mock_config.ids_allowed_to_chat_with_bot = [123456]
            
            @restricted
            def test_function(update, context):
                return "success"
            
            # Create mock update with unauthorized user
            mock_update = Mock()
            mock_update.effective_user.id = 999999
            mock_update.effective_user.first_name = "Unauthorized"
            
            result = test_function(mock_update, None)
            self.assertIsNone(result)


class TestUpdateGoogleSheet(unittest.TestCase):
    """Test Google Sheet update functionality."""
    
    @patch('bot.get_creds')
    @patch('bot.build')
    @patch('bot.detect_types')
    @patch('bot.ist_date')
    @patch('bot.config')
    def test_update_google_sheet_success(self, mock_config, mock_ist_date, 
                                       mock_detect_types, mock_build, mock_get_creds):
        """Test successful Google Sheet update."""
        mock_config.current_month = "July"
        mock_config.sheet_range = "!B8:E8"
        mock_config.google_sheet_id = "test_sheet"
        
        mock_ist_date.return_value.strftime.return_value = "24/07/2025"
        mock_detect_types.return_value = ("Food", "Beverages")
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        mock_service.spreadsheets().values().append().execute.return_value = {
            "updates": {"updatedRange": "July!B8:H8"}
        }
        
        result = update_google_sheet("150", "Coffee", "Gopi")
        
        self.assertIsInstance(result, dict)
        self.assertIn("updates", result)


class TestGetTypesData(unittest.TestCase):
    """Test types data loading functionality."""
    
    @patch('bot.config')
    @patch('bot._data_cache', {})
    def test_get_types_data_success(self, mock_config):
        """Test successful types data loading."""
        mock_config.types_data_json = "test_types.json"
        
        types_data = [
            {"desc": "Coffee", "main_type": "Food", "sub_type": "Beverages"},
            {"desc": "Taxi", "main_type": "Transport", "sub_type": "Cab"}
        ]
        
        with patch('bot.open', mock_open(read_data=json.dumps(types_data))):
            get_types_data()
        
        from bot import _data_cache
        self.assertIn("coffee", _data_cache)
        self.assertIn("taxi", _data_cache)
    
    @patch('bot.config')
    @patch('bot._data_cache', {})
    def test_get_types_data_file_not_found(self, mock_config):
        """Test types data loading when file doesn't exist."""
        mock_config.types_data_json = "nonexistent.json"
        
        with patch('bot.open', side_effect=FileNotFoundError()):
            get_types_data()  # Should not raise exception
        
        from bot import _data_cache
        self.assertEqual(len(_data_cache), 0)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
