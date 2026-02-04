import curses

class Colors:
    '''
    Colors class sets up the colors for the curses interface
    '''
    _instance = None
    
    def __new__(obj, *args, **kwargs):
        if not obj._instance:
            obj._instance = super().__new__(obj)
            obj._instance._initialized = False
        return obj._instance
    
    def __init__(self, display=True):
        '''
        Set up the color pairs for the curses interface
        '''
        if not self._initialized:
            self._initialized = True
            colors = [
                'black',
                'red',
                'green',
                'yellow',
                'blue',
                'magenta',
                'cyan',
                'white',
                'white_inv',
                'yellow_bg'
            ]
            if display:
                self.cursesColors()
                for idx,color in enumerate(colors):
                    setattr(self, color, curses.color_pair(idx+1))
            else:
                for idx,color in enumerate(colors):
                    setattr(self, color, None)

    def cursesColors(self):
        '''
        Create the color pairs for the curses module
        '''
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_YELLOW)
