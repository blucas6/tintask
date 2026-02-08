import calendar
import math
import curses
import windows
import os
import sqlite3
import datetime
import dateutil.relativedelta
import sys

class DBTables:
    tasks = 'tasks'
    config = 'config'
    tags = 'tags'
    tasks_columns = 'date DATE, tag TEXT, task TEXT'
    tags_columns = 'tag TEXT, active bool'
    config_columns = 'mailto TEXT, subject TEXT, footer TEXT, signature TEXT'

class Install(windows.Window):
    def __init__(self, row, col, length, width):
        super().__init__(row, col, length, width)
        self.bar = windows.Bar(30)

    def verify(self):
        try:
            Manager.start()
        except:
            return False
        return True

    def setuptables(self):
        if not Database.checktable(DBTables.tasks):
            Database.createtable(DBTables.tasks, DBTables.tasks_columns)
        if not Database.checktable(DBTables.config):
            Database.createtable(DBTables.config, DBTables.config_columns)
        if not Database.checktable(DBTables.tags):
            Database.createtable(DBTables.tags, DBTables.tags_columns)
    
    def step(self, func, msg):
        windows.Logger.log(f'Install step: {msg}')
        self.win.addstr(4, 1, ' '*50)
        self.win.addstr(4, 1, msg)
        if func:
            func()
        else:
            windows.Logger.log(f'Install step: {func} is null')
        self.win.addstr(5, 1, self.bar.update(60))
        self.win.noutrefresh()
        curses.doupdate()
        curses.napms(1000)
    
    def setup(self):
        self.win.addstr(0, 0, 'TINTASK IS INSTALLING...')
        self.win.addstr(5, 1, self.bar.update(0))
        self.win.noutrefresh()
        curses.doupdate()
        curses.napms(1000)
        try:
            self.step(Database.connect, 'Creating storage space...')
            self.step(self.setuptables, 'Making tables...')
            self.win.addstr(4, 1, ' '*50)
            self.win.addstr(4, 1, 'Final check...')
            if not Database.sanitycheck():
                raise Exception('Database tables could not be created!')
            self.win.addstr(5, 1, self.bar.update(100))
            self.win.addstr(4, 1, ' '*50)
            self.win.addstr(4, 1, 'Done!')
            self.win.noutrefresh()
            curses.doupdate()
            curses.napms(1000)
        except Exception as e:
            raise Exception(f'Installation exception: {e}')

    def draw(self):
        self.win.addstr(0, 0, 'WELCOME TO TINTASK')

    def input(self, ch):
        return None, windows.Waction.POP

