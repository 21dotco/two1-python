# 3rd party imports
import click
import pytest

# two1 imports
import two1.commands.login as login
import two1.commands.log as log
import two1.commands.status as status
import two1.commands.mine as mine
import two1.commands.util.uxstring as uxstring
# import two1.commands.util.bitcoin_computer as bitcoin_computer


@pytest.mark.integration
def test_mine_log(patch_click, config, rest_client, machine_auth_wallet, username, password):
    # first log into the test account given by PASSWORD and USER_NAME
    login.login_account(config, machine_auth_wallet, username, password)
    click.confirm.assert_called_with(uxstring.UxString.analytics_optin)

    # cannot make an assumption of zero balance for now
    pre_status_dict = status._status(config, rest_client, machine_auth_wallet.wallet, False)
    pre_balance = pre_status_dict['wallet']['wallet']['twentyone_balance']

    # run mine to get an expected amount of off chain balance
    mine._mine(config, rest_client, machine_auth_wallet.wallet)

    # Status now should have an offchain balance
    post_status_dict = status._status(config, rest_client, machine_auth_wallet.wallet, False)
    post_balance = post_status_dict['wallet']['wallet']['twentyone_balance']

    # payout is higher for BCs
    # FIXME: prod temporarily has the payout at 20k
    payout = 20000
    # payout = 20000 if bitcoin_computer.has_mining_chip() else 10000

    # esure payout shows in status
    assert post_balance == pre_balance + payout

    # check logs to ensure payout is theres
    logs = log.get_bc_logs(rest_client, False)
    assert str(payout) in logs[1]
