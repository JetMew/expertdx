import pdb
import functools


def debug_on_end(func):
    debug = False

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if debug:
            pdb.set_trace()
        return result

    return wrapper