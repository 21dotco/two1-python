import click


from two1.commands.config import pass_config
from two1.lib.server.analytics import capture_usage


@click.command(context_settings=dict(
    ignore_unknown_options=True,
))
@click.option('--file', type=click.File('rb'))
@click.option('--price', type=click.INT)
@click.option('--store')
@pass_config
def sell_file(config, file, price, store):
    """
    Upload file to sell to selected file store.
    """
    _sell_file(config, file, price, store)


@capture_usage
def _sell_file(config, file, price, store):
    import requests
    try:
        file_name = extract_file_name(file.name)
        config.log(
            'Publishing {} file for sale in {} store. Price: {}.'.format(
                file_name, store, price
            )
        )

        response = requests.post(
            store,
            headers = {'Return-Wallet-Address': config.wallet.current_address},
            data={'price': price},
            files={'file': (file_name, file)}
        )

        if response.status_code != 201:
            config.log('Error status: %s' % response.status_code)
            config.log('Error reason: %s' % response.reason)
            return

        print(response)
        print(response.text)

    except Exception as e:
        raise click.ClickException(e)
def extract_file_name(f_name):
    try:
        return f_name.split('/')[-1]
    except:
        return f_name
