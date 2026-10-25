import curses
from dataclasses import dataclass

ANCHO, ALTO = 10000, 10000
MIN_FILAS, MIN_COLUMNAS = 20,100

MOVES = {
    "w": (0, -1), "KEY_UP": (0, -1),
    "s": (0, 1),  "KEY_DOWN": (0, 1),
    "a": (-1, 0), "KEY_LEFT": (-1, 0),
    "d": (1, 0),  "KEY_RIGHT": (1, 0),
}

def in_bounds(x, y):
    return 0 <= x < ANCHO and 0 <= y < ALTO #verificación de si las cordenadas son validas

def sign(n):
    return (n > 0) - (n < 0) #verificación del signo de n para moverse 1,-1 o 0

@dataclass
class Entity: #una clase es un concepto que no he usado antes pero que es muy útil en este caso
    x: int    #ya que me define una "plantilla" para las entenidades en este caso
    y: int
    hp: int
    char: str


@dataclass
class Player(Entity):       #plantilla para el jugador a partir de los datos de la entidad
    energy: int = 100        #es decir un player es una entidad
    max_energy: int = 100
    damage: int = 3


@dataclass
class Enemy(Entity):        #lo mismo que con jugador
    damage: int = 1
    speed: float = 1.0
    charge: float = 0.0
    def act(self, game):
        # El sistena de velocidad será igual para todos los enemigos
        self.charge+=self.speed #la carga de este enemigo se le suma la velocidad
        while self.charge >= 1:
            self.charge -= 1
            self.take_action(game)
    def take_action(self, game):
        #cuerpo a cuerpo
        p = game.player
        dx, dy = p.x - self.x, p.y - self.y

        if abs(dx) +abs(dy)==1:
            p.hp-=self.damage
        else:
            self.step(game, dx, dy) #entender
    def step(self, game, dx, dy, away=False):
        #funcion para moverse. Sirve tanto para perseguir como para alejar
        if away:
            dx, dy = -dx, -dy # Invierte la dirección para alejarse
        sx, sy = sign(dx), sign(dy)

        if abs(dx) <= abs(dy):          #Obtienes el signo así que solo indicas la dirección del movimiento y la cantidad de pasos esta determinada por la velocidad de la entidad
           pasos = [(sx, 0), (0, sy)]
        else:
           pasos = [(0, sy), (sx, 0)]

        for mx, my in pasos:
            if (mx, my)!=(0,0) and game.free(self.x+mx, self.y+my): #voler aqui
                self.x += mx
                self.y += my
                break

@dataclass
class Archer(Enemy): # Hereda de Enemy para aprovechar speed, charge y el método step()
    range: int = 6
    min_dist: int = 2

    def take_action(self, game):
        # Sobreescribimos el comportamiento para que actúe como arquero
        p = game.player
        dx, dy = p.x - self.x, p.y - self.y
        dist = abs(dx) + abs(dy)

        if dist < self.min_dist:
            self.step(game, dx, dy, away=True) # Huye si está muy cerca
        elif dist <= self.range and self.clear_shot(game):
            p.hp -= self.damage                # Dispara si está a rango y alineado
        else:
            self.step(game, dx, dy)            # Se acerca para buscar ángulo

    def clear_shot(self, game):
        p = game.player
        if self.x != p.x and self.y != p.y:
            return False  # No está alineado ortogonalmente

        dx, dy = sign(p.x - self.x), sign(p.y - self.y)
        x, y = self.x + dx, self.y + dy

        while (x, y) != (p.x, p.y):
            if not game.free(x, y):
                return False  # Hay un obstáculo (otro enemigo) bloqueando la flecha
            x, y = x + dx, y + dy

        return True


ENEMY_TYPES = {
    "goblin": {"cls": Enemy,"hp": 10, "damage": 1, "speed": 2,   "char": "g"},
    "orc":    {"cls": Enemy,"hp": 30, "damage": 4, "speed": 0.5, "char": "O"},
    "archer":    {"cls": Archer,"hp": 30, "damage": 4, "speed": 0.5, "char": "a", "range": 6, "min_dist":2},
}


def spawn(kind, x, y):                  #spawn enemies
    data = dict(ENEMY_TYPES[kind])
    clas = data.pop("cls")
    return clas(x, y, ** data)
                                                    #esto es la clase game que es mas complejas porque
