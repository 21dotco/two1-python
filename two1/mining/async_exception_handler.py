import logging


def handle_exception(exception):
    logger = logging.getLogger(__name__)

    # sys.exec_info MAGIC. It will figure out the info about the exception being currently handle
    # from the argument automagically
    logger.exception("Unhandled Global Exception")
