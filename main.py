import curses
import engine
import sys
import os
import tintask

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        tintask.InstallManager.filetype = 'executable'
        os.chdir(os.path.dirname(sys.executable))
    else:
        tintask.InstallManager.filetype = 'script'
    if len(sys.argv) > 1 and sys.argv[1] == '--uninstall':
        print()
        print('TinTask is uninstalling...', end='')
        try:
            tintask.InstallManager.uninstall()
            print('done!')
            print()
        except Exception as e:
            print()
            print('Failed to uninstall, please check logs!')
    else:
        if sys.platform == 'win32':
            os.environ['ESCDELAY'] = '25'
        try:
            curses.wrapper(engine.Engine.run)
        except SystemExit:
            pass
