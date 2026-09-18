"""
Unit tests for api/admin_pages.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from api.admin_pages import (
    list_candidates,
    set_page_status,
)


def test_list_candidates_invalid_site_id():
    """Test that invalid site_id raises ValueError."""
    with pytest.raises(ValueError, match="Invalid site_id"):
        list_candidates("nonexistent_site")


def test_set_page_status_invalid_site_id():
    """Test that invalid site_id raises ValueError."""
    with pytest.raises(ValueError, match="Invalid site_id"):
        set_page_status("nonexistent_site", "https://example.com", "included")


def test_set_page_status_invalid_status():
    """Test that invalid status raises ValueError."""
    with pytest.raises(ValueError, match="Invalid status"):
        set_page_status("ness", "https://example.com", "invalid_status")


def test_set_page_status_valid_values():
    """Test that valid status values are accepted."""
    with patch("api.admin_pages.get_dynamodb_table") as mock_table:
        mock_table_instance = MagicMock()
        mock_table.return_value = mock_table_instance

        # Should not raise
        for status in ["included", "excluded", "pending"]:
            set_page_status("ness", "https://example.com", status)
            # Verify update was called
            assert mock_table_instance.update_item.called


def test_list_candidates_calls_dynamodb(monkeypatch):
    """Test that list_candidates queries DynamoDB."""
    monkeypatch.setenv("DYNAMODB_TABLE_CANDIDATES", "page_candidates")

    with patch("api.admin_pages.get_dynamodb_table") as mock_table:
        mock_table_instance = MagicMock()
        mock_table_instance.query.return_value = {"Items": []}
        mock_table.return_value = mock_table_instance

        list_candidates("ness")

        # Verify query was called with correct parameters
        mock_table_instance.query.assert_called_once()
        call_args = mock_table_instance.query.call_args
        assert call_args.kwargs["KeyConditionExpression"] == "site_id = :site_id"
