"""Flush command unit tests. """
from two1.commands import flush


def test_flush(mock_rest_client, mock_wallet, patch_click):
    """Test standard flush."""
    flush._flush(mock_rest_client, mock_wallet, 0, "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
