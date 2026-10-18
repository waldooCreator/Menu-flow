# Guia 4 - Actividades 15, 16 y 17. Integracion al proyecto
# Walter Esteban Velasco

# ACTIVIDAD 15. ANALISIS
#
# NOMBRE DEL PROYECTO: Sistema web de gestion para restaurantes.
# FUNCIONALIDAD: el menu que ve el cliente y que la cocina prepara.
# INFORMACION QUE NECESITA ALMACENAR: los platos de una estacion, en este
#   caso los de cocina.
# POR QUE NECESITA VARIOS ELEMENTOS: un restaurante no vende un solo plato.
#   La carta cambia seguido: entran platos nuevos, se cambian nombres y se
#   quitan los que no se venden. Guardar un plato en una variable suelta
#   obligaria a crear una variable por cada plato.
# DATOS QUE TENDRA CADA ELEMENTO: por ahora el nombre del plato. Mas
#   adelante cada plato lleva tambien precio, categoria y estacion.

# ACTIVIDAD 16 Y 17. IMPLEMENTACION CON LAS MEJORAS

platos = ["Hamburguesa clasica", "Perro caliente", "Alitas BBQ"]

print("PLATOS DE LA ESTACION DE COCINA")
print()
print("Lista actual:")
print(platos)
print()

# Consultar un plato por su posicion, validando que exista.
posicion = int(input("Posicion que quieres consultar (0 a " + str(len(platos) - 1) + "): "))

if posicion >= 0 and posicion < len(platos):
    print("En esa posicion esta: " + platos[posicion])
else:
    print("Esa posicion no existe en la lista.")

print()

# Agregar un plato nuevo. No se acepta vacio.
nuevo = input("Plato que quieres agregar: ")

if nuevo == "":
    print("No se agrego nada porque el nombre venia vacio.")
else:
    platos.append(nuevo)
    print("Plato agregado.")

print()
print("Lista despues de agregar:")
print(platos)
print()

# Modificar un plato existente.
posicion = int(input("Posicion del plato que quieres modificar: "))

if posicion >= 0 and posicion < len(platos):
    cambio = input("Nuevo nombre para ese plato: ")
    if cambio == "":
        print("No se modifico nada porque el nombre venia vacio.")
    else:
        anterior = platos[posicion]
        platos[posicion] = cambio
        print("Se cambio " + anterior + " por " + cambio + ".")
else:
    print("Esa posicion no existe, no se modifico nada.")

print()
print("INFORMACION ACTUALIZADA")
print(platos)
