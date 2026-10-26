import curses
from dataclasses import dataclass
import time
import math
from traceback import format_list

ANCHO, ALTO = 10000, 10000
MIN_FILAS, MIN_COLUMNAS = 20, 100

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
    name: str

@dataclass
class Player(Entity):       #plantilla para el jugador a partir de los datos de la entidad
    energy: int = 100      #es decir un player es una entidad
    max_energy: int = 100
    damage: int = 3
    last_hurt: float = 0.0

@dataclass
class NPC(Entity):
    pass

@dataclass
class Enemy(Entity):        #lo mismo que con jugador
    damage: int = 1
    speed: float = 1.0
    charge: float = 0.0

    def act(self, game):
        # El sistena de velocidad será igual para todos los enemigos
        self.charge += self.speed #la carga de este enemigo se le suma la velocidad
        while self.charge >= 1:
            self.charge -= 1
            self.take_action(game)

    def take_action(self, game):
        #cuerpo a cuerpo
        p = game.player
        dx, dy = p.x - self.x, p.y - self.y

        if abs(dx) + abs(dy) == 1:
            p.hp -= self.damage
            p.last_hurt = time.time()
            add_message(f"{self.name} dealt {self.damage} to you ({p.hp}/100)", 26)
        else:
            self.step(game, dx, dy)

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
            if (mx, my) != (0, 0) and game.free(self.x + mx, self.y + my): #voler aqui
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
            dx, dy = sign(p.x - self.x), sign(p.y - self.y)
            # Asigna la flecha correcta según la dirección
            if dx == 1: char_flecha = "→"
            elif dx == -1: char_flecha = "←"
            elif dy == 1: char_flecha = "↓"
            else: char_flecha = "↑"

            game.projectiles.append({
                "x": self.x, "y": self.y, "tx": p.x, "ty": p.y,
                "dx": dx, "dy": dy, "damage": self.damage, "shooter": self.name,
                "char": char_flecha
            })
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
    "goblin": {"cls": Enemy, "hp": 10, "damage": 1, "speed": 2.0,   "char": "g", "name": "goblin"},
    "orc":    {"cls": Enemy, "hp": 30, "damage": 4, "speed": 0.5, "char": "O", "name": "orc"},
    "archer": {"cls": Archer, "hp": 30, "damage": 4, "speed": 0.5, "char": "a", "range": 6, "min_dist": 2, "name": "archer"},
}


def spawn(kind, x, y):                  #spawn enemies
    data = dict(ENEMY_TYPES[kind])
    clas = data.pop("cls")
    return clas(x, y, **data)
                                                    #esto es la clase game que es mas complejas porque
