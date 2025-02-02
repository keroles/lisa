from lisa.version import __version__

import warnings
# Raise an exception when a deprecated API is used from within a lisa.*
# submodule. This ensures that we don't use any deprecated APIs internally, so
# they are only kept for external backward compatibility purposes.
warnings.filterwarnings(
    action='error',
    category=DeprecationWarning,
    module=r'{}\..*'.format(__name__),
)

# When the deprecated APIs are used from __main__ (script or notebook), always
# show the warning
warnings.filterwarnings(
    action='always',
    category=DeprecationWarning,
    module=r'__main__',
)

# vim :set tabstop=4 shiftwidth=4 textwidth=80 expandtab
