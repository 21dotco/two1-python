import os
import sys
import json
import getpass
from codecs import open

import click
from path import path
from two1.wallet import electrumWallet
from two1.debug import dlog
from two1.uxstring import UxString

TWO1_CONFIG_FILE = path("~/.two1/two1.json")
TWO1_VERSION = "0.1"
TWO1_HOST = "http://127.0.0.1:8000"

'''Primary use case for the following class is the singleton that holds
   all the state & config data required to run commands and subcommands 
   for two1 app
'''
class Config(object):

    def __init__(self, config_file=TWO1_CONFIG_FILE, config=None):
        self.file = path(config_file).expand().abspath()
        self.dir = self.file.parent
        self.defaults = {}
        self.load()
        dlog("Manual config = %s" % str(config))
        #add wallet object
        self.wallet = electrumWallet.ElectrumWallet()          

    #pulls attributes from the self.defaults dict
    def __getattr__(self, name):
        if name in self.defaults:
            return self.defaults[name]
        else:
            # Default behaviour
            raise AttributeError

    def save(self):
        """Save config file, handling various edge cases."""
        if not self.dir.exists():
            self.dir.mkdir()
        if self.file.isdir():
            print("self.file=" + self.file)
            self.file.rmdir()
        with open(self.file + ".tmp", mode="w", encoding='utf-8') as fh:
            json.dump(self.defaults, fh, indent=2, sort_keys=True)
        #move file if successfully written
        os.rename(self.file+".tmp",self.file)
        return self

    def load(self):
        """Load config from (1) self.file if extant or (2) from defaults."""
        if self.file.exists() and self.file.isfile():
            try:
                with open(self.file, mode="r", encoding='utf-8') as fh:
                    self.defaults = json.load(fh)
            except:
                print(UxString.Errorself.file_load % self.file)
                self.defaults = {}

        defaults = dict(username=getpass.getuser(),
                                 sellprice=10000,
                                 contact="two1@21.co",
                                 stdout=".two1/two1.stdout",
                                 stderr=".two1/two1.stderr",
                                 bitin=".bitcoin/wallet.dat",
                                 bitout=".bitcoin/wallet.dat",
                                 sortby="price",
                                 maxspend=20000,
                                 verbose=False,
                                 mining_auth_pubkey=None)


        save_config = False
        for key,default_value in defaults.items():
            if key not in self.defaults:
                self.defaults[key]=default_value
                save_config=True

        if save_config:
            self.save()

        return self

    def update_key(self,key,value):
        self.defaults[key] = value
        #might be better to switch to local sqlite for persisting 
        #the config
        #self.save()


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
            pairs.append("%s: %s" % (key, self.defaults[key]))
        out = "file: %s\n%s\n""" % (self.file, "\n".join(sorted(pairs)))
        return out

    def __repr__(self):
        return "<Config\n%s>" % self.fmt()

pass_config = click.make_pass_decorator(Config, ensure=False)