class Game:                                             #tiene funciones dentro
    def __init__(self):                                     # basicamente representa la partida entera
        self.player = Player(0, 0, hp=100, char="@", name="player")    #define player
        self.enemies = [spawn("archer", 10, 4), spawn("goblin", 5, 4), spawn("orc", 3, 7)]  #spawn enemy
        self.rest_streak = 1  #se crea la racha de descanso para su posterior acumulación
        self.effects = []
        """SISTEMA DE UBICACIÓN Y EDIFICIOS"""
        self.location = "world" # Corregido a "world"
        self.return_coords = (0, 0)

        #map interior de la cabaña
        self.cabin_map = {}

        self.map = {
            (5, 5): "#",
            (6, 5): "#",
            (5000, 8000): "#"
        }
        #Puerta al exterior (Definida DESPUÉS de self.map)
        self.door_outside = (2, 2)
        self.map[self.door_outside] = "🚪"
        self.incos = NPC(x=10, y=5, hp=100, char="I", name="incos")
        self.crops = {}
        self.integration = 0
        self.inventory = []
        self.ground_items = {}
        self.altars = {
            (2500, 2500): {"name": "Altar del Noroeste", "active": True},
            (7500, 2500): {"name": "Altar del Noreste", "active": True},
            (2500, 7500): {"name": "Altar del Suroeste", "active": True},
            (7500, 7500): {"name": "Altar del Sureste", "active": True},
        }
        self.projectiles = []
        self.build_cabin()

    def build_cabin(self):
        #paredes
        width, height = 20, 12
        for x in range(width):
            for y in range(height):
                #poner "#" en los bordes
                if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                    self.cabin_map[(x, y)] = "#"
                else:
                    self.cabin_map[(x, y)] = "." # Suelo interior
        #puerta de salida desde dentro de la cabaña
        self.door_inside = (10, 11)
        self.cabin_map[self.door_inside] = "·"

    def advance_crops(self):
        for pos in list(self.crops.keys()):
            if self.crops[pos] > 0:
                self.crops[pos] -= 1

    def get_tile(self, x, y):
        if 0 <= x < 10000 and 0 <= y < 10000:
            return self.map.get((x, y), ".")
        return " "

    def free(self, x, y):
        if self.location == "world":
            return 0 <= x < 10000 and 0 <= y < 10000 \
                and self.map.get((x, y)) != "#" \
                and self.entity_at(x, y) is None
        else:
            return self.cabin_map.get((x, y)) != "#" \
                and self.entity_at(x, y) is None

    def entity_at(self, x, y):
        if self.location == "world":
            entities = (self.player, *self.enemies)
        else:
            entities = (self.player, self.incos)
                                                #devuelve que entidad hay en la casilla si es que hay
        for e in entities:          #el "*"desempaqueta la lista por si hay mas enemigos
            if e.x == x and e.y == y:
                return e
        return None
                                                                    #bordes y en la casilla no hay una entidad

    def player_turn(self, key):
        p = self.player

        if key == " ":                                                           #descanso
            p.energy = min(p.energy + 2 * self.rest_streak, p.max_energy)
            self.rest_streak += 1
            add_message(f"You rested! ({p.energy}/100)", 25)
            self.advance_crops()
            return True
        self.rest_streak = 1

        #hechizo
        if key == "h" and self.location == "world":
            if p.energy >= 10:
                p.energy -= 10
                active_altars = [data for data in self.altars.values() if data["active"]]
                if not active_altars:
                    add_message("All the altars have been destroyed. The veil is tearing...", 26)
                else:
                    nearest_name = None
                    min_dist = float("inf")
                    for (ax, ay), data in self.altars.items():
                        if data["active"]:
                            dist = math.hypot(ax - p.x, ay - p.y)
                            if dist < min_dist:
                                min_dist = dist
                                nearest_name = data["name"]
                    add_message(f"Spell: The {nearest_name} pulses at ~{int(min_dist)}m.", 27)
                self.advance_crops()
                return True
            else:
                add_message("You don't have enough energy to cast the spell (you need 10).", 26)
                return False

        if (key not in MOVES and key != "f") or p.energy <= 0: #tecla no valida
            return False
        #Agricultura
        if self.location == "cabin" and key == "f":
            pos = (p.x, p.y)
            tile = self.cabin_map.get(pos)

            if tile == "." or tile == "·":
                if pos not in self.crops:
                    if p.energy >= 5:
                        p.energy -= 5
                        self.crops[pos] = 6
                        add_message("You planted a seed in the soil.", 25)
                        self.advance_crops()
                        return True
                    else:
                        add_message("You are too exhausted to plow the land.", 26)
                        return False
                elif self.crops[pos] <= 0:
                    del self.crops[pos]
                    p.max_energy += 5
                    p.hp = min(p.hp + 15, 100)
                    self.integration = min(100, self.integration + 10)
                    add_message(f"You harvested! Max energy +5. Integration: {self.integration}%", 25)
                    self.advance_crops()
                    return True
                else:
                    add_message(f"The crop is still growing ({self.crops[pos]} turns remaining).", 27)
                    return False

        dx, dy = MOVES.get(key, (0, 0))
        nx, ny = p.x + dx, p.y + dy #nx y ny es la cordenada del jugador mas la cordenada dx, que es la cordenada que devuelve el pulsar una tecla
        if self.location == "world":
            if (nx, ny) == self.door_outside:
                self.return_coords = (p.x, p.y)
                self.location = "cabin"
                p.x, p.y = 10, 10 #posición al aparecer dentro
                add_message("You entered Inco's cabin.", 25)
                return True
            if not in_bounds(nx, ny):
                return False
        elif self.location == "cabin":
            if (nx, ny) == self.door_inside:
                self.location = "world" # Corregido a "world"
                p.x, p.y = self.return_coords
                add_message("You left to the exterior", 25)
                return True
            if not (0 <= nx < 20 and 0 <= ny < 12):
                return False
        #COLISIONES
        current_map = self.map if self.location == "world" else self.cabin_map
        if current_map.get((nx, ny)) == "#":
            return False
        if not in_bounds(nx, ny):
            return False  # chocar con el borde no gasta turno

        target = self.entity_at(nx, ny)
        if target: # moverse hacia un enemigo = atacarlo
            if self.location == "cabin" and target == self.incos:
                if time.time() - p.last_hurt < 10.0:
                    add_message("Incos touches his side: 'Ugh... I feel a strange pain, as if you had been the one attacked.'", 26)
                else:
                    add_message("Incos smiles: 'The land is peaceful today. Rest a while.'", 25)
                return False
            elif self.location == "world":
                target.hp -= p.damage
                add_message(f"You dealt {p.damage} damage to the {target.name}.", 25)
                if target.hp <= 0:
                    self.enemies.remove(target)
                    # Soltar objeto de lore al morir
                    drops = {
                        "goblin": "Cristal parabrisas",
                        "orc": "Informe médico",
                        "archer": "Reloj (03:14)",
                        "The Moon Lord": "Núcleo estelar"
                    }
                    item_dropped = drops.get(target.name, "Nota borrosa")
                    self.ground_items[(target.x, target.y)] = item_dropped
                    add_message(f"The {target.name} dropped: {item_dropped}", 27)
        else:
            p.x, p.y = nx, ny                   #si hay movimiento hay un gasto de energia
            # Recoger objetos del suelo
            if self.location == "world" and (p.x, p.y) in self.ground_items:
                picked = self.ground_items.pop((p.x, p.y))
                self.inventory.append(picked)
                add_message(f"Picked up: {picked}!", 25)

            # Destruir altares al pisarlos y activar jefe final si se destruyen todos
            if self.location == "world" and (p.x, p.y) in self.altars and self.altars[(p.x, p.y)]["active"]:
                self.altars[(p.x, p.y)]["active"] = False
                remaining_altars = sum(1 for a in self.altars.values() if a["active"])
                add_message(f"You have destroyed the {self.altars[(p.x, p.y)]['name']}! {remaining_altars} altars remain.", 26)
                if remaining_altars == 0:
                    add_message("The last altar has fallen! The Moon Lord has descended into the world...", 26)
                    self.enemies.append(Enemy(x=p.x + 2, y=p.y + 2, hp=150, damage=6, speed=1.0, char="M", name="The Moon Lord"))

        p.energy -= 1
        self.advance_crops()
        return True

    def enemy_turn(self): #esta funcion hace que el enemigo actue solo una vez
        if self.location != "world":
            return
        for e in self.enemies:
            e.act(self)

