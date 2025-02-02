import minestar
logger = minestar.initApp()
import datastore, mstarpaths, i18n
from Tkinter import *


WIDTH = 400
HEIGHT = 300

class Gui:
    def __init__(self):
        self.root = Tk()
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()
        if h * 2 < w:
            w = h * 4 / 3
        x = (w - WIDTH) / 2
        y = (h - HEIGHT) / 2
        self.root.geometry("+%d+%d" % (x, y))
        topFrame = Frame(self.root, width=WIDTH, height=HEIGHT)
        topFrame.grid(row=0, column=0, sticky=E+W+N+S)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        topFrame.columnconfigure(0, weight=1)


    def mainloop(self):
        self.root.mainloop()

if __name__ == '__main__':
    mstarpaths.loadMineStarConfig()
    gui = Gui()
    gui.mainloop()
