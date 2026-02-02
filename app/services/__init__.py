"""app.services package initializer.

Keep this module lightweight: don't perform heavy initialization at import
time (like creating Google services). Tests import submodules under
`app.services` and expect import-time to be cheap.
"""

from . import google  # re-export the submodule for convenience

__all__ = [
    "google",
]
