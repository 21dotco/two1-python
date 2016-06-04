"""Flush command unit tests. """
from two1.commands import flush


def test_flush(mock_rest_client, mock_wallet, mock_machine_auth, patch_click):
    """Test standard flush."""
    flush._flush(client=mock_rest_client, wallet=mock_wallet, machine_auth=mock_machine_auth,
                 amount=0, payout_address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", silent=True,
                 to_primary=False)
