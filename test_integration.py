"""
Integration tests for the Expense Bot.
These tests focus on testing interactions between components.
"""

import asyncio
import json
import tempfile
import unittest
from unittest.mock import Mock, patch, AsyncMock, mock_open
from datetime import datetime, timedelta

from bot import (
    Config, ExpenseItem, expense_summary, expense_summary_with_types,
    start, end_conv, button, reminders_command, active_reminders
)


class TestExpenseWorkflow(unittest.IsolatedAsyncioTestCase):
    """Test complete expense logging workflow."""
    
    async def test_complete_expense_logging_flow(self):
        """Test the complete flow of logging an expense."""
        with patch('bot.config') as mock_config, \
             patch('bot.update_google_sheet') as mock_update_sheet, \
             patch('bot.detect_types') as mock_detect_types:
            
            mock_config.ids_allowed_to_chat_with_bot = [123456]
            mock_detect_types.return_value = ("Food", "Beverages")
            mock_update_sheet.return_value = {"updates": {"updatedRange": "July!B8:H8"}}
            
            # Mock Telegram objects
            mock_update = Mock()
            mock_update.message.chat.id = 123456
            mock_update.message.from_user.first_name = "TestUser"
            mock_update.message.text = "Coffee 150"
            mock_update.message.reply_text = AsyncMock()
            mock_update.effective_chat.id = 123456
            
            mock_context = Mock()
            mock_context.user_data = {}
            mock_context.bot.send_message = AsyncMock()
            
            # Test start function
            result = await start(mock_update, mock_context)
            self.assertEqual(result, 0)
            self.assertTrue(mock_context.user_data.get('show_markup'))
            
            # Test end_conv function (expense processing) with proper user authorization
            mock_update.effective_user = Mock()
            mock_update.effective_user.id = 123456
            mock_update.effective_user.first_name = "TestUser"
            mock_update.message.from_user = mock_update.effective_user
            
            # Mock the function to bypass the decorator issues
            with patch('bot.restricted', lambda func: func):
                result = await end_conv(mock_update, mock_context)
                # Verify result is an integer (ConversationHandler state)
                self.assertIsInstance(result, int)
            
            # Verify expense was processed
            mock_update_sheet.assert_called_once()
            mock_update.message.reply_text.assert_called()


class TestReminderWorkflow(unittest.IsolatedAsyncioTestCase):
    """Test reminder workflow integration."""
    
    async def test_reminder_workflow_with_expenses(self):
        """Test reminder workflow when expenses are already logged."""
        reminder_data = [
            {"desc": "Rent", "date_range": "1-31", "main_type": "Housing", "sub_type": "Rent"}
        ]
        
        expense_data = [
            ExpenseItem(1, "24/07", "Monthly Rent", "15000", "Housing", "Rent", "Gopi", "No")
        ]
        
        with patch('bot.applicable_reminders', return_value=reminder_data), \
             patch('bot.get_expense_data', return_value=expense_data):
            
            result = await active_reminders()
            
            # Should return empty list as expense is already logged
            self.assertEqual(len(result), 0)
    
    async def test_reminder_workflow_without_expenses(self):
        """Test reminder workflow when expenses are not logged."""
        reminder_data = [
            {"desc": "Utilities", "date_range": "1-31", "main_type": "Utilities", "sub_type": "Power"}
        ]
        
        expense_data = []  # No expenses logged
        
        with patch('bot.applicable_reminders', return_value=reminder_data), \
             patch('bot.get_expense_data', return_value=expense_data):
            
            result = await active_reminders()
            
            # Should return the reminder as no matching expense found
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['desc'], "Utilities")


class TestExpenseSummaryIntegration(unittest.IsolatedAsyncioTestCase):
    """Test expense summary integration with data processing."""
    
    async def test_expense_summary_with_data(self):
        """Test expense summary with actual expense data."""
        today_date = "24/07"
        expenses = [
            ExpenseItem(1, today_date, "Coffee", "150", "Food", "Beverages"),
            ExpenseItem(2, today_date, "Lunch", "300", "Food", "Meals"),
            ExpenseItem(3, "23/07", "Dinner", "400", "Food", "Meals")  # Different date
        ]
        
        with patch('bot.get_expense_data', return_value=expenses), \
             patch('bot.ist_date') as mock_ist_date:
            
            mock_ist_date.return_value.strftime.return_value = today_date
            
            # Mock Telegram objects
            mock_update = Mock()
            mock_update.message.from_user.first_name = "TestUser"
            mock_update.message.reply_text = AsyncMock()
            
            mock_context = Mock()
            
            result = await expense_summary(mock_update, mock_context)
            
            # Verify summary was sent
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            summary_text = call_args[0][0]
            
            # Should include today's expenses only
            self.assertIn("Coffee", summary_text)
            self.assertIn("Lunch", summary_text)
            self.assertNotIn("Dinner", summary_text)  # Different date
            self.assertIn("450.00", summary_text)  # Total amount
    
    async def test_expense_summary_with_types_image(self):
        """Test expense summary with types that generates an image."""
        today_date = "24/07"
        expenses = [
            ExpenseItem(1, today_date, "Coffee", "150", "Food", "Beverages"),
            ExpenseItem(2, today_date, "Taxi", "200", "Transport", "Cab")
        ]
        
        with patch('bot.get_expense_data', return_value=expenses), \
             patch('bot.ist_date') as mock_ist_date, \
             patch('bot.create_image', return_value="test_image.png"), \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_ist_date.return_value.strftime.return_value = today_date
            
            # Mock Telegram objects
            mock_update = Mock()
            mock_update.message.from_user.first_name = "TestUser"
            mock_update.message.reply_document = AsyncMock()
            
            mock_context = Mock()
            
            result = await expense_summary_with_types(mock_update, mock_context)
            
            # Verify image was sent
            mock_update.message.reply_document.assert_called_once()


