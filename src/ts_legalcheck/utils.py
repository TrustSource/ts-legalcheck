import time
import logging

def time_it(f, *args, **kwargs):
    t = time.time()
    res = f(*args, **kwargs)
    return res, time.time() - t


def get_args(args):
    if len(args) == 1 and isinstance(args[0], list):
        return args[0]
    else:
        return list(args)


def setup_logging():
    logging.basicConfig(level=logging.DEBUG,
                        format='[%(levelname)s] %(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')