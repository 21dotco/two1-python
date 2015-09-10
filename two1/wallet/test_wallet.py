from two1.wallet.base_wallet import BaseWallet


class TestWallet(BaseWallet):
    def sign_transaction(self, tx):
        return '0b091c9568c1bc9d683f0ea603a6b8c9efb03a3ed8a1867eb972717d78c8682d'

    def confirmed_balance(self):
        return 100000

    def config_options(self):
        return {}

    def addresses(self):
        return ['18oTQdbxnmUU5DntHjWu96hkwjm9wsbB8E']

    def send_to(self, address, amount):
        return '0b091c9568c1bc9d683f0ea603a6b8c9efb03a3ed8a1867eb972717d78c8682d'

    def make_signed_transaction_for(self, address, amount):
        return '0b091c9568c1bc9d683f0ea603a6b8c9efb03a3ed8a1867eb972717d78c8682d'

    def broadcast_transaction(self, tx):
        return '0b091c9568c1bc9d683f0ea603a6b8c9efb03a3ed8a1867eb972717d78c8682d'

    def current_address(self):
        return '18oTQdbxnmUU5DntHjWu96hkwjm9wsbB8E'

    def unconfirmed_balance(self):
        return 100000

    def is_configured(self):
        return True

    def configure(self, config_options):
        pass

    # TODO probably should not be here, but config.py calls it
    def start_daemon(self):
        return True
