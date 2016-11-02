import logging
import requests

from two1.wallet import exceptions

DEFAULT_FEE_PER_KB = 100000  # Satoshis

# Each txn input is ~150 bytes:
# outpoint: 32 bytes
# outpoint index: 4 bytes
# signature: 77-78 bytes
# compressed public key: 33 bytes
# sequence num: 4 bytes
DEFAULT_INPUT_SIZE_KB = 0.15

# Each txn output is ~40 bytes, thus 0.04
DEFAULT_OUTPUT_SIZE_KB = 0.04

DUST_LIMIT_PER_KB = 5000  # satoshis
# Dust limit is Min fee for 180 bytes * 3
# The 3 is a magic number in Bitcoin Core
# cf. https://github.com/bitcoin/bitcoin/blob/28ad4d9fc2be102786a8c6c32ebecb466b2a03dd/src/primitives/transaction.h#L175
DUST_LIMIT = int(DUST_LIMIT_PER_KB * 0.20 * 3)

_fee_host = "https://bitcoinfees.21.co/"

logger = logging.getLogger('wallet')


def get_fees():
    try:
        response = requests.get(_fee_host + "v1/fees/recommended")
        if response.status_code == 200:
            fee_per_kb = response.json()['halfHourFee'] * 1000
        else:
            raise requests.ConnectionError('Received status_code %d' % response.status_code)
    except requests.RequestException as error:
        fee_per_kb = DEFAULT_FEE_PER_KB
        logger.error(
            "Error getting recommended fees from server: %s. Using defaults." %
            error)

    if not 0 <= fee_per_kb <= 2 * DEFAULT_FEE_PER_KB:
        raise exceptions.UnreasonableFeeError(
            'Unreasonable fee per kB: %s' % fee_per_kb)

    return {
        'per_kb': fee_per_kb,
        'per_input': int(DEFAULT_INPUT_SIZE_KB * fee_per_kb),
        'per_output': int(DEFAULT_OUTPUT_SIZE_KB * fee_per_kb)
    }
