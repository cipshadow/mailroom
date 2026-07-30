"""PyInstaller's Analysis wants a script, not a module, as its entry point -
this is that script. Everything real lives in kindle_mailroom.desktop."""

import sys

from kindle_mailroom.desktop import main

if __name__ == "__main__":
    sys.exit(main())
