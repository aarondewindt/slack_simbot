import sys


def guard(func):
    def decorator(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except:
            if self.debug:
                raise
            else:
                return sys.exc_info()
    return decorator
