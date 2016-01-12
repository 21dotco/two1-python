import logging


DEFAULT_FEE_PER_KB = 10000  # Satoshis

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
DUST_LIMIT = int(DUST_LIMIT_PER_KB * 0.18 * 3)

_fee_session = None
_fee_host = "http://api.cointape.com/"

logger = logging.getLogger('wallet')


def get_fees():
    global _fee_session

    fee_per_kb = DEFAULT_FEE_PER_KB

    if _fee_session is None:
        import requests
        _fee_session = requests.Session()

    try:
        r = _fee_session.request("GET",
                                 _fee_host + "v1/fees/recommended")
        if r.status_code == 200:
            fee_per_kb = r.json()['halfHourFee'] * 1000
    except Exception as e:
        logger.error(
            "Error getting recommended fees from server: %s. Using defaults." %
            e)

    return dict(per_kb=fee_per_kb,
                per_input=int(DEFAULT_INPUT_SIZE_KB * fee_per_kb),
                per_output=int(DEFAULT_OUTPUT_SIZE_KB * fee_per_kb))