class Database:
    dblog = 'dblog.txt'
    dbcon: sqlite3.Connection = None
    dbcursor: sqlite3.Cursor = None
    dbfile = '' 
    DB_NULL = 'N/A'

    @staticmethod
    def delete():
        try:
            dbfile = Database.getdbpath()
            if os.path.exists(dbfile):
                os.remove(dbfile)
                os.rmdir(os.path.dirname(dbfile))
        except Exception as e:
            windows.Logger.log(f'Uninstalling error: {e}')

    @staticmethod
    def sanitycheck():
        if not Database.checktable(DBTables.tasks):
            return False
        if not Database.checktable(DBTables.config):
            return False
        if not Database.checktable(DBTables.tags):
            return False
        return True

    @staticmethod
    def createtable(table, columns):
        try:
            cmd = f"""
            CREATE TABLE {table}({columns})
            """
            windows.Logger.log(f'SQL cmd: {cmd}')
            Database.dbcon.execute(cmd)
        except Exception as e:
            windows.Logger.log(f'SQL error: {e}')

    @staticmethod
    def checktable(table):
        try:
            cmd = f"""
            SELECT name FROM sqlite_master
            WHERE type='table' AND
            name='{table}'
            """
            windows.Logger.log(f'SQL cmd: "{cmd}"')
            res = Database.dbcon.execute(cmd).fetchall()
            if res:
                return True
        except Exception as e:
            windows.Logger.log(f'SQL error: "{e}"')
        return False

    @staticmethod
    def getdbpath():
        home = os.path.expanduser('~')
        if sys.platform == 'win32':
            return os.path.join(home, os.environ['LOCALAPPDATA'], 'TinTask', 'tintask.db')
            #return os.path.join(home, 'TinTask', 'tintask.db')
        else:
            return os.path.join(home, '.local', 'share', 'tintask', 'tintask.db')

    @staticmethod
    def connect():
        try:
            dbfile = Database.getdbpath()
            Database.dbfile = os.path.expanduser(dbfile)
            if not os.path.exists(Database.dbfile):
                windows.Logger.log(f'Making folders for database - {Database.dbfile}')
                os.makedirs(os.path.dirname(Database.dbfile))
            else:
                windows.Logger.log(f'Database exists')
        except Exception as e:
            windows.Logger.log(f'Database creation error: {e}')
            raise Exception(e)
        try:
            windows.Logger.log(f'Connecting to "{Database.dbfile}"')
            Database.dbcon = sqlite3.connect(Database.dbfile)
            Database.dbcursor = Database.dbcon.cursor()
        except Exception as e:
            windows.Logger.log(f'SQL exception: {e}')
            raise Exception(e)
        windows.Logger.log(f'Database "{Database.dbfile}" connected')

    @staticmethod
    def setup():
        Database.connect()

    @staticmethod
    def addrow(table: str, vals: list[str]):
        if not vals:
            return
        vals = [f'"{v}"' for v in vals]
        values = '(' + ','.join(vals) + ')'
        try:
            cmd = f"""
            INSERT INTO {table} VALUES {values}
            """
            windows.Logger.log(f'SQL cmd: "{cmd}"')
            Database.dbcursor.execute(cmd)
            Database.dbcon.commit()
        except Exception as e:
            windows.Logger.log(f'SQL error: {e}')
    
    @staticmethod
    def deleterow(table, values):
        try:
            cmd = f"""
            DELETE FROM {table}
            WHERE
            """
            for column,val in values:
                cmd += f"{column}='{val}'"
                if (column,val) != values[-1]:
                    cmd += ' AND '
            windows.Logger.log(f'SQL cmd: "{cmd}"')
            Database.dbcursor.execute(cmd)
            Database.dbcon.commit()
        except Exception as e:
            windows.Logger.log(f'SQL error: "{cmd}" -> {e}')

    @staticmethod
    def gettasks(start, end):
        try:
            cmd = f"""
            SELECT * FROM {DBTables.tasks}
            WHERE date >= '{start}' AND date <= '{end}'
            ORDER BY date ASC;
            """
            windows.Logger.log(f'SQL cmd: "{cmd}"')
            cmd = ' '.join(cmd.split())
            return Database.dbcursor.execute(cmd).fetchall()
        except Exception as e:
            windows.Logger.log(f'SQL error: "{cmd}" -> {e}')
        return ''

