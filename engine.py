import curses
import tintask
import windows
import sys

class Engine:
    winstack = []
    modals = []
    name = ''

    @staticmethod
    def errormsg():
        curses.endwin()
        print()
        print('--------------------------------------')
        print('| TinTask ERROR:                     |')
        print('|                                    |')
        print('|  A catastrophic error has occurred |')
        print('|  Please check the logs             |')
        print('--------------------------------------')
        print()

    @staticmethod
    def setup(stdscr):
        end_column = round(curses.COLS/2)
        minimum_columns = 40
        if end_column < minimum_columns:
            end_column = minimum_columns
        else:
            sidemenu = tintask.SideMenu(0,
                                        end_column+1,
                                        curses.LINES-1,
                                        curses.COLS-end_column-1)
            sidemenu.mode = 'report'
            Engine.winstack.append(sidemenu)
        main = tintask.TinTask(0, 0, curses.LINES-1, end_column)
        tintask.StatusBar.setup(curses.LINES-1, curses.COLS-1, stdscr)
        Engine.winstack.append(main)
        install = tintask.Install(0, 0, curses.LINES, curses.COLS)
        if not install.verify():
            install.setup()
            #Engine.modals.append(install)

    @staticmethod
    def run(stdscr):
        windows.Logger.init()
        if sys.platform != 'win32':
            curses.set_escdelay(25)
        curses.curs_set(0)
        stdscr.keypad(True)
        windows.Logger.log(f'Terminal size [{curses.LINES},{curses.COLS}]')
        stdscr.refresh()
        try:
            Engine.setup(stdscr)
        except Exception as e:
            windows.Logger.log(f'Engine exception: {e}')
            Engine.errormsg()
            return

        while True:

            for win in Engine.winstack:
                win.win.erase()
                win.draw()
                win.win.noutrefresh()

            for win in Engine.modals:
                win.win.erase()
                win.draw()
                win.win.noutrefresh()

            if Engine.modals and Engine.modals[-1].done:
                Engine.modals.pop()
                continue

            curses.doupdate()

            ch = stdscr.getch()

            action = None
            if Engine.modals:
                next_win,action = Engine.modals[-1].input(ch)
            else:
                for win in Engine.winstack:
                    nwin,nact = win.input(ch)
                    if nwin:
                        next_win,action = nwin,nact

            if action == windows.Waction.NEW:
                Engine.winstack = [next_win]
            elif action == windows.Waction.PUSH:
                #Engine.winstack.append(next_win)
                Engine.modals.append(next_win)
            elif action == windows.Waction.POP and len(Engine.winstack) > 1:
                #Engine.winstack.pop()
                Engine.modals.pop()

