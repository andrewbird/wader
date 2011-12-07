from wader.common.backends import BACKEND_LIST

from core.backends.nm import nm_backend
from core.backends.plain import plain_backend

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
