import logging.config
import os
import warnings
import yaml

__author__ = 'Ali'


def load_configs():
    # set configs based on the server mode
    TEST_MODE = False
    IS_DEBUG = True

    script_dir = os.path.dirname(__file__)
    log_config_path = os.path.join(script_dir, "logger_config.yaml")
    with open(log_config_path, 'rt') as f:
        config = yaml.load(f.read())

    config["handlers"]["file_handler"]["filename"] = os.path.join(script_dir, "logs/app.log")
    logging.config.dictConfig(config)
    if IS_DEBUG:
        # os.environ['PYTHONASYNCIODEBUG'] = '1'
        # logging.basicConfig(level=logging.DEBUG)
        warnings.filterwarnings("default", category=ResourceWarning, append=True)

    return TEST_MODE
