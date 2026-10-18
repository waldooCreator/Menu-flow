# Guia 4 - Actividad 10. Modificar informacion
# Walter Esteban Velasco

# Las mesas del salon con su estado. Es informacion que el sistema del
# restaurante tiene que cambiar todo el tiempo durante el servicio.

mesas = ["Mesa 1 libre", "Mesa 2 libre", "Mesa 3 libre", "Mesa 4 libre", "Mesa 5 libre"]

print("ESTADO DE LAS MESAS")
print()
print("Al abrir el restaurante:")
print(mesas)

# Llegan clientes a la mesa 2.
mesas[1] = "Mesa 2 ocupada"

print()
print("Despues de sentar a un cliente en la mesa 2:")
print(mesas)

# La mesa 4 queda apartada por una reserva.
mesas[3] = "Mesa 4 apartada"

print()
print("Despues de apartar la mesa 4:")
print(mesas)
