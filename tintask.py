import calendar
import curses.ascii
import curses.textpad
import math
import curses
import windows
import os
import sqlite3
import datetime
import dateutil.relativedelta
import sys

if sys.platform == 'win32':
    import win32com.client as win32

reportprefdefault = """
__MAILTO__first.last@company.com
__SUBJECT__Weekly Status Report (__SWEEK__-__EWEEK__)
Weekly Status Report

Accomplishments:
__TASKS__ __SFILTER__ notag:meeting __EFILTER__
Key Dates:
__TASKS__ __SFILTER__ tag:meeting,tags:0 __EFILTER__
Have a good weekend!
Name
"""

class ReportKeys():
    MAILTO = '__MAILTO__'
    SUBJECT = '__SUBJECT__'
    SWEEK = '__SWEEK__'
    EWEEK = '__EWEEK__'
    TASKS = '__TASKS__'
    SFILTER = '__SFILTER__'
    EFILTER = '__EFILTER__'

class ReportData:
    def __init__(self, tasks, start, end, prefile):
        self.tasks = tasks
        self.start = start
        self.end = end
        self.prefile = prefile
        self.mailto = '' 
        self.subject = '' 
        self.body = []
        self.loadreport()

    def loadreport(self):
        usefilter = ''
        tagfilter = ''
        tagtext = ''
        showtags = True
        for line in self.prefile:
            line = line.strip()
            if ReportKeys.MAILTO in line:
                line = line.replace(ReportKeys.MAILTO, '')
                self.mailto = line 
                continue
            if ReportKeys.SUBJECT in line:
                line = line.replace(ReportKeys.SUBJECT, '')
                if ReportKeys.SWEEK in line:
                    line = line.replace(ReportKeys.SWEEK, self.start)
                if ReportKeys.EWEEK in line:
                    line = line.replace(ReportKeys.EWEEK, self.end)
                self.subject = line
                continue
            if ReportKeys.SWEEK in line:
                line = line.replace(ReportKeys.SWEEK, self.start)
            if ReportKeys.EWEEK in line:
                line = line.replace(ReportKeys.EWEEK, self.end)
            if ReportKeys.TASKS in line:
                if ReportKeys.SFILTER in line and ReportKeys.EFILTER in line:
                    sx = line.find(ReportKeys.SFILTER) + len(ReportKeys.SFILTER)
                    ex = line.find(ReportKeys.EFILTER)
                    usefilter = line[sx:ex].strip()
                    for mfilter in usefilter.split(','):
                        prop,text = mfilter.split(':')
                        if prop == 'tag':
                            tagfilter = str(prop)
                            tagtext = str(text)
                        elif prop == 'notag':
                            tagfilter = str(prop)
                            tagtext = str(text)
                        elif prop == 'tags':
                            showtags = bool(int(text))
                    line = line.replace(ReportKeys.SFILTER, '')
                    line = line.replace(ReportKeys.EFILTER, '')
                    line = line.replace(usefilter, '')
                windows.Logger.log(f'tagfilter: {tagfilter} {showtags}')
                line = line.replace(ReportKeys.TASKS, '')
                for tag,tasks in self.tasks.items():
                    if tagfilter == 'tag':
                        if tag != tagtext:
                            continue
                    elif tagfilter == 'notag':
                        if tag == tagtext:
                            continue
                    if showtags:
                        if tag != Database.NULL_TAG:
                            self.body.append(f'  {tag}')
                    for task in tasks:
                        self.body.append(f'  - {task}')

            self.body.append(line)

class Options(windows.Window):
    def __init__(self, row, col, length, width):
        super().__init__(row, col, length, width)

    def header(self):
        self.win.addstr(1, 2, f'Options')
        windows.separator(self.win, self.width, (2,1))

    def footer(self):
        msg = f'<esc> to close'
        self.win.addstr(self.length-2, self.width-len(msg)-3, msg)

    def displaywindow(self):
        self.win.erase()
        curses.textpad.rectangle(self.win, 0, 0, self.length-2, self.width-2)
        self.header()
        self.footer()

    def draw(self):
        self.displaywindow()
        _,_ = windows.option(self.win, 'G', 'Generate report preference file', (3,1))

    def input(self, ch):
        if ch == curses.ascii.ESC:
            return None,windows.Waction.POP
        elif ch == ord('g'):
            StatusBar.update(10, 'Generating report preference file...')
            curses.napms(100)
            Manager.checkreportpref()
            Manager.readreportpref()
            StatusBar.update(100)
            curses.napms(100)
        return None,None

