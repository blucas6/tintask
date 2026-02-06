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
        if sys.platform == 'win32':
            os.environ['ESCDELAY'] = '25'
        curses.wrapper(engine.Engine.run)