class Game:                                             #tiene funciones dentro
    def __init__(self):                                 # basicamente representa la partida entera
        self.player = Player(3, 2, hp=100, char="@")    #define player
        self.enemies = [spawn("archer", 10, 4 ),spawn("goblin", 5, 4 ),spawn("orc", 3, 7 )]  #spawn enemy
        self.rest_streak = 1  #se crea la racha de descanso para su posterior acumulación
        self.effects=[]
        self.mapa = {
            (5,5):"#",
            (6,5):"#",
            (5000, 8000): "#" # Coordenada extrema sin gastar RAM intermedia
        }
    def get_tile(self, x, y):
        if 0<= x < 10000 and 0<= y< 10000:
            return self.mapa.get((x,y), ".")
        return " "
    def free(self, x, y):
            return 0 <= x < 10000 and 0 <= y < 10000 \
                and self.mapa.get((x, y)) != "#" \
                and self.entity_at(x, y) is None
    def entity_at(self, x, y):                          #devuelve que entidad hay en la casilla si es que hay
        for e in (self.player, *self.enemies):          #el "*"desempaqueta la lista por si hay mas enemigos
            if e.x == x and e.y == y:
                return e
        return None
                                                                    #bordes y en la casilla no hay una entidad
    def player_turn(self, key):
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
        for e in self.enemies:
            e.act(self)


def draw_world(stdscr, game):
    WIDTH_VIEW = 100
    HIGHT_VIEW = 20  #vista en terminal

    # Calcular la posición de la cámara centrada en el jugador
    cam_x = game.player.x - (WIDTH_VIEW // 2)
    cam_y = game.player.y - (HIGHT_VIEW // 2)
    MAX_MUNDO_X = 10000
    MAX_MUNDO_Y = 10000
    cam_x = max(0, min(cam_x, MAX_MUNDO_X -WIDTH_VIEW))# la parte de min() lo que hace es calcular la posición ideal cuando estas en el borde. En el borde la camara no se mueve porque esta
    cam_y = max(0, min(cam_y, MAX_MUNDO_Y -WIDTH_VIEW))
    stdscr.erase()

    # 1. Dibujar el terreno visible
    for y in range(HIGHT_VIEW):
        for x in range(WIDTH_VIEW):
            world_x = cam_x + x
            world_y = cam_y + y
            tile = game.get_tile(world_x, world_y) # dibuja el mundo a partir de la camara
            try:
                stdscr.addch(y, x, tile)
            except curses.error:
                pass # Evita errores si se dibuja en la última celda de la terminal

    # 2. Dibujar enemigos que estén dentro del campo de visión
    for e in game.enemies:
        if cam_x <= e.x < cam_x + WIDTH_VIEW and cam_y <= e.y < cam_y + HIGHT_VIEW:
            # Posición en pantalla = Posición real - Posición de la cámara
            pantalla_x = e.x - cam_x
            pantalla_y = e.y - cam_y
            stdscr.addch(pantalla_y, pantalla_x, e.char, curses.color_pair(2))

    # 3. Dibujar al jugador (siempre en el centro relativo de la cámara)
    p = game.player
    pantalla_px = p.x - cam_x
    pantalla_py = p.y - cam_y
    stdscr.addch(pantalla_py, pantalla_px, p.char, curses.color_pair(1))

    # 4. Mensajes del sistema
    if p.energy <= 0:
        stdscr.addstr(HIGHT_VIEW, 0, "You need to rest! (Press SPACE)")

    stdscr.noutrefresh()


def draw_stats(win, game):
    p = game.player
    win.erase()
    win.box()
    info = [f"Energy: {p.energy}/{p.max_energy}", f"Healt: {p.hp}/100", f"X={p.x}",f"Y={p.y}"]
    for i, texto in enumerate(info):
        win.addstr(1 + i, 1, texto)
    win.noutrefresh()

#def play_effects(stdscr, win_stats, game):

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
    win_stats = curses.newwin(10, 20, 0, 105 + 5)

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

    stdscr.erase()
    msg = "¡Has ganado!" if game.player.hp > 0 else "¡Has muerto!"
    stdscr.addstr(ALTO // 2, (ANCHO - len(msg)) // 2, msg)
    stdscr.refresh()
    stdscr.getkey()

curses.wrapper(main)
