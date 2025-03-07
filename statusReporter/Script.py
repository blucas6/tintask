import os
import datetime
from datetime import timedelta
import time
import win32com.client as win32

from statusReporter import Database
from statusReporter import Animator
from statusReporter.Format import Format
from statusReporter.DBTables import DBTables

class Script:
    def __init__(self):
        self.database = Database.Database()
        self.animator = Animator.Animator()
        while True:
            try:
                config = self.database.setup()
                self.MAIL_TO = config[0].split(';')
                self.EMAIL_SUBJECT = config[1]
                self.EMAIL_HEADER = config[2]
                self.EMAIL_FOOTER = config[3]
                self.EMAIL_SIGNATURE = config[4]
                break
            except Exception as e:
                self.freshInstall()
        self.DATE_FORMAT = '%A %B %d, %Y'
        self.ARCHIVEAREA = 'archive'
        self.COLUMN_WIDTH = 60
        self.DELIM = '&&'
        self.MAX_REPORT_LENGTH = 30
        self.EXTRA_LINES = 7
    
    def resizeTerminal(self):
        lines = self.displayMessage(forterminal=True).split('\n')
        cleanlines = []
        for line in lines:
            clean = self.verifyMsgLength(line).split('\n')
            for l in clean:
                cleanlines.append(l)
        os.system('cls')
        if len(cleanlines) > self.MAX_REPORT_LENGTH+self.EXTRA_LINES:
            buffer = len(cleanlines)-self.MAX_REPORT_LENGTH-self.EXTRA_LINES
        else:
            buffer = 0
        x = os.get_terminal_size().lines+buffer+self.EXTRA_LINES
        y = os.get_terminal_size().columns
        os.system(f'mode {y},{x}')

    def main(self):
        self.resizeTerminal()
        while True:
            lines = self.displayMessage(forterminal=True).split('\n')
            cleanlines = []
            for line in lines:
                clean = self.verifyMsgLength(line).split('\n')
                for l in clean:
                    cleanlines.append(l)
            os.system('cls')
            for i,line in enumerate(cleanlines):
                self.moveCursor(i,self.COLUMN_WIDTH)
                print(line)
            self.moveCursor(0, 0)
            print(Format.bgwhite+Format.fgblack+' Generate Status Report '+Format.end)
            print(self.MenuOption('A', 'Add what you worked on today'))
            print(self.MenuOption('E', 'Edit specific date'))
            print(self.MenuOption('S', 'Send the email'))
            # print(self.MenuOption('X', 'Clear current status report'))
            print(self.MenuOption('C', 'Change configurations'))
            print(self.MenuOption('F', 'Off-Friday'))
            print(self.MenuOption('M', 'Manage charge codes'))
            print(self.MenuOption('Q', 'Quit'))
            self.moveCursor(10,0)
            c = self.askforInput()
            if c == 'a':
                self.addWork(datetime.datetime.now())
            elif c == '`':
                self.sendAnimation()
            elif c == 'e':
                self.editMessage()
            elif c == 's':
                self.sendMessage() 
            elif c == 'c':
                self.changeConfig()
            elif c == 'q':
                self.database.close()
                break   
            # elif c == 'x':
            #     if input('Confirm delete (y/n): ') == 'y':
            #         self.database.clearWeek()    
            elif c == 'f':
                self.offFriday()
            elif c == 'm':
                self.ChargeCodeMenu()
    
    def sendAnimation(self):
        startrow = 16
        startcol = 5
        print("Sending....")
        for num,frame in enumerate(self.animator.frames):
            for r,line in enumerate(frame[1]):            
                self.moveCursor(startrow+r, startcol)
                print(line)
            time.sleep(frame[0])
            if num == 3:
                mail = "                          "
                for i in range(len(mail)):
                    self.moveCursor(startrow+3, startcol+12)
                    send = ""
                    for m in range(len(mail)):
                        if m == i:
                            send += "M"
                        elif m < i:
                            send += "="
                        else:
                            send += " "
                    print(send)
                    time.sleep(0.05)
        self.moveCursor(startrow, startcol)
        print('Sent!')

    def askQuestion(self, q):
        while True:
            ans = input('\n'+q+'\n>')
            yn = input('\tGood? (y/n or (S)kip)').lower()
            if yn == 'y' or yn == 'yes' or yn == '':
                return ans
            elif yn != 'n' and yn != 'no':
                return ' '
    
    def freshInstall(self):
        # Start User prompts sequence
        os.system('cls')
        print(Format.fgblack+Format.bgwhite+' Set up '+Format.end)
        mailto = self.askQuestion('Who to send the Status Report to?')
        subject = self.askQuestion('What should the subject title be?')
        header = self.askQuestion('What greeting would you like to use?')
        footer = self.askQuestion('Write your sign-off format (do not include signature)')
        signature = self.askQuestion('Write your signature')
        self.database.addConfigProperties(mailto, subject, header, footer, signature)

    def askforInput(self):
        return input(Format.bold+'Command: '+Format.end).lower()
    
    def moveCursor(self, x, y):
        print("\033[%d;%dH" % (x,y), end="")

    def verifyMsgLength(self, msg):
        # remove escape codes when counting length
        if len(Format.ansicodes.sub('', msg)) >= self.COLUMN_WIDTH-2 and not '====' in msg:
            closest = self.COLUMN_WIDTH
            for i,c in enumerate(msg):
                if c == ' ' and i>4:
                    if self.COLUMN_WIDTH - i < closest and self.COLUMN_WIDTH - i > 0:
                        closest = self.COLUMN_WIDTH - i
            if closest < self.COLUMN_WIDTH:
                ind = -1*(closest-self.COLUMN_WIDTH)
                msg = self.verifyMsgLength(msg[:ind]) + '\n' + self.verifyMsgLength(msg[ind+1:])
            else:
                msg = self.verifyMsgLength(msg[:self.COLUMN_WIDTH-4]) + '\n' + self.verifyMsgLength(msg[self.COLUMN_WIDTH-3:])
        return msg

    def MenuOption(self, letter, text):
        return f'{Format.bold}({letter}):{Format.end} {text}'

    def offFriday(self):
        weekday = 4
        todaynum = datetime.datetime.now().weekday()
        if todaynum - weekday > 0:
            period = datetime.datetime.now() - timedelta(days=todaynum-weekday)
        else:
            period = datetime.datetime.now() + timedelta(days=weekday-todaynum)
        self.database.addRowToDatabase(DBTables.status, [datetime.datetime.strftime(period, self.database.DB_DATE_FORMAT), self.database.DB_NULL, 'Off-Friday'])

    def border(self, title, forterminal=False):
        halfs = round((self.COLUMN_WIDTH - len(title) - 2)/2) # -2 for 2 spaces around the title
        title = '\n'+('='*halfs)+' '+title+' '+('='*halfs)
        if len(title) < 60:
            title += '='
        elif len(title) > 60:
            title = title[:-1]
        title += '\n'
        if forterminal:
            return Format.bold + title + Format.end
        else:
            return title

    def ChargeCodeMenu(self):
        while True:
            self.moveCursor(11, 0)
            print("\nCharge codes:")
            bar, codes, loc = self.database.getChargeCodeSelector()
            print('                                            ')
            self.moveCursor(13,0)
            print(bar)
            print('Add a charge code:')
            print('                                            ')
            self.moveCursor(15,0)
            do = input(' >')
            if do == '':
                break
            self.database.manageChargeCodes(do)

    def displayMessage(self, forterminal=False):
        if forterminal:
            bold = Format.bold
            clear = Format.end
        else:
            bold = ''
            clear = ''
        report = self.border('INFO', forterminal=forterminal)
        report +=f'{bold}Send to: {clear}{self.createMailtoList()}\n'
        report +=f'{bold}Subject: {clear}{self.createSubject()}'
        report += self.border('EMAIL', forterminal=forterminal)
        report += self.createReportDB(forterminal=forterminal)
        report += self.border('EMAIL', forterminal=forterminal)
        return report
    
    def createReportDB(self, forterminal=False):
        report = self.EMAIL_HEADER + '\n'
        report += 'Weekly Status Report:'
        if forterminal:
            report += '\n'
        start, end = self.getCurrentWeekStEn()
        res = self.database.getTasksfromDB(start.strftime(self.database.DB_DATE_FORMAT), end.strftime(self.database.DB_DATE_FORMAT))
        if res:
            tasks = self.database.organizeDBTasksToDict(res)
            for date, vals in tasks.items():
                report += '\n'
                if forterminal:
                    report += Format.bgwhite + Format.fgblack
                else:
                    report += '\n'
                report += self.database.changeDateFormat(date, self.database.DB_DATE_FORMAT, self.DATE_FORMAT) + ':\n'
                if forterminal:
                    report += Format.end
                for charge, ts in vals.items():
                    if charge == self.database.DB_NULL:
                        for t in ts:
                            report += '\t-- '+t+'\n'
                    else:
                        if forterminal:
                            report += Format.uline
                        report += charge
                        if forterminal:
                            report += Format.end
                        report += '\n'
                        for t in ts:
                            report += '\t-- '+t+'\n'

        report += '\n\n' + self.EMAIL_FOOTER + '\n'
        report += '\t' + self.EMAIL_SIGNATURE
        return report
    
    def getCurrentWeekStEn(self):
        start = datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().weekday())
        end = start + datetime.timedelta(days=6)
        return start, end

    def editMessage(self):
        while True:
            self.moveCursor(11,0)
            text = f'What date do you want to {Format.bold}change{Format.end}? (ex. M/T/W/Th/F or dM/dT/dW/dTh/dF to {Format.bold}delete{Format.end} a day or (Q)uit)'
            print()
            print(self.verifyMsgLength(text))
            print('                                                ')
            self.moveCursor(14,0)
            c = self.askforInput()
            todaynum = datetime.datetime.now().weekday()
            deletemode = False
            if c:
                if c[0] == 'd':
                    c = c[1:]
                    deletemode = True
                if c == 'm':
                    weekdaynum = 0
                elif c == 't':
                    weekdaynum = 1
                elif c == 'w':
                    weekdaynum = 2
                elif c == 'th':
                    weekdaynum = 3
                elif c == 'f':
                    weekdaynum = 4
                elif c == 'q':
                    break
                else:
                    continue
            else:
                continue
            if todaynum - weekdaynum > 0:
                period = datetime.datetime.now() - timedelta(days=todaynum-weekdaynum)
            else:
                period = datetime.datetime.now() + timedelta(days=weekdaynum-todaynum)
            if deletemode:
                self.database.deleteWork(period)
            else:
                day = self.database.getStatusForDay(period)
                if not day:
                    changedate = input(f"Default date: {Format.bold}{period.strftime('%A %d')}{Format.end} - Change date? (yes): ")
                    if changedate == 'y' or changedate == 'Y' or changedate == 'yes' or changedate == 'Yes':
                        newdate = input('New date: ')
                        try:
                            period = period.replace(day=int(newdate))
                        except Exception as e:
                            print(f'Failed -> {e}')
                            input('<enter>')
                self.addWork(period, extrabuff=6)
            break

    def chooseChargeCode(self, extrarows=0):
        while True:
            self.moveCursor(15+extrarows,0)
            print('Select Charge Code (enter,<-z:x->):')
            bar, codes, loc = self.database.getChargeCodeSelector()
            for i,code in enumerate(codes):
                if code[1]:
                    cc = i
            print('                                            ')
            self.moveCursor(16+extrarows,0)
            print(bar)
            print('                                            ')
            self.moveCursor(17+extrarows,0)
            ans = input(' >')
            if ans == 'z' or ans == 'x':
                diff = 0
                if ans == 'z':
                    diff = -1
                else:
                    diff = 1
                try:
                    self.database.swapActiveChargeCodes(codes[cc][0], codes[(cc+diff)%len(codes)][0])
                except Exception as e:
                    self.database.DBError(e)
            elif ans == '':
                return cc

    def addWork(self, day, extrabuff=0):
        key = day.strftime(self.DATE_FORMAT)
        tasks = []
        print()
        print('What did you do on '+day.strftime('%A')+'?')
        toadd = input(' >')
        if toadd != "":
            tasks.append(toadd)
            while True:
                add = input(' >')
                if add == "":
                    break
                tasks.append(add)
                extrabuff += 1
            # check for charge codes
            codes = self.database.getChargeCodesfromDB()
            cc = 0
            if codes:
                cc = self.chooseChargeCode(extrarows=extrabuff)
            c = input("Add to report? (enter,n):").lower()
            if c != "n":
                data = []
                if codes:
                    currentcode = codes[cc][0]
                else:
                    currentcode = self.database.DB_NULL
                for t in tasks:
                    data = [datetime.datetime.strptime(key,self.DATE_FORMAT).strftime(self.database.DB_DATE_FORMAT), currentcode, t]
                    self.database.addRowToDatabase(DBTables.status, data)

    def createSubject(self):
        start, end = self.getCurrentWeekStEn()
        if start != '' and end != '':
            return self.EMAIL_SUBJECT+f' ({start.strftime("%m/%d")}-{end.strftime("%m/%d")})'
        else:
            return self.EMAIL_SUBJECT

    def createMailtoList(self):
        tmp = ""
        for name in self.MAIL_TO:
            if name != self.MAIL_TO[-1]:
                tmp += name + '; '
            else:
                tmp += name
        return tmp

    def sendMessage(self):
        try:
            outlook = win32.Dispatch('outlook.application')
            mail = outlook.CreateItem(0)
            mail.To = self.createMailtoList()
            mail.Subject = self.createSubject()
            mail.Body = self.createReportDB()
            # mail.HTMLBody = self.createReport(HTML=True)
            send = input('Enter S to send. Enter anything else to quit\nChoice: ')
        except Exception as e:
            print(f'Failed to create email -> {e}')
            input('<enter>')
        else:
            if send == 'S':
                try:
                    mail.Send()
                    self.sendAnimation()
                except Exception as e:
                    print(f'FAILED to send! -> ({e})')
                    input('<enter>')
            else:
                print('Exiting...')

    def makeConfigChange(self, variable, column, mode='new'):
        if mode == 'delete':
            while True:
                print('Which one from the choices above? or (Q)uit')
                c = self.askforInput()
                if c == 'q' or c == 'Q':
                    return
                try:
                    c = int(c)
                    del variable[c]
                    new = "; ".join(variable)
                    break
                except Exception as e:
                    pass
        elif mode == 'add':
            variable.append(input(f'(Q to Quit)\nNew recipient: '))
            new = "; ".join(variable)
        else:
            new = input(f"New {column}: ")
        self.database.handleConfigUpdate(column, new)
        return new

    def changeConfig(self):
        while True:
            print()
            print(self.verifyMsgLength(f'{Format.uline}Subject:{Format.end} {self.createSubject()}'))
            print(self.verifyMsgLength(f'{Format.uline}Recipient:{Format.end} {self.createMailtoList()}'))
            print(self.verifyMsgLength(f'{Format.uline}Header:{Format.end} {self.EMAIL_HEADER}'))
            print(self.verifyMsgLength(f'{Format.uline}Footer:{Format.end} {self.EMAIL_FOOTER}'))
            print(self.verifyMsgLength(f'{Format.uline}Signature:{Format.end} {self.EMAIL_SIGNATURE}'))
            print(Format.bold+'Edit what?'+Format.end)
            print(self.MenuOption('U', 'Subject'))
            print(self.MenuOption('R', 'Recipient'))
            print(self.MenuOption('H', 'Header'))
            print(self.MenuOption('F', 'Footer'))
            print(self.MenuOption('S', 'Signature'))
            print(self.MenuOption('Q', 'Quit'))
            c = self.askforInput()
            if c == 'r':
                print(f"Which one? {self.MenuOption('Q', 'Quit')}  {self.MenuOption('A', 'Add')}  {self.MenuOption('D', 'Delete')}")
                for i,name in enumerate(self.MAIL_TO):
                    print(self.MenuOption(i, name))
                c = self.askforInput()
                if c == 'q' or c == 'Q':
                    break
                if c == 'a' or c == 'A':
                    self.makeConfigChange(self.MAIL_TO, 'mailto', mode='add')
                elif c == 'd' or c == 'D':
                    self.makeConfigChange(self.MAIL_TO, 'mailto', mode='delete')
                else:
                    continue
                break
            elif c == 'h':
                self.EMAIL_HEADER = self.makeConfigChange(self.EMAIL_HEADER, 'header')
            elif c == 'f':
                self.EMAIL_FOOTER = self.makeConfigChange(self.EMAIL_FOOTER, 'footer')
            elif c == 's':
                self.EMAIL_SIGNATURE = self.makeConfigChange(self.EMAIL_SIGNATURE, 'signature')
            elif c == 'u':
                self.EMAIL_SUBJECT = self.makeConfigChange(self.EMAIL_SUBJECT, 'subject')
            elif c == 'q':
                break
            else:
                continue
            break