#!/usr/bin/python
import os
import sys
import json
from lib.txn import Transaction

def main(args=None):
    if args is None:
        args = sys.argv[1:]

hexStr = input("Input Bitcoin transaction hex: ")
tx, _ = Transaction.from_bytes(bytes.fromhex(hexStr))
jsonobj = Transaction.__json__(tx)

print ("\nTransaction data")
print(json.dumps(jsonobj, indent=4))
print("\n")

if __name__ == "__main__":
    main()
