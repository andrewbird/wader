from wader.common.backends.nm import nm_backend
from wader.common.backends.plain import plain_backend

BACKEND_LIST = ['nm_backend', 'plain_backend']

__backend = None


def get_backend():
    global __backend
    if __backend is not None:
        return __backend

    for name in BACKEND_LIST:
        backend = globals()[name]
        if backend.should_be_used():
            __backend = backend
            return __backend
