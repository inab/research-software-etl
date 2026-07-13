# Makes `tests` a regular package so `from tests.application... import ...` resolves
# to this directory. Without it, the top-level `tests` package that webdriver-manager
# installs into site-packages shadows this one -- a regular package always wins over
# a namespace package, regardless of sys.path order.
