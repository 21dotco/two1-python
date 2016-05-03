"""Make purchases in the 21 marketplace."""
import sys

from .market import Market

# Set the `mkt` module import to an instance of the `Market` object above
# https://mail.python.org/pipermail/python-ideas/2012-May/014969.html
sys.modules[__name__] = Market()
