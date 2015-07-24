import os
import sys
import json
import getpass
from codecs import open

import click
from path import path

from two1.debug import dlog
TWO1_CONFIG_FILE = path("~/.two1/two1.json")
TWO1_VERSION = "0.1"

class Config(object):

    def __init__(self, config_file=TWO1_CONFIG_FILE, config=None):
        self.file = path(config_file).expand().abspath()
        self.dir = self.file.parent
        self.load()
        dlog("Manual config = %s" % str(config))
        if config is not None:
            for key, value in config:
                setattr(self, key, value)

    def save(self):
        """Save config file, handling various edge cases."""
        if not self.dir.exists():
            self.dir.mkdir()
        if self.file.isdir():
            print("self.file=" + self.file)
            self.file.rmdir()
        with open(self.file, mode="w", encoding='utf-8') as fh:
            json.dump(self.defaults, fh, indent=2, sort_keys=True)
        return self

    def load(self):
        """Load config from (1) self.file if extant or (2) from defaults."""
        if not self.file.exists() or not self.file.isfile():
            self.defaults = dict(username=getpass.getuser(),
                                 sellprice=10000,
                                 contact="two1@21.co",
                                 stdout=".two1/two1.stdout",
                                 stderr=".two1/two1.stderr",
                                 bitin=".bitcoin/wallet.dat",
                                 bitout=".bitcoin/wallet.dat",
                                 sortby="price",
                                 maxspend=20000,
                                 verbose=False)
            self.save()
        else:
            with open(self.file, mode="r", encoding='utf-8') as fh:
                self.defaults = json.load(fh)
        for kk, vv in self.defaults.items():
            setattr(self, kk, vv)
        return self

    def log(self, msg, *args):
        """Logs a message to stderr."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stderr)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)

    def fmt(self):
        pairs = []
        for key in sorted(self.defaults.keys()):
            pairs.append("%s: %s" % (key, getattr(self, key)))
        out = "file: %s\n%s\n""" % (self.file, "\n".join(sorted(pairs)))
        return out

    def __repr__(self):
        return "<Config\n%s>" % self.fmt()

pass_config = click.make_pass_decorator(Config, ensure=True)
