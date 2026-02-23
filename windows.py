import curses
import curses.textpad
import enum
import curses.ascii
import datetime
import calendar
import datetime

class mycalendar:
    def __init__(self, date):
        self.date = date
        self.cal = self.getcalendar(date)
        self.length = 8
        self.width = 20 

    def getcalendar(self, date: datetime.datetime):
        self.cal = calendar.month(date.year, date.month)
        self.calarray = [week.split() for week in self.cal.split('\n')]

    def print(self, win, strow, stcol, tasks={}, filters=[]):
        firstday = self.date.replace(day=1).weekday()
        attributes = curses.A_BOLD | curses.A_UNDERLINE
        win.addstr(strow, stcol, f'{self.calarray[0][0]} {self.calarray[0][1]}', attributes)
        win.addstr(strow+1, stcol, f'{" ".join(self.calarray[1][::])}')
        for row in range(2, len(self.calarray)):
            for col in range(0, len(self.calarray[row])):
                fshift = 0
                if row == 2:
                    fshift = 3*firstday
                datenum = self.calarray[row][col]
                if datenum in tasks:
                    if filters:
                        for filter in filters:
                            if filter in tasks[datenum]:
                                attribute = curses.A_REVERSE
                                break
                            else:
                                attribute = curses.A_NORMAL
                    else:
                        attribute = curses.A_REVERSE
                else:
                    attribute = curses.A_NORMAL
                r = strow+row
                c = stcol+(3*col)+fshift
                win.addstr(r, c, self.calarray[row][col], attribute)

class Bar:
    def __init__(self, size):
        self.bar = '|' + ' '*size + '|'
        self.size = size
        self.totalsize = self.size + 2

    def update(self, progress):
        if progress > 100:
            progress = 100
        if progress < 0:
            progress = 0
        barprog = round(progress / 100 * self.size)
        self.bar = '|' + '█'*barprog + ' '*(self.size-barprog) + '|'
        return self.bar

class Logger:
    '''Class to log all information to the same location'''
    debug = True
    logfile = 'log.log'

    @staticmethod
    def init():
        '''Clear the log file'''
        if Logger.debug:
            with open(Logger.logfile, 'w+') as l:
                l.write(f'{datetime.datetime.now()} - Starting new logger session\n')

    @staticmethod
    def log(msg):
        '''Log a message'''
        if Logger.debug:
            with open(Logger.logfile, 'a+') as l:
                l.write(f'{datetime.datetime.now()} - {msg}\n')


class Waction(enum.Enum):
    NEW = 0
    PUSH = 1
    POP = 2
    PASS = 3

def box(win, padx, pady, pos, msg=''):
    endrow = pos[0]+2+padx*2
    endcol = len(msg)+pos[1]+1+pady*2
    if msg:
        win.addstr(pos[0]+1+padx, pos[1]+1+pady, msg, curses.A_BOLD | curses.A_UNDERLINE)
    Logger.log(f'Rectangle: {pos} {endrow} {endcol}')
    curses.textpad.rectangle(win, pos[0], pos[1], endrow, endcol)
    return endrow+1, endcol+1

def option(stdscr, letter, msg, pos):
    opt = f'{letter}:'
    stdscr.addstr(pos[0], pos[1], opt , curses.A_BOLD)
    stdscr.addstr(pos[0], pos[1]+len(opt)+1, msg)
    return pos[0]+1, pos[1]+5+len(msg)+1
    
def tab(win, name, selected, pos):
    if selected:
        highlight = curses.A_BOLD
    else:
        highlight = curses.A_NORMAL
    win.addstr(pos[0], pos[1], '/ ', highlight)
    win.addstr(pos[0], pos[1]+2, name[0], curses.A_BOLD | curses.A_UNDERLINE)
    win.addstr(pos[0], pos[1]+3, name[1:]+' \\', highlight)
    return pos[0], pos[1]+2+len(name)+2

def separator(win, width, pos):
    for ix in range(width-3):
        win.addch(pos[0], pos[1]+ix, curses.ACS_HLINE)

class Editor:
    def __init__(self, pos, length, width, msg='', double=False):
        self.cancelled = False
        self.length = length
        self.width = width 
        self.pos = pos
        self.msg = msg
        self.double = double
        self.lastkey = 0

    def validator(self, ch):
        if ch == curses.ascii.NL or ch == curses.ascii.CR:
            if self.double:
                if self.lastkey == ord('\n'):
                    return curses.ascii.BEL
            else:
                return curses.ascii.BEL
        if ch == 27:
            self.cancelled = True
            return curses.ascii.BEL
        self.lastkey = ch
        return ch

    def gettext(self):
        curses.curs_set(1)
        Logger.log(f'Editor: rows:{self.length} cols:{self.width} pos:{self.pos}')
        win = curses.newwin(self.length, self.width, self.pos[0], self.pos[1])
        if self.msg:
            win.addstr(0, 0, self.msg)
        box = curses.textpad.Textbox(win)
        text = box.edit(self.validator).strip()
        curses.curs_set(0)
        if not self.cancelled:
            return text.replace('\n', '')
        else:
            return None

class Window:
    def __init__(self, row, col, length, width):
        self.done = False
        self.row = row
        self.col = col
        self.length = length
        self.width = width
        self.erow = 0
        self.ecol = 0
        self.mode = None
        self.win : curses.window = None
        try:
            self.win = curses.newwin(self.length, self.width, self.row, self.col)
        except Exception as e:
            self.win = None
            Logger.log(f'ERROR: {self} failed to create window! -> {e}')
        Logger.log(f'{self.__class__.__name__}:')
        Logger.log(f'\tRows: {self.length} Cols: {self.width}')
        Logger.log(f'\tStartR: {self.row} StartC: {self.col}')

    def draw(self):
        pass

    def input(self, _):
        return None,None

