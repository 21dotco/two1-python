"""Flush command unit tests. """
from two1.commands import flush


def test_flush(mock_config, mock_rest_client, mock_wallet, patch_click):
    """Test standard flush."""
    flush._flush(mock_config, mock_rest_client, mock_wallet)
