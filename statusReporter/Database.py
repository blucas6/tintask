import sqlite3
import datetime
import os

from statusReporter.DBTables import DBTables
from statusReporter.Format import Format

class Database:
    def __init__(self):
        self.dbfailurelog = 'dblog.txt'
        self.dbcon = ''
        self.dbcursor = ''
        self.DB_NULL = 'N/A'
        self.DB_DATE_FORMAT = '%Y-%m-%d'
        self.dbfile = self.getDatabaseLocation()
        
    def getDatabaseLocation(self):
        cdatabase_d = os.path.join(os.path.expanduser('~'), "AppData", "Local", "StatusReporter")
        cdatabase_f = os.path.join(cdatabase_d, "config.db")
        if os.path.exists(cdatabase_d):
            try:
                dbcon = sqlite3.connect(cdatabase_f)
                dbcursor = dbcon.cursor()
                res = dbcursor.execute(f"SELECT * FROM {DBTables.location}").fetchall()
                if res:
                    return res[0][0]
                else:
                    raise Exception("Database configuration error")
            except Exception as e:
                self.DBError(e)
        else:
            self.DBError("Couldn't find configuration database!")
        return ''
            
    def setup(self):
        try:
            self.dbcon = sqlite3.connect(self.dbfile)
            self.dbcursor = self.dbcon.cursor()
        except Exception as e:
            self.DBError(e)
            raise e

        if not self.checkForTable(DBTables.status):
            self.dbcursor.execute(f"CREATE TABLE {DBTables.status}(date DATE, chargecode TEXT, task TEXT)")
            self.dbcon.commit()
        if not self.checkForTable(DBTables.charge):
            self.dbcursor.execute(f"CREATE TABLE {DBTables.charge}(code TEXT, active bool)")
            self.dbcon.commit()
        if not self.checkForTable(DBTables.config):
            raise Exception()
        try:
            return self.dbcursor.execute(f"SELECT * FROM {DBTables.config}").fetchall()[0]
        except Exception as e:
            self.DBError(e)
            raise e

    def addConfigProperties(self, mailto, subject, header, footer, signature):
        try:
            if not self.checkForTable(DBTables.config):
                cmd = f"CREATE TABLE {DBTables.config}(mailto, subject, header, footer, signature)"
                self.dbcursor.execute(cmd)
                self.dbcon.commit()
                cmd = f"INSERT INTO {DBTables.config} VALUES ('{mailto}','{subject}','{header}','{footer}','{signature}')"
                self.dbcursor.execute(cmd)
                self.dbcon.commit()
            else:
                row = self.dbcursor.execute(f"SELECT * FROM {DBTables.config}").fetchall()
                cmd = f"UPDATE {DBTables.config} SET mailto='{mailto}', subject='{subject}', header='{header}', footer='{footer}', signature='{signature}' WHERE mailto='{row[0]}'"
                self.dbcursor.execute(cmd)
                self.dbcon.commit()
        except Exception as e:
            self.DBError(e, msg=cmd)

    def checkForTable(self, tablename):
        res = self.dbcursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tablename}'").fetchall()
        if res:
            return True
        return False

    def addRowToDatabase(self, table, vals=[]):
        if vals:
            values = "("
            for v in vals:
                values += f"'{v}'"
                if v != vals[-1]:
                    values += ','
                else:
                    values += ')'
            try:
                cmd = f"INSERT INTO {table} VALUES {values}"
                self.dbcursor.execute(cmd)
                self.dbcon.commit()
            except Exception as e:
                self.DBError(e, msg=cmd+' - '+','.join(vals))
    
    def manageChargeCodes(self, mycode):
        # add a new charge code, make it active
        # if it already present, delete it
        # if the deleted charge code was active, pick a new active
        bar, codes, listofcodes = self.getChargeCodeSelector()
        if mycode in listofcodes:
            try:
                self.dbcursor.execute(f"DELETE FROM {DBTables.charge} WHERE code='{mycode}'")
                self.dbcon.commit()
                available = self.dbcursor.execute(f"SELECT * FROM {DBTables.charge}").fetchall()
                if available:
                    self.dbcursor.execute(f"UPDATE {DBTables.charge} SET active=1 WHERE code='{available[0][0]}'")
                    self.dbcon.commit()
            except Exception as e:
                self.DBError(e)
        else:
            try:
                res = self.dbcursor.execute(f"SELECT * FROM {DBTables.charge} WHERE active=1").fetchall()
                for code in res:
                    self.dbcursor.execute(f"UPDATE {DBTables.charge} SET active=0 WHERE code='{code[0]}'")
                self.dbcursor.execute(f"INSERT INTO {DBTables.charge} VALUES ('{mycode}',1)")
                self.dbcon.commit()
            except Exception as e:
                self.DBError(e)

    def getChargeCodeSelector(self):
        codes = self.getChargeCodesfromDB()
        bar = '['
        for code in codes:
            if code[1]:
                bar += Format.bgwhite+Format.fgblack+code[0]+Format.end
            else:
                bar += code[0]
            if code != codes[-1]:
                bar += ','
        bar += ']'
        return bar, codes, [c[0] for c in codes]

    def changeDateFormat(self, date, format1, format2):
        return datetime.datetime.strptime(date, format1).strftime(format2)

    def getTasksfromDB(self, datestart, dateend):
        try:
            return self.dbcursor.execute(f"SELECT * FROM {DBTables.status} WHERE date >= '{datestart}' AND date <= '{dateend}' ORDER BY date ASC;").fetchall()
        except Exception as e:
            self.DBError(e)

    def organizeDBTasksToDict(self, taskrows):
        tasks = {}
        for date, chargec, task in taskrows:
            # check if date has been added
            if date in tasks:
                # if charge code has been added
                if chargec in tasks[date]:
                    # append the newest task
                    tasks[date][chargec].append(task)
                else:
                    # or add a new slot for the code
                    tasks[date][chargec] = [task]
            else:
                # or add a new date slot and dict
                tasks[date] = {chargec: [task]}
        return tasks

    def getStatusForDay(self, day):
        return self.dbcursor.execute(f"SELECT * FROM {DBTables.status} WHERE date={datetime.datetime.strftime(day, self.DB_DATE_FORMAT)}").fetchall()

    def clearWeek(self):
        start, end = self.getCurrentWeekStEn()
        self.dbcursor.execute(f"DELETE FROM {DBTables.status} WHERE date >= '{start.strftime(self.DB_DATE_FORMAT)}' AND date <= '{end.strftime(self.DB_DATE_FORMAT)}'")
        self.dbcon.commit()

    def getChargeCodesfromDB(self):
        try:
            return self.dbcursor.execute(f"SELECT * FROM {DBTables.charge}").fetchall()
        except Exception as e:
            self.DBError(e)

    def DBError(self, e, msg=''):
        with open(self.dbfailurelog, 'a+') as log:
            log.write(f'{datetime.datetime.now()} - {msg} {e}\n')

    def handleConfigUpdate(self, column, new):
        try:
            cmd = f"SELECT * FROM {DBTables.config}"
            row = self.dbcursor.execute(cmd).fetchall()[0]
            cmd = f"UPDATE {DBTables.config} SET {column}='{new}' WHERE mailto='{row[0]}'"
            self.dbcursor.execute(cmd)
            self.dbcon.commit()
        except Exception as e:
            self.DBError(e, msg=cmd)

    def deleteWork(self, day):
        try:
            try:
                self.dbcursor.execute(f"DELETE FROM {DBTables.status} WHERE date='{day.strftime(self.DB_DATE_FORMAT)}';")
                self.dbcon.commit()
            except Exception as e:
                self.DBError(e)
        except Exception as e:
            print(f'Failed to remove {day}! -> {e}')
            input('<enter>')

    def swapActiveChargeCodes(self, curr, new):
        self.dbcursor.execute(f"UPDATE {DBTables.charge} SET active=0 WHERE code='{curr}'")
        self.dbcursor.execute(f"UPDATE {DBTables.charge} SET active=1 WHERE code='{new}'")

    def close(self):
        try:
            self.dbcon.close()
        except Exception as e:
            self.DBError(e)