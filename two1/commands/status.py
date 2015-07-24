import click
from two1.config import pass_config
from two1.debug import dlog

@click.command()
@click.option('--private',
              is_flag=True,
              default=False,
              help='Show private keys.')
@pass_config
def status(config, private):
    """View earned Bitcoin and configuration"""
    dlog("Entered status")
    foo = config.fmt()
    print("\nConfig\n------\n" + foo)
    config.log("Invoked config.log")
    click.echo("config.verbose = %s" % config.verbose)
    config.vlog("Invoked config.vlog")
    
