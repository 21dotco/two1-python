"""Flush command unit tests. """
from two1.commands import flush


def test_flush(mock_rest_client, mock_wallet, patch_click):
    """Test standard flush."""
    flush._flush(mock_rest_client, mock_wallet)
