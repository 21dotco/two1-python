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
import pkg_resources 

TWO1_CONFIG_FILE = path("~/.two1/two1.json")
TWO1_PURCHASES_FILE = path("~/.two1/purchases.json")
TWO1_HOST = "http://twentyone-devel-1d3c.herokuapp.com"
#TWO1_HOST = "http://127.0.0.1:8000"

try:
    TWO1_VERSION = pkg_resources.require("two1")[0].version
except:
    TWO1_VERSION = "undefined"
    

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
        #override config variables
        for k,v in config:
            self.defaults[k]=v

        if self.verbose:
            self.vlog("Applied manual config.")
            for k,v in config:
                self.vlog("  {}={}".format(k,v))

        #add wallet object
        self.wallet = electrumWallet.ElectrumWallet()          

        #create an empty purchases file if it does not exist
        self.purchases_file = path(TWO1_PURCHASES_FILE).expand().abspath()
        if self.purchases_file.exists() and self.purchases_file.isfile():
            pass
        else:
            with open(self.purchases_file, mode='w', encoding='utf-8') as f:
                pass

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

    # kwargs is styling parameters
    def log(self, msg, *args,**kwargs):
        """Logs a message to stderr."""
        if args:
            msg %= args
        if len(kwargs) > 0:
            out = click.style(msg,**kwargs)
        else:
            out = msg
        click.echo(out, file=sys.stderr)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)

    def log_purchase(self,**kwargs):
        #simple logging to file
        #this can be replaced with pickle/sqlite
        with open(self.purchases_file, mode='a', encoding='utf-8') as pjson:
            pjson.write(json.dumps(kwargs)+"\n")

    def get_purchases(self):
        #read all right now. TODO: read the most recent ones only
        try:
            with open(self.purchases_file, mode='r', encoding='utf-8') as pjson:
                content = pjson.readlines()
            return [json.loads(n) for n in content]
        except:
            dlog("Error: Could not load purchases.")
            return []

        


    def fmt(self):
        pairs = []
        for key in sorted(self.defaults.keys()):
            pairs.append("%s: %s" % (key, self.defaults[key]))
        out = "file: %s\n%s\n""" % (self.file, "\n".join(sorted(pairs)))
        return out

    def __repr__(self):
        return "<Config\n%s>" % self.fmt()

pass_config = click.make_pass_decorator(Config, ensure=False)
