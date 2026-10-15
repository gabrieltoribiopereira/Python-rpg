import curses
from curses import wrapper
from player import energy, maxEnergy

ANCHO = 50
ALTO = 10
mapa = [["." for x in range(ANCHO)] for y in range(ALTO)]
px = 3
py = 2

def draw(stdscr):
    stdscr.erase()

    # Es mejor inicializar los colores al principio
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    green = curses.color_pair(1)

    for y in range(ALTO):
        for x in range(ANCHO):
            if x == px and y == py:
                # Usamos addstr() en lugar de addch() para caracteres Unicode
                stdscr.addstr(y, x, "ꬋ", green)
            else:
                stdscr.addch(y, x, mapa[y][x])

    stdscr.refresh()
    stdscr.getch()

wrapper(draw)
