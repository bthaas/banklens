import os
import json
from unittest.mock import MagicMock, patch

import pytest
from categorizer import categorize_transactions, BATCH_SIZE


@patch("categorizer.OpenAI")
def test_categorize_transactions_calls_openai(mock_openai_class):
    """Test that OpenAI is instantiated and called when mock mode is off."""
    # Setup environment
    with patch.dict(os.environ, {"BANKLENS_MOCK_MODE": "", "OPENAI_API_KEY": "fake-key"}):
        # Mock the client instance
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock the API response
        mock_message = MagicMock()
        mock_message.content = '{"categories": ["Food"]}'

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client.chat.completions.create.return_value = mock_completion

        # Action
        descriptions = ["Coffee"]
        categories = categorize_transactions(descriptions)

        # Assertions
        assert categories == ["Food"]
        mock_client.chat.completions.create.assert_called_once()


def test_mock_mode_is_deterministic():
    """Test that mock mode returns consistent results without API calls."""
    with patch.dict(os.environ, {"BANKLENS_MOCK_MODE": "true"}):
        descriptions = ["Coffee", "Rent", "Salary"]
        categories1 = categorize_transactions(descriptions)
        categories2 = categorize_transactions(descriptions)

        assert len(categories1) == 3
        assert categories1 == categories2  # Determinism check


@patch("categorizer._categorize_batch")
def test_batching_calls_helper_multiple_times(mock_batch_helper):
    """Verify that transactions are split into batches."""
    with patch.dict(os.environ, {"BANKLENS_MOCK_MODE": "", "OPENAI_API_KEY": "fake-key"}):
        with patch("categorizer.OpenAI"):  # prevent real client creation
            # Mock the helper to return dummy categories matching the batch size passed
            def side_effect(client, model, batch):
                return ["Mock"] * len(batch)

            mock_batch_helper.side_effect = side_effect

            # Input: 1.5 batches (e.g. 75 items if batch is 50)
            total_items = BATCH_SIZE + 25
            descriptions = ["Tx"] * total_items

            categories = categorize_transactions(descriptions)

            assert len(categories) == total_items
            assert mock_batch_helper.call_count == 2

            # Verify batch sizes
            # First call args: (client, model, batch)
            first_call_args = mock_batch_helper.call_args_list[0]
            assert len(first_call_args[0][2]) == BATCH_SIZE

            second_call_args = mock_batch_helper.call_args_list[1]
            assert len(second_call_args[0][2]) == 25
