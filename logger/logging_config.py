import logging
import os


def get_logger(_dir, name=__file__, console_level=logging.INFO):
    _dir = os.path.join('log', _dir)
    os.makedirs(_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to INFO
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    # create formatter
    formatter = logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s]: %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)
    # file version of console output
    chf = logging.FileHandler(os.path.join(_dir, 'console.log'))
    chf.setLevel(console_level)
    chf.setFormatter(formatter)
    logger.addHandler(chf)

    # create error file handler and set level to WARNING
    eh = logging.FileHandler(os.path.join(_dir, 'error.log'))
    eh.setLevel(logging.WARNING)
    eh.setFormatter(formatter)
    logger.addHandler(eh)

    # create debug file handler and set level to DEBUG
    dh = logging.FileHandler(os.path.join(_dir, 'debug.log'))
    dh.setLevel(logging.DEBUG)
    dh.setFormatter(formatter)
    logger.addHandler(dh)

    return logger
