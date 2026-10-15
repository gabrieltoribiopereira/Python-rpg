import curses
from player import energy, maxEnergy

ANCHO = 50
ALTO = 10
mapa = [["." for x in range(ANCHO)] for y in range(ALTO)]
px = 3
py = 2

MIN_FILAS = ALTO + 3
MIN_COLUMNAS = ANCHO + 5 + 20


def XvalidMovement(x):
    return 0 <= x < ANCHO


def YvalidMovement(y):
    return 0 <= y < ALTO


def tired(e):
    return e <= 0


def draw_world(stdscr):
    stdscr.erase()
    green = curses.color_pair(1)
    for y in range(ALTO):
        for x in range(ANCHO):
            if x == px and y == py:
                stdscr.addch(y, x, "@", green)
            else:
                stdscr.addch(y, x, mapa[y][x])
    if tired(energy):
        stdscr.addstr(ALTO + 2, 0, "You need to rest! (Press SPACE)")
    stdscr.noutrefresh()


def draw_stats(win_stats):
    win_stats.erase()
    win_stats.box()
    info = [f"Energy: {energy}/{maxEnergy}", "Vida: 100/100", "Oro: 50"]
    for i, texto in enumerate(info):
        win_stats.addstr(1 + i, 1, texto)
    win_stats.noutrefresh()


def main(stdscr):
    global px, py, energy
    contador = 1

    filas, columnas = stdscr.getmaxyx()
    if filas < MIN_FILAS or columnas < MIN_COLUMNAS:
        raise SystemExit(
            f"Terminal demasiado pequeña: necesitas al menos "
            f"{MIN_COLUMNAS}x{MIN_FILAS} (tienes {columnas}x{filas})."
        )

    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    win_stats = curses.newwin(10, 20, 0, ANCHO + 5)

    while True:
        draw_world(stdscr)
        draw_stats(win_stats)
        curses.doupdate()

        key = stdscr.getkey()  # bloqueante: espera a que pulses una tecla

        if key == "q":
            break

        # Descansar
        if key == " ":
            energy = min(energy + 2 * contador, maxEnergy)
            contador += 1
            continue
        contador = 1

        # Sin energía no puedes moverte
        if tired(energy):
            continue

        nx, ny = px, py
        if key in ("w", "KEY_UP"):
            ny -= 1
        elif key in ("s", "KEY_DOWN"):
            ny += 1
        elif key in ("a", "KEY_LEFT"):
            nx -= 1
        elif key in ("d", "KEY_RIGHT"):
            nx += 1
        else:
            continue

        if XvalidMovement(nx) and YvalidMovement(ny):
            px, py = nx, ny
            energy -= 1


curses.wrapper(main)
