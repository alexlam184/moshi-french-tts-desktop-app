"""PyInstaller entry point for the macOS application bundle.

This file deliberately imports the package instead of executing
``french_learning_app/__main__.py`` as a loose script.  That preserves the
package context required by its relative imports once it is inside a .app.
"""

from french_learning_app.app import main


if __name__ == "__main__":
    raise SystemExit(main())
