#!/usr/bin/python
import os
import sys
from lib.txn import Transaction
def main(args=None):
    """The main routine."""
    if args is None:
        args = sys.argv[1:]

    hexStr = raw_input("Input transaction hex: ")

if __name__ == "__main__":
    main()
