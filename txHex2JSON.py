#!/usr/bin/python
import os
import sys
from lib.txn import Transaction
def main(args=None):
    """The main routine."""
    if args is None:
        args = sys.argv[1:]

hexStr = input("Input transaction hex: ")
tx = Transaction.from_bytes(bytes.fromhex(hexStr))

if __name__ == "__main__":
    main()