class Manager:
    DB_DATE_FORMAT = '%Y-%m-%d'
    DATE_FORMAT = '%A %B %d, %Y'
    BRIEF_FORMAT = '%m/%d'
    currentday = datetime.datetime.now()
    viewingdate = datetime.datetime.now()

    @staticmethod
    def datetobriefformat(dobj):
        return dobj.strftime(Manager.BRIEF_FORMAT)

    @staticmethod
    def updatedate(date, value, amount='week'):
        if amount == 'week':
            td = datetime.timedelta(days=7)
            date += td * value
        elif amount == 'month':
            td = dateutil.relativedelta.relativedelta(months=1)
            date += td * value
        return date

    @staticmethod
    def start():
        Database.setup()
        if not Database.sanitycheck():
            raise Exception(f'Error: Databases not set up properly')

    @staticmethod
    def datetodbformat(dobj):
        return dobj.strftime(Manager.DB_DATE_FORMAT)

    @staticmethod
    def dbformattodate(date):
        return datetime.datetime.strptime(date,
                Manager.DB_DATE_FORMAT).strftime(Manager.DATE_FORMAT)

    @staticmethod
    def addtasks(date, selection, tasks, tag=''):
        day = Manager.shiftdate(date, selection)
        windows.Logger.log(f'Adding new task -> "{tasks}"')
        for t in tasks:
            if not t:
                continue
            if tag:
                dbtag = tag
            else:
                dbtag = Database.DB_NULL
            data = [Manager.datetodbformat(day), dbtag, t.strip()]
            Database.addrow(DBTables.tasks, data)

    @staticmethod
    def shiftdate(date, selection):
        todayn = date.weekday()
        if todayn - selection > 0:
            return date - datetime.timedelta(days=todayn-selection)
        else:
            return date + datetime.timedelta(days=selection-todayn)

    @staticmethod
    def deletetasks(date, selection, tag=None):
        day = Manager.shiftdate(date, selection)
        windows.Logger.log(f'Deleting tasks on "{day}"')
        day = Manager.datetodbformat(day)
        if tag:
            Database.deleterow(DBTables.tasks, [('date',day), ('tag',tag)])
        else:
            Database.deleterow(DBTables.tasks, [('date',day)])

    @staticmethod
    def gettasks(date, selection):
        day = Manager.shiftdate(date, selection)
        windows.Logger.log(f'Get tasks for day "{day}"')
        day = Manager.datetodbformat(day)
        tasks = Database.gettasks(day, day)
        if not tasks:
            tasks = ''
        return tasks
    
    @staticmethod
    def getreport(date=None, period='week'):
        if not date:
            date = Manager.currentday
        if period == 'week':
            start,end = Manager.getweek(date)
        elif period == 'month':
            start,end = Manager.getmonth(date)
        start = Manager.datetodbformat(start)
        end = Manager.datetodbformat(end)
        tasks = Database.gettasks(start, end)
        tasks = Manager.organizetasks(tasks)
        return tasks

    @staticmethod
    def organizetasks(data):
        tasks = {}
        for date, tag, task in data:
            # check if date has been added
            if date in tasks:
                # if tag has been added
                if tag in tasks[date]:
                    # append the newest task
                    tasks[date][tag].append(task)
                else:
                    # or add a new slot for the tag
                    tasks[date][tag] = [task]
            else:
                # or add a new date slot and dict
                tasks[date] = {tag: [task]}
        return tasks

    @staticmethod
    def getweek(date=None):
        if not date:
            date = Manager.currentday
        start = date - datetime.timedelta(days=date.weekday())
        end = start + datetime.timedelta(days=6)
        windows.Logger.log(f'Get tasks for week of {start} -> {end}')
        return start, end
    
    @staticmethod
    def getmonth(date=None):
        if not date:
            date = Manager.currentday
        start = date.replace(day=1)
        end = calendar.monthrange(date.year, date.month)[1]
        end = datetime.date(date.year, date.month, end)
        windows.Logger.log(f'Get tasks for month of {start} -> {end}')
        return start, end

