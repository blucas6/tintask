import curses
import engine
import sys
import os
import tintask

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--uninstall':
        print()
        print('TinTask is uninstalling...', end='')
        tintask.InstallManager.uninstall()
        print('done!')
        print()
    else:
        if getattr(sys, 'frozen', False):
            tintask.InstallManager.filetype = 'executable'
        else:
            tintask.InstallManager.filetype = 'script'
        if sys.platform == 'win32':
            os.environ['ESCDELAY'] = '25'
        curses.wrapper(engine.Engine.run)
