import click
from two1.config import pass_config

@click.command()
@pass_config
def publish():
    """Publish your endpoint to the MMM"""
    import sys
    import time
    sys.stderr.write("\x1b[35mloading[" + " "*10 + "]\x1b[0m\r")
    sys.stderr.write("\x1b[8C")
    for i in range(10):
        sys.stderr.write('.')
        time.sleep(1)
    sys.stderr.write('\n')
    return
