import curses
from dataclasses import dataclass

ANCHO, ALTO = 50, 10
MIN_FILAS, MIN_COLUMNAS = ALTO + 3, ANCHO + 25

MOVES = {
    "w": (0, -1), "KEY_UP": (0, -1),
    "s": (0, 1),  "KEY_DOWN": (0, 1),
    "a": (-1, 0), "KEY_LEFT": (-1, 0),
    "d": (1, 0),  "KEY_RIGHT": (1, 0),
}


@dataclass
class Entity: #una clase es un concepto que no he usado antes pero que es muy útil en este caso
    x: int    #ya que me define una "plantilla" para las entenidades en este caso
    y: int
    hp: int
    char: str


@dataclass
class Player(Entity):       #plantilla para el jugador a partir de los datos de la entidad
    energy: int = 10        #es decir un player es una entidad
    max_energy: int = 10
    damage: int = 3


@dataclass
class Enemy(Entity):        #lo mismo que con jugador
    damage: int = 1


def in_bounds(x, y):
    return 0 <= x < ANCHO and 0 <= y < ALTO #verificación de si las cordenadas son validas


def sign(n):
    return (n > 0) - (n < 0) #verificación del signo de n para moverse 1,-1 o 0

                                                        #esto es la clase game que es mas complejas porque
class Game:                                             #tiene funciones dentro
    def __init__(self):                                 # basicamente representa la partida entera
        self.player = Player(3, 2, hp=100, char="@")    #define player
        self.enemies = [Enemy(10, 5, hp=10, char="ꬋ")]  #define enemy
        self.rest_streak = 1                            #se crea la racha de descanso para su posterior acumulación

    def entity_at(self, x, y):                          #devuelve que entidad hay en la casilla si es que hay
        for e in (self.player, *self.enemies):          #el "*"desempaqueta la lista por si hay mas enemigos
            if e.x == x and e.y == y:
                return e
        return None

    def free(self, x, y):                                           #verifica si la casilla es valida
        return in_bounds(x, y) and self.entity_at(x, y) is None     #si las cordenadas estan dentro de los
                                                                    #bordes y en la casilla no hay una entidad
    def player_turn(self, key):
        """Devuelve True si el jugador consumió turno."""
        p = self.player

        if key == " ":                                                      #descanso
            p.energy = min(p.energy + 2 * self.rest_streak, p.max_energy)
            self.rest_streak += 1
            return True
        self.rest_streak = 1

        if key not in MOVES or p.energy <= 0: #tecla no valida
            return False

        dx, dy = MOVES[key]
        nx, ny = p.x + dx, p.y + dy #nx y ny es la cordenada del jugador mas la cordenada dx, que es la cordenada que devuelve el pulsar una tecla
        if not in_bounds(nx, ny):
            return False  # chocar con el borde no gasta turno

        target = self.entity_at(nx, ny)
        if target:                              # moverse hacia un enemigo = atacarlo
            target.hp -= p.damage               #esto sería importante darle una vuelta para cuando implemente
            if target.hp <= 0:                  #el ataque a distancia ataques magicos o cualquier paranoia
                self.enemies.remove(target)
        else:
            p.x, p.y = nx, ny                   #si hay movimiento hay un gasto de energia
        p.energy -= 1
        return True

    def enemy_turn(self): #esta funcion hace que el enemigo actue solo una vez
        p = self.player   #guardo las cordenadas del jugador
        for e in self.enemies:  #en este bucle se recorren los enemigos es decir "e" es un enemigo(si hay varios)
            dx, dy = p.x - e.x, p.y - e.y #dx y dy es la diferencia entre el jugador y el enemigo

            if abs(dx) + abs(dy) == 1:  # adyacente: ataca, no se mueve. tengo que pensarme si hacer ataque diagonal
                p.hp -= e.damage        # porque por una parte visualmente es raro pero por otra la diagonal no es 1 sino raiz de 2
                continue

            sx, sy = sign(dx), sign(dy) #utilizo la funcion creada anteriormente para moverme solo 1 casilla por turno comprobando el signo.

            if abs(dx) >= abs(dy):          #orden para priorizar los movimientos
                pasos = [(sx, 0), (0, sy)]
            else:
                pasos = [(0, sy), (sx, 0)]

            for mx, my in pasos:
                if (mx, my) != (0, 0) and self.free(e.x + mx, e.y + my):    #verificar pasos
                    e.x += mx
                    e.y += my
                    break


def draw_world(stdscr, game):
    stdscr.erase()
    for y in range(ALTO):
        stdscr.addstr(y, 0, "." * ANCHO)
    for e in game.enemies:
        stdscr.addch(e.y, e.x, e.char, curses.color_pair(2))
    p = game.player
    stdscr.addch(p.y, p.x, p.char, curses.color_pair(1))
    if p.energy <= 0:
        stdscr.addstr(ALTO + 2, 0, "You need to rest! (Press SPACE)")
    stdscr.noutrefresh()


def draw_stats(win, game):
    p = game.player
    win.erase()
    win.box()
    info = [f"Energy: {p.energy}/{p.max_energy}", f"Vida: {p.hp}/100", "Oro: 50"]
    for i, texto in enumerate(info):
        win.addstr(1 + i, 1, texto)
    win.noutrefresh()


def main(stdscr):
    filas, columnas = stdscr.getmaxyx()
    if filas < MIN_FILAS or columnas < MIN_COLUMNAS:
        raise SystemExit(
            f"Terminal demasiado pequeña: necesitas al menos "
            f"{MIN_COLUMNAS}x{MIN_FILAS} (tienes {columnas}x{filas})."
        )

    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    win_stats = curses.newwin(10, 20, 0, ANCHO + 5)

    game = Game()
    while game.player.hp > 0:
        draw_world(stdscr, game)
        draw_stats(win_stats, game)
        curses.doupdate()

        key = stdscr.getkey()
        if key == "q":
            break
        if game.player_turn(key):
            game.enemy_turn()


curses.wrapper(main)
