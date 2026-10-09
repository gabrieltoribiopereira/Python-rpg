from player import energy, maxEnergy
ANCHO = 50
ALTO = 10
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
    print(f"{energy}/{maxEnergy}")
def XvalidMovement(x):
        return 0 <= x < ANCHO
def YvalidMovement(y):
        return 0 <= y < ALTO
def movimiento():
    global px,py,energy
    contador=1
    while True:
        dibujar()
        m=input()
        nx=px
        ny=py
        if m==" ":
            energy=min(energy+2*contador, maxEnergy)
            contador+=1
            continue
        else:
            contador=1
        if energy <=0:
            print("You need to rest")
            continue
        if m=="w":
            ny=py-1
        elif m=="s":
            ny=py+1
        elif m=="a":
            nx=px-1
        elif m=="d":
            nx=px+1

        else:
            continue

        if XvalidMovement(nx) and YvalidMovement(ny):
            px =nx
            py=ny
            energy-=1
movimiento()