class SideMenu(windows.Window):
    def __init__(self, row, col, length, width):
        super().__init__(row, col, length, width)
        self.filtering = False
        self.filter = ''

    def wrap(self, tab, task):
        cutat = self.width-tab
        newtask = task[:cutat]
        am = 0
        while True:
            end = cutat + self.width
            if end < len(task):
                #newtask += '\n' + task[cutat:end]
                newtask += task[cutat:end]
                cutat += self.width
                am += 1
            else:
                extra = task[cutat:]
                if extra:
                    #newtask += '\n' + extra
                    newtask += extra
                    am += 1
                break
        return newtask, am
    
    def tab(self, name, selected, pos):
        if selected:
            highlight = curses.A_BOLD
        else:
            highlight = curses.A_NORMAL
        self.win.addstr(pos[0], pos[1], '/ ', highlight)
        self.win.addstr(pos[0], pos[1]+2, name[0], curses.A_BOLD | curses.A_UNDERLINE)
        self.win.addstr(pos[0], pos[1]+3, name[1:]+' \\', highlight)
        return pos[0], pos[1]+2+len(name)+2

    def menu(self):
        if self.mode == 'report':
            er,ec = self.tab('Report', True, (0,0))
            _,_ = self.tab('Calendar', False, (er,ec))
        elif self.mode == 'calendar':
            er,ec = self.tab('Report', False, (0,0))
            _,_ = self.tab('Calendar', True, (er,ec))
        self.win.addstr(1, 0, '-'*(self.width-1))
    
    def report(self):
        start,end = Manager.getweek(Manager.viewingdate)
        start = Manager.datetobriefformat(start)
        end = Manager.datetobriefformat(end)
        weekmark = f'{start} - {end}'
        self.win.addstr(2, self.width-len(weekmark)-5, weekmark, curses.A_REVERSE)
        tasks = Manager.getreport(Manager.viewingdate)
        daterow = 3
        for date, vals in tasks.items():
            date = Manager.dbformattodate(date)
            if daterow < self.length-3:
                self.safeprint((daterow,1), date, curses.A_BOLD | curses.A_UNDERLINE)
            tagrow = 1
            for tag, task in vals.items():
                if tag == Database.DB_NULL:
                    trow = 1
                    for t in task:
                        tab = '  - '
                        text,am = self.wrap(len(tab), t)
                        if daterow < self.length-3:
                            self.safeprint((daterow+trow,0), tab+text)
                        trow += 1 + am
                    daterow += trow
                else:
                    self.safeprint((daterow+tagrow,2), tag, curses.A_REVERSE)
                    trow = 1
                    for t in task:
                        tab = '   - '
                        text,am = self.wrap(len(tab), t)
                        if daterow < self.length-3:
                            self.safeprint((daterow+tagrow+trow,0), tab+text)
                        trow += 1 + am
                    daterow += trow + tagrow

    def calendar(self):
        self.win.addstr(2, 2, 'F', curses.A_UNDERLINE)
        self.win.addstr(2, 3, 'ilter:')
        self.win.addstr(2, 10, self.filter, curses.A_REVERSE)
        if self.filtering:
            edit = windows.Editor(1, 20, (self.row+2,self.col+10))
            filter = edit.gettext()
            if filter:
                self.filter = filter
            self.win.addstr(2, 10, self.filter, curses.A_REVERSE)
            self.filtering = False
        row = 4
        col = 2
        colspace = 2
        rowspace = 1
        maxrow = self.length-2
        currentmonth = Manager.viewingdate
        calendar = windows.mycalendar(currentmonth)
        pts = []
        colpts = math.floor(self.width / (calendar.width+colspace))
        rowpts = math.floor(maxrow / (calendar.length+rowspace))
        for _ in range(rowpts):
            for _ in range(colpts):
                pts.append((row,col))
                col += calendar.width + colspace
            col = 2
            row += calendar.length + rowspace
        for pt in pts:
            calendar = windows.mycalendar(currentmonth)
            lookup = self.gettasksaslookup(currentmonth)
            calendar.print(self.win, pt[0], pt[1], lookup, self.filter)
            td = dateutil.relativedelta.relativedelta(months=1)
            currentmonth = currentmonth + td

    def gettasksaslookup(self, date):
        tasks = Manager.getreport(date, 'month')
        windows.Logger.log(tasks)
        lookup = {}
        for date, data in tasks.items():
            index = str(int(date.split('-')[-1]))
            lookup[index] = {}
            for tag, tasks in data.items():
                lookup[index][tag] = len(tasks)
        windows.Logger.log(lookup)
        return lookup

    def footer(self, increment='week'):
        self.win.addstr(self.length-1, 0, '-'*(self.width-1))
        self.win.addstr(self.length-2, 0, '< ')
        self.win.addstr(self.length-2, 2, 'P', curses.A_BOLD | curses.A_UNDERLINE)
        self.win.addstr(self.length-2, 3, f'revious {increment}')
        msg = f'ext {increment} >'
        self.win.addstr(self.length-2, self.width-1-len(msg)-1, 'N', curses.A_BOLD | curses.A_UNDERLINE)
        self.win.addstr(self.length-2, self.width-1-len(msg), msg)

    def draw(self):
        self.menu()
        if self.mode == 'report':
            self.report()
            self.footer('week')
        elif self.mode == 'calendar':
            self.calendar()
            self.footer('month')

    def input(self, ch):
        if ch == ord('r'):
            self.mode = 'report'
        elif ch == ord('c'):
            self.mode = 'calendar'
        else:
            if self.mode == 'report':
                if ch == ord('p'):
                    Manager.viewingdate = Manager.updatedate(Manager.viewingdate, -1, 'week')
                elif ch == ord('n'):
                    Manager.viewingdate = Manager.updatedate(Manager.viewingdate, 1, 'week')
            elif self.mode == 'calendar':
                if ch == ord('p'):
                    Manager.viewingdate = Manager.updatedate(Manager.viewingdate, -1, 'month')
                elif ch == ord('n'):
                    Manager.viewingdate = Manager.updatedate(Manager.viewingdate, 1, 'month')
                elif ch == ord('f'):
                    self.filtering = True
                    self.filter = ''
        return None,None

