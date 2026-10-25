import curses
import time

DEGRADED = 24  # número de tonos del degradado


def color_gradient(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)


    colors = []
    DEGRADED=24
    for k in range(DEGRADED): #crea los tonos y los pone en pares
        green = int(120 + (800 - 120) * k / (DEGRADED - 1))  # escala de curses: 0-1000
        curses.init_color(100 + k, 0, green, 0)
        curses.init_pair(k + 1, 15, 100 + k)  # 15 = blanco
        colors.append(curses.color_pair(k + 1))

    while True:
        for x, color in enumerate(colors):
            stdscr.addstr(0, x, " ", color)
        stdscr.refresh()
        time.sleep(0.05)

curses.wrapper(color_gradient)
