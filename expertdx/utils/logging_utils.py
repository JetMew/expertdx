import os
import yaml
import logging
import logging.config


def _create_logger(name):
    return logging.getLogger(name)


def get_logger(name):
    logger = _create_logger(name)
    return logger


def setup_logger(output_file=None, logging_config=None):
    if logging_config is not None:
        if output_file is not None:
            logging_config['handlers']['file_handler']['filename'] = output_file
        logging.config.dictConfig(logging_config)
    else:
        with open(os.path.join(os.path.dirname(__file__), 'logging.yaml'), 'r') as fh:
            logging_config = yaml.safe_load(fh)
        if output_file is not None:
            logging_config['handlers']['file_handler']['filename'] = output_file
        logging.config.dictConfig(logging_config)