def get_grass_color(x, y):
    wave1 = math.sin(x / 31.0) + math.cos(y / 29.0)
    wave2 = math.sin((x + y) / 13.0)
    wave3 = math.sin(x / 7.0) * math.cos(y / 5.0)

    noise = (wave1 + wave2 + wave3 + 4.0) / 8.0
    noise = max(0.0, min(1.0, noise))

    index = int(noise * 23)
    return max(1, min(24, index + 1))

def draw_world(stdscr, game):
    WIDTH_VIEW = 100
    HIGHT_VIEW = 20  #vista en terminal
    stdscr.erase()

    cam_x, cam_y = 0, 0
    if game.location == "world":
        #Renderizado del mudnoa bierto
        # Calcular la posición de la cámara centrada en el jugador
        cam_x = game.player.x - (WIDTH_VIEW // 2)
        cam_y = game.player.y - (HIGHT_VIEW // 2)
        MAX_MUNDO_X = 10000
        MAX_MUNDO_Y = 10000
        cam_x = max(0, min(cam_x, MAX_MUNDO_X - WIDTH_VIEW))# la parte de min() lo que hace es calcular la posición ideal cuando estas en el borde. En el borde la camara no se mueve porque esta
        cam_y = max(0, min(cam_y, MAX_MUNDO_Y - HIGHT_VIEW))


        # Dibujar el terreno visible
        for y in range(HIGHT_VIEW):
            for x in range(WIDTH_VIEW):

                world_x = cam_x + x
                world_y = cam_y + y
                tile = game.map.get((world_x, world_y)) # Usando game.map unificado
                if tile == "🚪":
                    try:
                        stdscr.addstr(y, x, "🚪", curses.color_pair(27))
                    except curses.error:
                        pass
                else:
                    color_id = get_grass_color(world_x, world_y)# dibuja el mundo a partir de la camara

                    try:
                        stdscr.addch(y, x, " ", curses.color_pair(color_id))
                    except curses.error:
                        pass # Evita errores si se dibuja en la última celda de la terminal

        # Dibujar los altares activos en el mundo abierto (∆)
        for (ax, ay), data in game.altars.items():
            if data["active"] and cam_x <= ax < cam_x + WIDTH_VIEW and cam_y <= ay < cam_y + HIGHT_VIEW:
                try:
                    stdscr.addch(ay - cam_y, ax - cam_x, "∆", curses.color_pair(27))
                except curses.error:
                    pass

        for (gx, gy), item_name in game.ground_items.items():
            if cam_x <= gx < cam_x + WIDTH_VIEW and cam_y <= gy < cam_y + HIGHT_VIEW:
                try:
                    stdscr.addch(gy - cam_y, gx - cam_x, "?", curses.color_pair(27))
                except curses.error:
                    pass
        # Dibujar enemigos que estén dentro del campo de visión
        for e in game.enemies:
            if cam_x <= e.x < cam_x + WIDTH_VIEW and cam_y <= e.y < cam_y + HIGHT_VIEW:
                # Posición en pantalla = Posición real - Posición de la cámara
                pantalla_x = e.x - cam_x
                pantalla_y = e.y - cam_y
                try:
                    stdscr.addch(pantalla_y, pantalla_x, e.char, curses.color_pair(26))
                except curses.error:
                    pass

        for proj in game.projectiles:
            pantalla_px = proj["x"] - cam_x
            pantalla_py = proj["y"] - cam_y
            if 0 <= pantalla_px < WIDTH_VIEW and 0 <= pantalla_py < HIGHT_VIEW:
                try:
                    stdscr.addstr(pantalla_py, pantalla_px, proj["char"], curses.color_pair(27))
                except curses.error:
                    pass


    else:
        #RENDERIZADO INTERIOR DE LA CABAÑA
        for (x, y), tile in game.cabin_map.items():
            try:
                if tile == "#":
                    stdscr.addch(y, x, "#", curses.color_pair(28))
                else:
                    if (x, y) in game.crops:
                        turns = game.crops[(x, y)]
                        char_crop = "*" if turns <= 0 else ","
                        color_crop = 25 if turns <= 0 else 27
                        stdscr.addch(y, x, char_crop, curses.color_pair(color_crop))
                    else:
                        stdscr.addch(y, x, "·", curses.color_pair(1))
            except curses.error:
                pass
        try:
            stdscr.addch(game.incos.y, game.incos.x, game.incos.char, curses.color_pair(25))
        except curses.error:
            pass
        try:
            stdscr.addstr(game.door_inside[1], game.door_inside[0], "🚪", curses.color_pair(27))
        except curses.error:
            pass

    # Dibujar al jugador (siempre en el centro relativo de la cámara en el mundo, o posición real en la cabaña)
    p = game.player
    if game.location == "world":
        pantalla_px = p.x - cam_x
        pantalla_py = p.y - cam_y
    else:
        pantalla_px, pantalla_py = p.x, p.y


    parpadeo_activo = time.time() - p.last_hurt < 2.0
    ocultar_sprite = parpadeo_activo and int(time.time() * 10) % 2 == 0

    if not ocultar_sprite:
        try:
            stdscr.addch(pantalla_py, pantalla_px, p.char, curses.color_pair(25))
        except curses.error:
            pass

    # Mensajes del sistema
    if p.energy <= 0:
        stdscr.addstr(HIGHT_VIEW, 0, "You need to rest! (Press SPACE)", curses.color_pair(25))

    stdscr.noutrefresh()

combat_log = []
MAX_MESSAGES = 8
def add_message(text, color_id=0):
    combat_log.append((text, color_id))
    if len(combat_log) > MAX_MESSAGES:
        combat_log.pop(0)

def draw_log(win):
    win.erase()
    win.box()
    win.addstr(0, 2, " Combat Log ")

    alto, ancho = win.getmaxyx()

    for i, (mensaje, color_id) in enumerate(reversed(combat_log)):
        if 1 + i < alto - 1:
            win.addstr(1 + i, 1, mensaje, curses.color_pair(color_id))

    win.noutrefresh()

def draw_stats(win, game): #la ventana se crea en main()
    p = game.player
    win.erase()
    win.box()
    info = [f"Energy: {p.energy}/{p.max_energy}", f"Health: {p.hp}/100", f"X={p.x}", f"Y={p.y}", f"Integ.: {game.integration}%"]
    for i, texto in enumerate(info):
        win.addstr(1 + i, 1, texto)
    win.noutrefresh()

def draw_inv(win, game):
    win.erase()
    win.box()
    win.addstr(0, 2, " Inventory ")
    alto, ancho = win.getmaxyx()
    if not game.inventory:
        win.addstr(1, 1, "(Empty)", curses.color_pair(0))
    else:
        for i, item in enumerate(game.inventory):
            if 1 + i < alto - 1:
                win.addstr(1 + i, 1, f"• {item[:15]}", curses.color_pair(27))
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
    curses.init_pair(25, curses.COLOR_GREEN, curses.COLOR_BLACK)#color de personaje
    curses.init_pair(26, curses.COLOR_RED, curses.COLOR_BLACK)#color del enemigo
    curses.init_pair(27, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    if curses.can_change_color():
        curses.init_color(150, 600, 300, 0)
        curses.init_pair(28, 150, curses.COLOR_BLACK)
    else:
        curses.init_pair(28, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    win_stats = curses.newwin(10, 20, 0, 105 + 5)
    win_log = curses.newwin(10, 100, 21, 0)
    win_inv = curses.newwin(21, 20, 10, 110) # Ventana de inventario en el hueco libre
    DEGRADED = 24
    if curses.can_change_color():
        for k in range(DEGRADED):
            # Calcula el tono de verde (escala 0-1000)
            green = int(120 + (800 - 120) * k / (DEGRADED - 1))
            curses.init_color(100 + k, 0, green, 0)

            # Crea el par: ID (1 a 24), Color de Texto (Negro), Color de Fondo (Tono Verde)
            curses.init_pair(k + 1, curses.COLOR_BLACK, 100 + k)

    stdscr.timeout(50)
    game = Game()
    while game.player.hp > 0:
        if game.projectiles:
            for proj in game.projectiles[:]:
                proj["x"] += proj["dx"]
                proj["y"] += proj["dy"]
                if (proj["x"], proj["y"]) == (proj["tx"], proj["ty"]):
                    game.player.hp -= proj["damage"]
                    game.player.last_hurt = time.time()
                    add_message(f"The {proj['shooter']} shot you for {proj['damage']} damage!", 26)
                    game.projectiles.remove(proj)
                elif not in_bounds(proj["x"], proj["y"]) or game.get_tile(proj["x"], proj["y"]) == "#":
                    game.projectiles.remove(proj)
            draw_world(stdscr, game)
            curses.doupdate()
            time.sleep(0.05)
            continue
        draw_world(stdscr, game)
        draw_stats(win_stats, game)
        draw_log(win_log)
        draw_inv(win_inv, game)
        curses.doupdate()

        try:
            key = stdscr.getkey()
        except curses.error:
            key = None

        if key == "q":
            break
        if key and game.player_turn(key):
            game.enemy_turn()

    stdscr.erase()
    msg = "¡Has ganado!" if game.player.hp > 0 else "¡Has muerto!"
    stdscr.addstr(ALTO // 2, (ANCHO - len(msg)) // 2, msg)
    stdscr.refresh()
    stdscr.timeout(-1)
    stdscr.getkey()

curses.wrapper(main)