class Mail(windows.Window):
    def __init__(self, row, col, length, width):
        super().__init__(row, col, length, width)
        self.dosend = False
        self.status = ['Ready to send', 'Sending', 'Sent!', 'Failed to send!']
        self.statusix = 0

    def displaystatus(self, row):
        maxlen = max([len(smsgs) for smsgs in self.status])
        msg = f'Status: '
        self.win.addstr(row, self.width-2-maxlen, ' '*maxlen)
        self.win.addstr(row, self.width-2-len(msg)-maxlen, msg)
        self.win.addstr(row, self.width-2-maxlen, self.status[self.statusix])

    def footer(self):
        msg = f'<esc> to close'
        self.win.addstr(self.length-2, self.width-len(msg)-3, msg)

    def displaywindow(self, reportdata: ReportData | None = None):
        self.win.addstr(1, 1, 'Outlook Email Report')
        self.footer()
        windows.separator(self.win, self.width, (2,1))
        if not self.dosend:
            attrib1 = curses.A_BOLD | curses.A_UNDERLINE
            attrib2 = curses.A_NORMAL
        else:
            attrib1 = curses.A_REVERSE
            attrib2 = curses.A_REVERSE
        row = 3
        col = 1
        if reportdata != None:
            text = f'Send to: {reportdata.mailto}'
            spliced,am = Manager.splice(text, self.width-2-col)
            for ix,txt in enumerate(spliced):
                self.win.addstr(row+ix, col, txt)
            row += am
            text = f'Subject: {reportdata.subject}'
            spliced,am = Manager.splice(text, self.width-2-col)
            for ix,txt in enumerate(spliced):
                self.win.addstr(row+ix, col, txt)
            row += am + 1
            self.displaystatus(row)
            self.win.addstr(row, col, 'Actions:', curses.A_UNDERLINE)
            row += 1
            self.win.addstr(row, col+1, 'M', attrib1)
            self.win.addstr(row, col+2, 'ail now', attrib2)
            self.win.noutrefresh()

    def draw(self):
        curses.textpad.rectangle(self.win, 0, 0, self.length-2, self.width-2)
        if sys.platform != 'win32':
            text = 'Currently unavailable for non Windows Operating Systems'
            spliced,_ = Manager.splice(text, self.width-3)
            for ix,txt in enumerate(spliced):
                self.win.addstr(1+ix, 1, txt)
            self.footer()
        else:
            self.displaywindow()
            try:
                reportdata = Manager.loadreportdata()
            except Exception as e:
                windows.Logger.log(f'Error loading report data: {e}')
                self.win.addstr(3, 1, f'Failed to create the email, please check the logs')
                return
            self.displaywindow(reportdata)
            if self.dosend:
                StatusBar.update(10, 'Sending Email ...')
                try:
                    curses.napms(200)
                    Manager.sendemail(reportdata)
                    self.done = True
                except Exception as e:
                    self.statusix = 3
                    windows.Logger.log(f'Error sending the email -> {e}')
                    self.dosend = False
                    StatusBar.update(0)
                    self.displaywindow(reportdata)
                    return
                StatusBar.update(100)
                curses.napms(100)
                self.statusix = 2
                self.displaywindow(reportdata)
                curses.doupdate()
                curses.napms(200)

    def input(self, ch):
        if ch == curses.ascii.ESC:
            return None,windows.Waction.POP
        elif ch == ord('m'):
            self.dosend = True
            self.statusix = 1
        return None,None

class DBTables:
    #tasks = 'tasks'
    #tasks_columns = 'date DATE, tag TEXT, task TEXT'
    tasks = 'tasks'
    tasks_columns = 'id INTEGER PRIMARY KEY AUTOINCREMENT, date DATE, task TEXT'
    tags = 'tags'
    tags_columns = 'id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT'
    junction = 'junction'
    junction_columns = 'task_id INTEGER, tag_id INTEGER, PRIMARY KEY (task_id,tag_id) FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE, FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE'

