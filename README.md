txHex2JSON
decode a raw hex Bitcoin transaction to a readable JSON data set

--python 3.4+ is required

Installaion (Ubuntu/Debian):

sudo sh install.sh

Run:

./txHex2JSON

Example:

./txHex2JSON

Input Bitcoin transaction hex: 0100000001000000000000000000000000000000000000000000000
0000000000000000000ffffffff0704ffff001d0136ffffffff0100f2052a01000000434104fcc2888ca91
cf0103d8c5797c256bf976e81f280205d002d85b9b622ed1a6f820866c7b5fe12285cfa78c035355d752fc
94a398b67597dc4fbb5b386816425ddac00000000

Transaction data
{
    "Outputs": [
        "TransactionOutput(Value: 5000000000 satoshis Script: 0x04fcc2888ca91cf0103d8c5797c256bf976e81f280205d002d85b9b622ed1a6f820866c7b5fe12285cfa78c035355d752fc94a398b67597dc4fbb5b386816425dd OP_CHECKSIG)"
    ],
    "Inputs": [
        "TransactionInput(Outpoint: 0000000000000000000000000000000000000000000000000000000000000000 Outpoint Index: 4294967295 Script: 0xffff001d 0x36 Sequence: 4294967295)"
    ],
    "Version": 1,
    "Locktime": 0
}


