'''
from colorama import just_fix_windows_console

from statusReporter import Script

just_fix_windows_console()

if __name__ == "__main__":
    s = Script.Script()
    s.main()
    '''

import curses
import engine
import sys
import os
import tintask

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--uninstall':
        print()
        print('TinTask is uninstalling...', end='')
        tintask.Database.delete()
        print('done!')
        print()
    else:
        curses.wrapper(engine.Engine.run)
