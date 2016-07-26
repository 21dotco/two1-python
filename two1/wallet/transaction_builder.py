from collections import defaultdict
from collections import deque

from two1.wallet import fees
from two1.wallet import exceptions


def pack_wallets(wallets, addresses_and_amounts):
    '''
        Pack a list of wallets with transactions, greedily in the order given,
        splitting a payout across multiple wallets if it doesn't fit. Return the built
        transactions and the payouts that don't fit even after splitting.

        inputs:
            wallets: [Two1Wallet]
            addresses_and_amounts: [(string, int)]
        outputs:
            ([TransactionBuilder], [(string, int)])
        throws:
            DustLimitError: a given amount does not exceed the dust limit.

        Output consists of a list of TransactionBuilders, one for each input wallet,
        and a list of address/amount pairs that do not fit in any wallet even
        after splitting.
    '''
    if len(set(wallets)) != len(wallets):
        raise Exception('Passed in duplicate wallets')

    builders = [TransactionBuilder(wallet) for wallet in wallets]
    payouts = deque(addresses_and_amounts)

    for builder in builders:
        try:
            while payouts:
                address, amount = payouts.popleft()
                builder.add(address, amount)
        except exceptions.OverfullTransactionException as e:
            # ensure what's left after splitting this payout exceeds the dust limit
            overage = max(e.args[0]['overage'], fees.DUST_LIMIT + 1000)
            amount_that_fits = amount - overage

            try:
                builder.add(address, amount_that_fits)
                payouts.appendleft((address, overage))
            except exceptions.DustLimitError:
                payouts.appendleft((address, amount))

    return builders, list(payouts)


class TransactionBuilder(object):
    def __init__(self, wallet):
        '''
            A TransactionBuilder object allows one to build a transaction by adding
            additional outputs step by step, recalculating fees along the way. If
            an added output would exceed the wallet's capacity to pay, TransactionBuilder
            raises an exception. This allows one to easily fill up a set of wallets with
            batched payments as follows.

                builders = [TransactionBuilder(wallet) for wallet in wallets]
                added_payouts = set()
                for payout in payouts:
                    for builder in builders:
                        if payout in added_payouts:
                            break

                        try:
                            builder.add(payout.address, payout.amount)
                            added_payouts.add(payout)
                        except exceptions.OverfullTransactionException:
                            continue

                for builder in builders:
                    builder.execute_transaction()

            The TransactionBuilderException also includes in its args a dictionary
            with additional information you can use to split transactions across multiple
            wallets. For example, it includes the `'overage'` key which includes the
            amount you've exceeded beyond the wallet's balance. This allows one to cap off
            a wallet as follows.

                try:
                    builder.add(payout_address, amount)
                except exceptions.OverfullTransactionException as e:
                    message_dict = e.args[0]
                    amount -= message_dict['overage']
                    if amount < fees.DUST_LIMIT:
                        return

                try:
                    builder.add(payout_address, amount)
                except exceptions.DustLimitError:
                    # handle DustLimitError

            Overage information isn't easy to query before trying to add an output,
            because the fee depends on the number of UTXOs in the wallet, and new utxos
            may or may not need to be spent for an additional output. So use the try/except
            style.

            The transaction_builder module has a pack_wallets function that
            intelligently packs wallets using the TransactionBuilder
        '''
        self.wallet = wallet
        self.current_fees = 0
        self._addresses_and_amounts = defaultdict(int)
        self.selected_utxos = {}  # {address: [utxo]}

    @property
    def subtotal(self):
        ''' Subtotal transaction amount (excluding fees) '''
        return sum(v for (a, v) in self.addresses_and_amounts.items())

    @property
    def total(self):
        ''' Total transaction amount (including fees) '''
        return self.subtotal + self.current_fees

    @property
    def spendable_balance(self):
        utxos_by_addr = self.wallet.get_utxos()
        _spendable_balance = sum(
            sum(u.value for u in utxos) for _, utxos in utxos_by_addr.items()
        )
        return _spendable_balance

    @property
    def remaining_balance(self):
        return self.spendable_balance - self.total

    @property
    def addresses_and_amounts(self):
        # strip out the zeros introduced by defaultdict
        return {
            a: v for (a, v) in self._addresses_and_amounts.items() if v > 0
        }

    def __len__(self):
        return len([a for (a, v) in self.addresses_and_amounts.items()])

    def __repr__(self):
        return '<TransactionBuilder: {}>'.format(repr(self.addresses_and_amounts))

    def _rebuild(self):
        '''
            Check if the current transaction can be sent as is,
            and throw an exception if not.
        '''
        for address, amount in self.addresses_and_amounts.items():
            if amount < fees.DUST_LIMIT:
                raise exceptions.DustLimitError(amount)

        amount = self.subtotal
        if amount == 0:
            self.current_fees = 0
            self.selected_utxos = {}
            return

        selected_utxos, txn_fees = self.wallet.utxo_selector(
            utxos_by_addr=self.wallet.get_utxos(),
            amount=amount,
            num_outputs=len(self),
        )

        if not selected_utxos:
            raise exceptions.OverfullTransactionException({
                'amount': amount,
                'fee': txn_fees,
                'spendable_balance': self.spendable_balance,
                'overage': abs(self.spendable_balance - amount - txn_fees),
            })

        self.current_fees = txn_fees
        self.selected_utxos = selected_utxos

    def add(self, address, amount):
        '''
            Try to add the amount `amount` to the payout to `address`.
            If the resulting amount does not fit in the wallet, or
            the resulting amount paid to that address is less than the
            dust limit, raise an exception

            raises:
                DustLimitError: if the resulting amount being paid to `address` is
                                below the dust limit
                OverfullTransactionException: if the resulting transaction does not
                                              fit in the wallet.
        '''
        old_amount = self._addresses_and_amounts[address]
        self._addresses_and_amounts[address] += amount

        try:
            self._rebuild()
        except (exceptions.TransactionBuilderException, exceptions.DustLimitError):
            self._addresses_and_amounts[address] = old_amount
            raise

    def remove(self, address, amount='all'):
        '''
            Try to subtract `amount` from the payout to `address`.
            If `amount` is 'all', then this address is removed
            from the transaction.

            raises:
                DustLimitError: if the resulting amount being paid to `address` is
                                below the dust limit
                OverfullTransactionException: if the resulting transaction does not
                                              fit in the wallet.
        '''
        old_amount = self._addresses_and_amounts[address]

        if amount == 'all':
            new_amount = 0
        elif old_amount - amount < 0:
            new_amount = 0
        else:
            new_amount = old_amount - amount

        self._addresses_and_amounts[address] = new_amount

        try:
            self._rebuild()
        except (exceptions.TransactionBuilderException, exceptions.DustLimitError):
            self._addresses_and_amounts[address] = old_amount
            raise

    def execute_transaction(self):
        if not self.addresses_and_amounts:
            raise exceptions.TransactionBuilderException("Can't execute an empty transaction")

        return self.wallet.send_to_multiple(self.addresses_and_amounts)