class StatusBar:
    mrow = 0
    mcol = 0
    delay = 100
    bar = windows.Bar(10)
    stdscr: curses.window = None

    @staticmethod
    def setup(termrows, termcols, stdscr):
        StatusBar.mrow = termrows
        StatusBar.mcol = termcols
        StatusBar.stdscr = stdscr

    @staticmethod
    def update(progress=0, message=''):
        StatusBar.stdscr.addstr(StatusBar.mrow, 0, ' '*StatusBar.mcol)
        StatusBar.stdscr.addstr(
                StatusBar.mrow,
                StatusBar.mcol-StatusBar.bar.totalsize,
                StatusBar.bar.update(0))
        StatusBar.stdscr.addstr(StatusBar.mrow, StatusBar.mcol-StatusBar.bar.totalsize,
                                    StatusBar.bar.update(progress))
        if message:
            decal = StatusBar.bar.totalsize+len(message)+1
            if StatusBar.mcol-decal >= 0:
                StatusBar.stdscr.addstr(StatusBar.mrow,
                                        StatusBar.mcol-decal,
                                        message)
        StatusBar.stdscr.noutrefresh()
        curses.doupdate()

class AddTask(windows.Window):
    def draw(self):
        tab = 2
        date = Manager.currentday.strftime('%m/%d')
        self.win.addstr(1, tab, f'What did you do today? ({date})')
        am = 0
        tasks = []
        row = 2+am
        col = tab+2
        while True:
            self.win.addstr(row, tab, '> ')
            self.win.noutrefresh()
            edit = windows.Editor(self.length-row, self.width-col, (self.row+row,self.col+col))
            task = edit.gettext()
            if task:
                tasks.append(task)
                am += math.ceil(len(task) / round(self.width-col))
            else:
                if edit.cancelled:
                    tasks = []
                break
            row = 2+am
        if tasks:
            row = 2+am+1
            self.win.addstr(row, tab, 'Add a tag?')
            self.win.addstr(row+1, tab, '>')
            self.win.noutrefresh()
            row += 1
            edit = windows.Editor(self.length-row, self.width-col, (self.row+row,self.col+col))
            tag = edit.gettext()
            if not tag:
                tag = ''
            StatusBar.update(10, 'Adding task to database...')
            curses.napms(100)
            Manager.addtasks(Manager.currentday, 0, tasks, tag)
            StatusBar.update(100)
            curses.napms(100)
        self.done = True

    def input(self, ch):
        return None, windows.Waction.POP

