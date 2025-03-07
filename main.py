from colorama import just_fix_windows_console

from statusReporter import Script

just_fix_windows_console()

if __name__ == "__main__":
    s = Script.Script()
    s.main()