class DBIndexes:
    tagindex = f'tagindex ON {DBTables.tasks}(date)'

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
        Database.createtable(DBTables.tasks, DBTables.tasks_columns)
        Database.createtable(DBTables.tags, DBTables.tags_columns)
        Database.createtable(DBTables.junction, DBTables.junction_columns)
    
    def step(self, func, msg, amount):
        self.win.clear()
        self.win.addstr(0, 0, 'TINTASK IS INSTALLING...')
        self.win.addstr(4, 1, msg)
        if func:
            func()
        else:
            windows.Logger.log(f'Install step: {msg} func:{func} is null')
        self.win.addstr(5, 1, self.bar.update(amount))
        self.win.noutrefresh()
        curses.doupdate()
        curses.napms(1000)
    
    def setup(self):
        self.step(None, '', 0)
        try:
            self.step(Database.connect, 'Creating storage space...', 20)
            self.step(self.setuptables, 'Making tables...', 40)
            self.step(Manager.checkreportpref(), 'Setting up preferences', 80)
            self.step(Manager.start(), 'Final check...', 80)
            self.step(None, 'Done', 100)
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
    NULL_TAG = 'N/A'

    @staticmethod
    def verify():
        if os.path.exists(Database.getdbpath()):
            return True
        return False

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
    def createtable(table, columns):
        try:
            cmd = f"""
            CREATE TABLE IF NOT EXISTS {table} ({columns})
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
            if not os.path.exists(os.path.dirname(Database.dbfile)):
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
    def addrow(table: str, vals: list[str], cols: list[str]=[], ignore=False):
        if not vals:
            return
        if not cols:
            columns = ''
        else:
            cols = [f'"{c}"' for c in cols]
            columns = '(' + ','.join(cols) + ')'
        vals = [f'"{v}"' for v in vals]
        values = '(' + ','.join(vals) + ')'
        if ignore:
            ignorestm = 'OR IGNORE'
        else:
            ignorestm = ''
        try:
            cmd = f"""
            INSERT {ignorestm} INTO {table} {columns} VALUES {values}
            """
            windows.Logger.log(f'SQL cmd: "{cmd}"')
            Database.dbcursor.execute(cmd)
            Database.dbcon.commit()
            return Database.dbcursor.lastrowid
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
            windows.Logger.log(f'SQL error: {e}')

    @staticmethod
    def gettasks(start, end):
        try:
            cmd = f"""
            SELECT * FROM {DBTables.tasks}
            WHERE date >= '{start}' AND date <= '{end}'
            ORDER BY date ASC;
            """
            windows.Logger.log(f'SQL cmd: "{cmd}"')
            #cmd = ' '.join(cmd.split())
            return Database.dbcursor.execute(cmd).fetchall()
        except Exception as e:
            windows.Logger.log(f'SQL error: {e}')
        return ''

    @staticmethod
    def gettags(taskid):
        try:
            cmd = f"""
            SELECT {DBTables.tags}.tag
            FROM {DBTables.tags}
            JOIN {DBTables.junction}
            ON {DBTables.tags}.id = {DBTables.junction}.tag_id
            WHERE {DBTables.junction}.task_id = {taskid}
            """
            windows.Logger.log(f'SQL cmd: "{cmd}"')
            return Database.dbcursor.execute(cmd).fetchall()
        except Exception as e:
            windows.Logger.log(f'SQL error: {e}')
        return ''

    @staticmethod
    def search(column, substring):
        try:
            cmd = f"""
            SELECT * FROM {column}
            WHERE task LIKE '{substring}';
            """
            windows.Logger.log(f'SQL cmd: "{cmd}"')
            return Database.dbcursor.execute(cmd).fetchall()
        except Exception as e:
            windows.Logger.log(f'SQL error: {e}')
        return ''

class Manager:
    DB_DATE_FORMAT = '%Y-%m-%d'
    DATE_FORMAT = '%A %B %d, %Y'
    BRIEF_FORMAT = '%m/%d'
    currentday = datetime.datetime.now()
    viewingdate = datetime.datetime.now()
    reportpref = ''
    reportpreffile = 'report.pref'

    @staticmethod
    def splice(text, width):
        spliced = [text[i:i+width] for i in range(0, len(text), width)]
        am = Manager.wrap(text, width)
        return spliced, am

    @staticmethod
    def wrap(text, width):
        am = math.ceil(len(text) / width)
        if am == 0:
            return 1
        return am

    @staticmethod
    def loadreportdata():
        mytasks = Manager.getreport(Manager.viewingdate, groupby='tag')
        windows.Logger.log(f'report tasks {mytasks}')
        start,end = Manager.getweek(Manager.viewingdate)
        start = Manager.datetobriefformat(start)
        end = Manager.datetobriefformat(end)
        return ReportData(mytasks, start, end, Manager.reportpref)

    @staticmethod
    def sendemail(reportdata):
        if sys.platform != 'win32':
            return
        try:
            outlook = win32.Dispatch('outlook.application')
            mail = outlook.CreateItem(0)
            mail.To = reportdata.mailto
            mail.Subject = reportdata.subject
            body = '\n'.join(reportdata.body)
            mail.Body = body
            mail.Send()
            # mail.HTMLBody = self.createReport(HTML=True)
        except Exception as e:
            windows.Logger.log(f"""
            Email:
                Mailto:{reportdata.mailto}
                Subject:{reportdata.subject}
                Body:{body}
            """)
            windows.Logger.log(f'Error: failed to create email -> {e}')
            raise Exception(e)

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
    def checkreportpref():
        if not os.path.exists(Manager.reportpreffile):
            with open(Manager.reportpreffile, 'w+') as file:
                file.write(reportprefdefault)

    @staticmethod
    def readreportpref():
        try:
            if os.path.exists(Manager.reportpreffile):
                with open(Manager.reportpreffile, 'r') as rp:
                    Manager.reportpref = rp.readlines()
                windows.Logger.log(f'Loaded preferences file ->\n{Manager.reportpref}')
            else:
                windows.Logger.log(f'Preference file "{Manager.reportpreffile}" does not exist')
        except Exception as e:
            windows.Logger.log(f'Error: Failed to load preferences file! -> {e}')

    @staticmethod
    def start():
        if not Database.verify():
            raise Exception(f'Databases not set up')
        Database.setup()
        Manager.readreportpref()

    @staticmethod
    def datetodbformat(dobj):
        return dobj.strftime(Manager.DB_DATE_FORMAT)

    @staticmethod
    def dbformattodate(date):
        return datetime.datetime.strptime(date,
                Manager.DB_DATE_FORMAT).strftime(Manager.DATE_FORMAT)

    @staticmethod
    def addtasks(date, tasks, tag='', selection=None):
        windows.Logger.log(f'Add tasks date: {date} select:{selection}')
        if selection != None:
            day = Manager.shiftdate(date, selection)
        else:
            day = date
        windows.Logger.log(f'Add tasks day: {day}')
        windows.Logger.log(f'Adding new task -> "{tasks}"')
        for t in tasks:
            if not t:
                continue
            if tag:
                dbtag = tag
            else:
                dbtag = Database.NULL_TAG
            cols = ['date', 'task']
            row = [Manager.datetodbformat(day), t.strip()]
            taskid = Database.addrow(DBTables.tasks, row, cols)
            windows.Logger.log(f'task id: {taskid}')
            cols = ['tag']
            row = [dbtag]
            tagid = Database.addrow(DBTables.tags, row, cols, ignore=True)
            windows.Logger.log(f'task id: {tagid}')
            if taskid != None and tagid != None:
                row = [str(taskid), str(tagid)]
                _ = Database.addrow(DBTables.junction, row)

    @staticmethod
    def shiftdate(date, selection):
        windows.Logger.log(f'Shifting date: {date} by {selection}')
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
    def getreport(date=None, period='week', groupby=''):
        windows.Logger.log(f'Get report for date:{date} period:{period} groupby:{groupby}')
        if not date:
            date = Manager.currentday
        if period == 'week':
            start,end = Manager.getweek(date)
        elif period == 'month':
            start,end = Manager.getmonth(date)
        start = Manager.datetodbformat(start)
        end = Manager.datetodbformat(end)
        tasks = Database.gettasks(start, end)
        tags = {}
        for task in tasks:
            taskid = task[0]
            rows = Database.gettags(task[0])
            if not rows:
                continue
            tags[taskid] = rows
        windows.Logger.log(f'New result format tasks: {tasks}')
        windows.Logger.log(f'New result format tags: {tags}')
        if groupby == 'tag':
            tasks = Manager.organizetasksbytag(tasks, tags)
        else:
            tasks = Manager.organizetasksbydate(tasks, tags)
        return tasks

    @staticmethod
    def organizetasksbytag(tasks, tags):
        data = {}
        '''
        for taskid,date,task in tasks:
            if tag in tasks:
                tasks[tag].append(task)
            else:
                tasks[tag] = [task]
        tasks = {tag: tasks for tag,tasks in sorted(tasks.items())}
        '''
        return data 

    @staticmethod
    def organizetasksbydate(tasks, tags):
        tasks = {}
        '''
        for _,date,task in data:
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
        '''
        return tasks

    @staticmethod
    def getweek(date=None):
        if not date:
            date = Manager.currentday
        start = date - datetime.timedelta(days=date.weekday())
        end = start + datetime.timedelta(days=6)
        return start, end
    
    @staticmethod
    def getmonth(date=None):
        if not date:
            date = Manager.currentday
        start = date.replace(day=1)
        end = calendar.monthrange(date.year, date.month)[1]
        end = datetime.date(date.year, date.month, end)
        return start, end

    @staticmethod
    def searchtasks(substring):
        return Database.search(DBTables.tasks, substring)

class SideMenu(windows.Window):
    def __init__(self, row, col, length, width):
        super().__init__(row, col, length, width)
        self.filtering = False
        self.filter = ''
        self.searching = False
        self.searchterm = ''
        self.searchresults = []

    def displayday(self, row, col, maxrow, maxcol, date, data):
        windows.Logger.log(f'Display day {date}')
        date = Manager.dbformattodate(date)
        if row < maxrow:
            self.win.addstr(row, col, date, curses.A_BOLD | curses.A_UNDERLINE)
            row += 1
        for tag,tasks in data.items():
            tab = ''
            if tag != Database.NULL_TAG:
                if row < maxrow:
                    self.win.addstr(row, col+2, tag, curses.A_REVERSE)
                    row += 1
                    tab = '  '
            for task in tasks:
                text = f' {tab}- {task}'
                am = Manager.wrap(text, maxcol)
                if row < maxrow:
                    self.win.addstr(row, col, text)
                row += am
        return row,col

    def menu(self):
        tasks = False
        calendar = False
        report = False
        search = False
        if self.mode == 'tasks':
            tasks = True
        elif self.mode == 'calendar':
            calendar = True
        elif self.mode == 'report':
            report = True
        elif self.mode == 'search':
            search = True
        er,ec = windows.tab(self.win, 'Tasks', tasks, (0,0))
        er,ec = windows.tab(self.win, 'Calendar', calendar, (er,ec))
        er,ec = windows.tab(self.win, 'Report', report, (er,ec))
        _,_ = windows.tab(self.win, 'Search', search, (er,ec))
        for ix in range(self.width-1):
            self.win.addch(1, ix, curses.ACS_HLINE, curses.A_BOLD)

    def search(self):
        self.win.addstr(2, 2, 'S', curses.A_UNDERLINE)
        self.win.addstr(2, 3, 'earch:')
        self.win.addstr(2, 10, self.searchterm, curses.A_REVERSE)
        if self.searching:
            edit = windows.Editor((self.row+2,self.col+10), 1, 20)
            searchterm = edit.gettext()
            if searchterm:
                self.searchterm = searchterm
            else:
                self.searchresults = []
            self.win.addstr(2, 10, self.searchterm, curses.A_REVERSE)
            self.searching = False
            self.searchresults = Manager.searchtasks(self.searchterm)
        restxt = 'Results:'
        self.win.addstr(4, 2, restxt)
        if not self.searchresults:
            self.win.addstr(4, 2+len(restxt)+1, 'none')
        else:
            row = 5
            for rx,task in enumerate(self.searchresults):
                text = f'  {rx+1}: {task}'
                am = Manager.wrap(text, self.width)
                self.win.addstr(row, 0, text)
                self.win.addstr(row, 2, f'{rx+1}:', curses.A_REVERSE)
                row += am
        windows.Logger.log(f'Found tasks -> {self.searchresults}')
    
    def tasks(self):
        start,end = Manager.getweek(Manager.viewingdate)
        start = Manager.datetobriefformat(start)
        end = Manager.datetobriefformat(end)
        weekmark = f'{start} - {end}'
        self.win.addstr(2, self.width-len(weekmark)-5, weekmark, curses.A_REVERSE)
        tasks = Manager.getreport(Manager.viewingdate, groupby='date')
        windows.Logger.log(f'Get report tasks: {tasks}')
        er = 3
        for date, vals in tasks.items():
            er,_ = self.displayday(er, 0, self.length-3, self.width, date, vals)

    def calendar(self):
        self.win.addstr(2, 2, 'F', curses.A_UNDERLINE)
        self.win.addstr(2, 3, 'ilter:')
        self.win.addstr(2, 10, self.filter, curses.A_REVERSE)
        if self.filtering:
            edit = windows.Editor((self.row+2,self.col+10), 1, 20)
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
        tasks = Manager.getreport(date, 'month', groupby='date')
        windows.Logger.log(tasks)
        lookup = {}
        for date, data in tasks.items():
            index = str(int(date.split('-')[-1]))
            lookup[index] = {}
            for tag, tasks in data.items():
                lookup[index][tag] = len(tasks)
        windows.Logger.log(lookup)
        return lookup

    def report(self):
        try:
            reportdata = Manager.loadreportdata()
            row = 2
            col = 1
            if reportdata.mailto:
                text = f'To: {reportdata.mailto}'
                am = Manager.wrap(text, self.width)
                self.win.addstr(row, col, text)
                row += am
            if reportdata.subject:
                text = f'Subject: {reportdata.subject}'
                am = Manager.wrap(text, self.width)
                self.win.addstr(row, col, text)
                row += am
            row += 1
            windows.Logger.log(reportdata.body)
            for line in reportdata.body:
                am = Manager.wrap(line, self.width)
                self.win.addstr(row, col, line)
                row += am
        except Exception as e:
            self.win.addstr(row, col, f'Unable to load {Manager.reportpreffile} file, check log for failures')
            windows.Logger.log(f'Error ({Manager.reportpreffile}): {e}')

    def footer(self, increment=''):
        for ix in range(self.width-1):
            self.win.addch(self.length-1, ix, curses.ACS_HLINE, curses.A_BOLD)
        if increment:
            self.win.addstr(self.length-2, 0, '<', curses.A_BOLD | curses.A_UNDERLINE)
            self.win.addstr(self.length-2, 1, f' Previous {increment}',)
            msg = f'Next {increment} '
            self.win.addstr(self.length-2, self.width-2-len(msg), msg)
            self.win.addstr(self.length-2, self.width-2, '>', curses.A_BOLD | curses.A_UNDERLINE)

    def draw(self):
        self.menu()
        if self.mode == 'tasks':
            self.tasks()
            self.footer('week')
        elif self.mode == 'calendar':
            self.calendar()
            self.footer('month')
        elif self.mode == 'report':
            self.report()
            self.footer('week')
        elif self.mode == 'search':
            self.search()
            self.footer()

    def input(self, ch):
        if self.mode == 'tasks' or self.mode == 'report':
            if ch == ord('<'):
                Manager.viewingdate = Manager.updatedate(Manager.viewingdate, -1, 'week')
            elif ch == ord('>'):
                Manager.viewingdate = Manager.updatedate(Manager.viewingdate, 1, 'week')
        elif self.mode == 'calendar':
            if ch == ord('<'):
                Manager.viewingdate = Manager.updatedate(Manager.viewingdate, -1, 'month')
            elif ch == ord('>'):
                Manager.viewingdate = Manager.updatedate(Manager.viewingdate, 1, 'month')
            elif ch == ord('f'):
                self.filtering = True
                self.filter = ''
        elif self.mode == 'search':
            if ch == ord('s'):
                self.searching = True
                self.searchterm = ''
        if ch == ord('t'):
            self.mode = 'tasks'
        elif ch == ord('c'):
            self.mode = 'calendar'
        elif ch == ord('r'):
            self.mode = 'report'
        elif ch == ord('s'):
            self.mode = 'search'
        return None,None

class StatusBar:
    delay = 100
    bar = windows.Bar(10)
    win: curses.window = None

    @classmethod
    def setup(cls, length, width, pos):
        StatusBar.length = length 
        StatusBar.width = width 
        try:
            StatusBar.win = curses.newwin(length, width, pos[0], pos[1])
        except Exception as e:
            StatusBar.win = None
            windows.Logger.log(f'ERROR: StatusBar failed to create window! -> {e}')
            raise Exception(e)
        windows.Logger.log(f'{cls.__name__}:')
        windows.Logger.log(f'\tRows: {length} Cols: {width}')
        windows.Logger.log(f'\tStartR: {pos[0]} StartC: {pos[1]}')

    @staticmethod
    def update(progress=0, message=''):
        StatusBar.win.addstr(0, 0, ' '*(StatusBar.width-1))
        StatusBar.win.addstr(0,
                             StatusBar.width-StatusBar.bar.totalsize-1,
                             StatusBar.bar.update(0))
        StatusBar.win.addstr(0,
                             StatusBar.width-StatusBar.bar.totalsize-1,
                             StatusBar.bar.update(progress))
        if message:
            decal = StatusBar.bar.totalsize+len(message)+1
            if StatusBar.width-decal >= 0:
                StatusBar.win.addstr(0, StatusBar.width-decal-1, message)
        StatusBar.win.noutrefresh()
        curses.doupdate()

class MenuState:
    EDITTAG = 'Edit Tag'
    EDITTASK = 'Typing'
    DONE = 'Done? <tab>'
    SELECTDATE = 'Select Date'
    SELECTTAG = 'Select Tag'

class AddMenu(windows.Window):
    def __init__(self, row, col, length, width):
        super().__init__(row, col, length, width)
        self.status = MenuState.DONE
        self.tag = ''
        self.tasks = []
        self.rawtasks = ''
        self.taglb = 'Tag: '
        self.tasklb = 'Tasks: '

    def displaywindow(self):
        self.win.erase()
        curses.textpad.rectangle(self.win, 0, 0, self.length-2, self.width-2)
        self.header()
        self.footer()
        row = 3
        col = 1
        self.win.addstr(row, col, self.taglb[0], curses.A_UNDERLINE)
        self.win.addstr(row, col+1, self.taglb[1:])
        if self.tag:
            self.win.addstr(row, col+len(self.taglb), self.tag, curses.A_REVERSE)
        row += 1
        self.win.addstr(row, col, f'Tasks: ')
        if self.tasks:
            for task in self.tasks:
                splice,am = Manager.splice(task, self.width-2-col)
                for jx,txt in enumerate(splice):
                    self.win.addstr(row+jx, col, txt)
                row += am
        self.win.noutrefresh()

    def draw(self):
        self.displaywindow()
        if self.status == MenuState.EDITTAG:
            self.status = MenuState.DONE
            edit = windows.Editor((self.row+3,self.col+1+len(self.taglb)), 1, self.width-2-len(self.taglb)-self.col-1)
            text = edit.gettext()
            if not edit.cancelled:
                self.tag = text
            else:
                self.tag = ''
            self.displaywindow()
        elif self.status == MenuState.EDITTASK:
            self.status = MenuState.DONE
            if self.rawtasks:
                msg = self.rawtasks
            else:
                msg = '- '
            edit = windows.Editor((self.row+5,self.col+1), self.length-7, self.width-3, msg, double=True)
            text = edit.gettext()
            if not edit.cancelled and text:
                self.tasks = [t.strip() for t in text.split('-')[1:]]
                self.rawtasks = ''
                for t in self.tasks: self.rawtasks += f'- {t}\n'
            self.displaywindow()

    def header(self):
        date = Manager.currentday.strftime('%m/%d')
        self.win.addstr(1, 2, f'Add Tasks')
        self.win.addstr(1, self.width-len(str(date))-3, str(date), curses.A_REVERSE)
        self.displaystatus()
        windows.separator(self.win, self.width, (2,1))

    def footer(self):
        msg = f'<esc> to close'
        self.win.addstr(self.length-2, self.width-len(msg)-3, msg)

    def displaystatus(self):
        self.win.addstr(1, int(self.width/2)-int(len(self.status)/2)-1, self.status)

    def sendtasks(self):
        if self.tasks:
            windows.Logger.log(f'Sending tasks: {self.tag} {self.tasks}')
            if not self.tag:
                self.tag = Database.NULL_TAG
            StatusBar.update(10, 'Adding task to database...')
            curses.napms(100)
            Manager.addtasks(Manager.currentday, self.tasks, self.tag)
            StatusBar.update(100)
            curses.napms(100)

    def input(self, ch):
        if ch == curses.ascii.ESC:
            return None,windows.Waction.POP
        elif self.status == MenuState.DONE:
            if ch == curses.ascii.NL:
                self.status = MenuState.EDITTASK
            elif ch == curses.ascii.TAB:
                self.sendtasks()
                return None,windows.Waction.POP
            elif ch == ord('t'):
                self.status = MenuState.EDITTAG
        return None,None

class EditMenu(windows.Window):
    def __init__(self, row, col, length, width):
        super().__init__(row, col, length, width)
        self.status = MenuState.SELECTDATE
        self.dateselector = 0
        self.dateselection = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri', 'Sat', 'Sun']
        self.tagselector = 0
        self.tagselection = []
        self.library = {}
        self.date = None
        self.newtag = ''
        self.prevtag = ''
        self.tasks = []
        self.rawtasks = ''
        self.taglb = 'Tag: '
        self.tasklb = 'Tasks: '

    def draw(self):
        self.displaywindow()
        row = 8
        col = 1
        if self.status == MenuState.EDITTASK:
            self.status = MenuState.DONE
            if self.rawtasks:
                msg = self.rawtasks
            else:
                msg = '- '
            edit = windows.Editor((self.row+row,self.col+col), self.length-row-2, self.width-3, msg, double=True)
            text = edit.gettext()
            if not edit.cancelled:
                if text:
                    self.tasks = [t.strip() for t in text.split('-')[1:]]
                    self.rawtasks = ''
                    for t in self.tasks: self.rawtasks += f'- {t}\n'
                else:
                    self.tasks = []
                    self.rawtasks = ''
            self.displaywindow()
        elif self.status == MenuState.EDITTAG:
            self.status = MenuState.DONE
            edit = windows.Editor((self.row+6,self.col+1+len(self.taglb)), 1, self.width-2-len(self.taglb)-self.col-1)
            text = edit.gettext()
            if not edit.cancelled:
                self.newtag = text
            else:
                self.newtag = ''
            self.displaywindow()

    def displayselection(self, row, col, selection, selector, highlight):
        if not selection:
            return
        if highlight:
            self.win.addstr(row, col, '<')
        col += 2
        self.win.addstr(row, col, '[ ')
        col += 2
        for ix,sel in enumerate(selection):
            if selector == ix:
                attributes = curses.A_REVERSE
            else:
                attributes = curses.A_NORMAL
            self.win.addstr(row, col, sel, attributes)
            col += len(sel) + 1
        self.win.addstr(row, col, ']')
        col += 2
        if highlight:
            self.win.addstr(row, col, '>') 

    def displaywindow(self):
        self.win.erase()
        curses.textpad.rectangle(self.win, 0, 0, self.length-2, self.width-2)
        self.header()
        self.footer()
        highlight = True if self.status == MenuState.SELECTDATE else False
        self.displayselection(3, 1, self.dateselection, self.dateselector, highlight)
        highlight = True if self.status == MenuState.SELECTTAG else False
        self.displayselection(4, 1, self.tagselection, self.tagselector, highlight)
        self.win.addstr(1, int(self.width/2)-int(len(self.status)/2)-1, self.status)
        row = 6
        col = 1
        self.win.addstr(row, col, self.taglb[0], curses.A_UNDERLINE)
        self.win.addstr(row, col+1, self.taglb[1:])
        if self.newtag:
            self.win.addstr(row, col+len(self.taglb), self.newtag, curses.A_REVERSE)
        row += 1
        self.win.addstr(row, col, f'Tasks: ')
        row += 1
        if self.tasks:
            for task in self.tasks:
                text = f'- {task}'
                splice,am = Manager.splice(text, self.width-3)
                for jx,txt in enumerate(splice):
                    self.win.addstr(row+jx, 1, txt)
                row += am

        self.win.noutrefresh()

    def footer(self):
        msg = f'<esc> to close'
        self.win.addstr(self.length-2, self.width-len(msg)-3, msg)
    
    def header(self):
        self.win.addstr(1, 2, f'Edit Tasks')
        if self.date:
            self.win.addstr(1, self.width-len(str(self.date))-3, str(self.date), curses.A_REVERSE)
        windows.separator(self.win, self.width, (2,1))

    def loadlibrary(self):
        tasks = Manager.gettasks(Manager.viewingdate, self.dateselector)
        self.date = Manager.shiftdate(Manager.viewingdate, self.dateselector).strftime('%m/%d')
        self.library = {}
        for task in tasks:
            if task[1] in self.library:
                self.library[task[1]].append(task[2])
            else:
                self.library[task[1]] = [task[2]]
        windows.Logger.log(f'Edit task: library -> {self.library} -> {tasks}')
        if self.library.keys():
            self.tagselection = list(self.library.keys())
            self.tagselector = 0
        else:
            self.status = MenuState.DONE
            self.tagselection = []
            self.tagselector = 0
        self.tagselection.append('+')

    def loadtasks(self):
        if self.tagselection:
            tag = self.tagselection[self.tagselector]
            if tag == '+':
                self.prevtag = tag
                self.newtag = Database.NULL_TAG
            else:
                self.prevtag = self.tagselection[self.tagselector]
                self.newtag = self.tagselection[self.tagselector]
                if self.prevtag in self.library:
                    self.tasks = self.library[self.prevtag]
                    self.rawtasks = '- '+'\n- '.join(self.tasks)

    def sendtasks(self):
        if not self.newtag:
            self.newtag = Database.NULL_TAG
        StatusBar.update(10, 'Updating tasks in database...')
        curses.napms(100)
        Manager.deletetasks(Manager.viewingdate, self.dateselector, self.prevtag)
        Manager.addtasks(Manager.viewingdate, self.tasks, self.newtag, self.dateselector)
        StatusBar.update(100)
        curses.napms(100)

    def input(self, ch):
        if ch == curses.ascii.ESC:
            return None, windows.Waction.POP
        elif self.status == MenuState.SELECTDATE:
            if ch == ord('>'):
                self.dateselector += 1
                if self.dateselector >= len(self.dateselection):
                    self.dateselector = 0
            elif ch == ord('<'):
                self.dateselector -= 1
                if self.dateselector < 0:
                    self.dateselector = len(self.dateselection)-1
            elif ch == curses.ascii.NL:
                self.status = MenuState.SELECTTAG
                self.loadlibrary()
        elif self.status == MenuState.SELECTTAG:
            if ch == ord('>'):
                self.tagselector += 1
                if self.tagselector >= len(self.tagselection):
                    self.tagselector = 0
            elif ch == ord('<'):
                self.tagselector -= 1
                if self.tagselector < 0:
                    self.tagselector = len(self.tagselection)-1
            elif ch == curses.ascii.BS or ch == curses.KEY_BACKSPACE:
                self.status = MenuState.SELECTDATE
                self.tagselection = []
                self.tagselector = 0
                self.prevtag = ''
                self.newtag = ''
            elif ch == curses.ascii.NL:
                self.status = MenuState.DONE
                self.loadtasks()
        elif self.status == MenuState.DONE:
            if ch == curses.ascii.NL:
                self.status = MenuState.EDITTASK
            elif ch == curses.ascii.TAB:
                self.sendtasks()
                return None,windows.Waction.POP
            elif ch == ord('t'):
                self.status = MenuState.EDITTAG
            elif ch == curses.ascii.BS or ch == curses.KEY_BACKSPACE:
                self.rawtasks = ''
                self.tasks = []
                if len(self.tagselection) > 1:
                    self.status = MenuState.SELECTTAG
                else:
                    self.status = MenuState.SELECTDATE
                    self.tagselection = []
                    self.tagselector = 0
                    self.prevtag = ''
                    self.newtag = ''

        return None,None

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
        er,_ = windows.option(self.win, 'M', 'Mail your tasks', (er,coltab))
        er,_ = windows.option(self.win, 'X', 'Options', (er,coltab))
        er,_ = windows.option(self.win, 'Q', 'Quit', (er,coltab))
        self.erow = er
        StatusBar.update(0)

    def input(self, ch):
        if ch == ord('q'):
            raise SystemExit
        elif ch == ord('a'):
            return AddMenu(self.erow+1,
                           0,
                           self.length-self.erow,
                           self.width), windows.Waction.PUSH
        elif ch == ord('e'):
            return EditMenu(self.erow+1,
                            0,
                            self.length-self.erow,
                            self.width), windows.Waction.PUSH
        elif ch == ord('m'):
            return Mail(self.erow+1,
                        0,
                        self.length-self.erow,
                        self.width), windows.Waction.PUSH
        elif ch == ord('x'):
            return Options(self.erow+1,
                           0,
                           self.length-self.erow,
                           self.width), windows.Waction.PUSH
        return None, None