class EditTask(windows.Window):
    def draw(self):
        tab = 2
        self.win.addstr(1, tab, 'What date to edit? (ex. M/T/W/Th/F/S/Su or dM/dT/dW/dTh/dF/dS/dSu to delete)')
        self.win.addstr(3, tab, '> ')
        self.win.noutrefresh()
        row = 3
        col = tab+2
        edit = windows.Editor(self.length-row, self.width-col, (self.row+row,self.col+col))
        choice = edit.gettext()
        if not choice or edit.cancelled:
            self.done = True
            return
        delete = False
        if choice[0] == 'd':
            delete = True
            choice = choice[1:]
        choices = {'m':0, 't':1, 'w':2, 'th':3, 'f':4, 's':5, 'su':6}
        if choice not in choices:
            self.done = True
            return
        selection = choices[choice]
        if delete:
            StatusBar.update(10, 'Deleting tasks from database...')
            curses.napms(100)
            Manager.deletetasks(Manager.viewingdate, selection)
            StatusBar.update(100)
            curses.napms(100)
        else:
            tasks = Manager.gettasks(Manager.viewingdate, selection)
            library = {}
            tagtoedit = Database.DB_NULL
            for task in tasks:
                if task[1] in library:
                    library[task[1]].append(task[2])
                else:
                    library[task[1]] = [task[2]]
            self.win.addstr(row+1, tab, 'Edit which tag?')
            self.win.addstr(row+2, tab, '> ')
            self.win.noutrefresh()
            row += 2
            edit = windows.Editor(self.length-row, self.width-col, (self.row+row,self.col+col))
            tagtoedit = edit.gettext()
            if edit.cancelled:
                self.done = True
                return
            if not tagtoedit:
                tagtoedit = Database.DB_NULL
            if tagtoedit in library:
                text = library[tagtoedit]
            else:
                text = ''
            text = '- ' + '\n- '.join(text)
            if tagtoedit == Database.DB_NULL:
                tagtext = 'no tag'
            else:
                tagtext = tagtoedit
            self.win.addstr(row, tab, f"Editting '{tagtext}'")
            self.win.addstr(row+1, tab, '> ')
            row += 1
            self.win.noutrefresh()
            edit = windows.Editor(self.length-row, self.width-col, (self.row+row,self.col+col),
                                  text, double=True)
            text = edit.gettext()
            if text and not edit.cancelled:
                StatusBar.update(10, 'Updating tasks in database...')
                curses.napms(100)
                Manager.deletetasks(Manager.viewingdate, selection, tagtoedit)
                tasks = text.split('-')
                Manager.addtasks(Manager.viewingdate, selection, tasks, tagtoedit)
                StatusBar.update(100)
                curses.napms(100)
        self.done = True

    def input(self, ch):
        return None, windows.Waction.POP

class TinTask(windows.Window):
    def draw(self):
        #s = "TinTask"
        #er,_ = windows.box(self.win, s, 0, 4, (0,0))
        s = [   '░▀█▀░▀█▀░█▀█░▀█▀░█▀█░█▀▀░█░█',
                '░░█░░░█░░█░█░░█░░█▀█░▀▀█░█▀▄',
                '░░▀░░▀▀▀░▀░▀░░▀░░▀░▀░▀▀▀░▀░▀',
             ]
        for rx,rs in enumerate(s):
            self.win.addstr(rx+1, 1, rs)
        er = 4
        coltab = 2
        er,_ = windows.option(self.win, 'A', 'Add a task', (er+1,coltab))
        er,_ = windows.option(self.win, 'E', 'Edit a date', (er,coltab))
        er,_ = windows.option(self.win, 'S', 'Send your task list', (er,coltab))
        er,_ = windows.option(self.win, 'X', 'Configurations', (er,coltab))
        er,_ = windows.option(self.win, 'Q', 'Quit', (er,coltab))
        self.erow = er
        StatusBar.update(0)

    def input(self, ch):
        if ch == ord('q'):
            raise SystemExit
        elif ch == ord('a'):
            return AddTask(self.erow,
                           0,
                           self.length-self.erow,
                           self.width), windows.Waction.PUSH
        elif ch == ord('e'):
            return EditTask(self.erow,
                            0,
                            self.length-self.erow,
                            self.width), windows.Waction.PUSH
        return None, None

