ANCHO = 8
ALTO = 5
mapa = [["." for x in range(ANCHO)] for y in range(ALTO)]

px = 3
py = 2

def dibujar():
    for y in range(ALTO):
        fila = ""
        for x in range(ANCHO):
            if x == px and y == py:
                fila = fila + "@"
            else:
                fila = fila + mapa[y][x]
        print(fila)

def movimiento():
    global px,py
    while True:
        dibujar()
        m=input()
        nx=px
        ny=py
        if m=="w":
            ny=ny-1
        elif m=="s":
            ny=ny+1
        elif m=="a":
            nx=nx-1
        elif m=="d":
            nx=nx+1
        else:
            break
        px =nx
        py=ny
movimiento()