class TestConfigurationIntegration(unittest.TestCase):
    """Test configuration integration with various components."""
    
    def test_config_integration_with_environment(self):
        """Test how configuration integrates with different environment settings."""
        import os
        
        # Test production-like configuration
        with patch.dict(os.environ, {
            'bot_token': 'prod_token',
            'webhook_url': 'https://prod.example.com',
            'google_sheet_id': 'prod_sheet_id',
            'scheduler_token': 'prod_scheduler_token',
            'local': 'false'
        }):
            config = Config()
            
            self.assertEqual(config.token, 'prod_token')
            self.assertFalse(config.is_local)
            self.assertEqual(len(config.users), 2)
            self.assertNotEqual(config.current_month, "Test")
        
        # Test local configuration
        with patch.dict(os.environ, {
            'bot_token': 'local_token',
            'local': 'true'
        }):
            config = Config()
            
            self.assertTrue(config.is_local)
            self.assertEqual(config.current_month, "Test")
            self.assertEqual(len(config.users), 1)


class TestErrorHandlingIntegration(unittest.IsolatedAsyncioTestCase):
    """Test error handling across different components."""
    
    async def test_expense_summary_with_api_error(self):
        """Test expense summary when Google Sheets API fails."""
        with patch('bot.get_expense_data', return_value="Google Sheets API Error: Quota exceeded"):
            
            # Mock Telegram objects
            mock_update = Mock()
            mock_update.message.from_user.first_name = "TestUser"
            mock_update.message.reply_text = AsyncMock()
            
            mock_context = Mock()
            
            result = await expense_summary(mock_update, mock_context)
            
            # Should handle error gracefully
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            error_text = call_args[0][0]
            self.assertIn("error", error_text.lower())
    
    async def test_types_refresh_with_file_errors(self):
        """Test types refresh handling file system errors."""
        from bot import refresh_types_data
        
        with patch('bot.get_expense_data', return_value=[]), \
             patch('bot.config') as mock_config, \
             patch('bot.bot_builder') as mock_bot_builder, \
             patch('bot.os.path.exists', return_value=False):
            
            mock_bot_builder.bot = AsyncMock()
            mock_config.types_data_json = "test_types.json"
            mock_config.users = [{"id": 123, "name": "Test"}]
            mock_config.ids_allowed_to_chat_with_bot = [123]
            
            # Should handle missing file gracefully
            result = await refresh_types_data()
            
            self.assertEqual(result["status"], "success")
    
    async def test_credit_card_reminders_with_invalid_data(self):
        """Test credit card reminders with invalid or missing data."""
        from bot import handle_credit_card_reminders
        
        # Test with invalid card data
        invalid_cards = [
            {"name": "Card1", "due_date": None, "amount": "1000", "status": "unpaid"},
            {"name": "Card2", "due_date": "24/07", "amount": "", "status": "unpaid"},
            {"name": "Card3", "due_date": "24/07", "amount": "0", "status": "unpaid"}
        ]
        
        with patch('bot.get_credit_card_data', return_value=invalid_cards), \
             patch('bot.config') as mock_config, \
             patch('bot.bot_builder') as mock_bot_builder:
            
            mock_bot_builder.bot = AsyncMock()
            mock_config.ids_allowed_to_chat_with_bot = [123]
            
            await handle_credit_card_reminders(None)
            
            # Should not send any reminders for invalid data
            mock_bot_builder.bot.send_message.assert_not_called()


class TestDataValidationIntegration(unittest.TestCase):
    """Test data validation across different components."""
    
    def test_expense_item_data_validation(self):
        """Test ExpenseItem handles various data formats correctly."""
        # Test with various amount formats
        test_cases = [
            ("1,500.50", 1500.50),
            ("500", 500.0),
            ("", 0.0),
            ("invalid", 0.0),
            ("1,000", 1000.0)
        ]
        
        for amount_str, expected in test_cases:
            item = ExpenseItem(1, "24/07", "Test", amount_str)
            self.assertEqual(item.numeric_amount, expected, 
                           f"Failed for amount: {amount_str}")
    
    def test_date_format_consistency(self):
        """Test that date formats are handled consistently."""
        from bot import ist_date
        
        # Test IST date function
        result = ist_date()
        self.assertIsInstance(result, datetime)
        
        # Test date string format
        date_str = result.strftime("%d/%m")
        self.assertRegex(date_str, r'^\d{1,2}/\d{1,2}$')


if __name__ == '__main__':
    unittest.main(verbosity=2)
