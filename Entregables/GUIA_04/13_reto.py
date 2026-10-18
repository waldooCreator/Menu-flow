# Guia 4 - Actividades 18 y 19. Reto
# Walter Esteban Velasco

# Administracion de los platos de una estacion del restaurante: registrar,
# consultar, agregar, modificar y mostrar. Es la misma problematica del
# proyecto, resuelta aqui con listas.

platos = []

print("PLATOS DE LA ESTACION DE COCINA")
print()

plato = input("Primer plato: ")
platos.append(plato)

plato = input("Segundo plato: ")
platos.append(plato)

plato = input("Tercer plato: ")
platos.append(plato)

print()
print("Platos registrados:")
print(platos)
print()

# Consultar por posicion
posicion = int(input("Posicion que quieres consultar (0 a " + str(len(platos) - 1) + "): "))

if posicion >= 0 and posicion < len(platos):
    print("Plato en esa posicion: " + platos[posicion])
else:
    print("Esa posicion no existe.")

print()

# Agregar
nuevo = input("Plato nuevo para la estacion: ")

if nuevo == "":
    print("No se agrego nada.")
else:
    platos.append(nuevo)
    print(nuevo + " quedo agregado.")

print()

# Modificar
posicion = int(input("Posicion del plato que quieres corregir: "))

if posicion >= 0 and posicion < len(platos):
    cambio = input("Nombre corregido: ")
    if cambio == "":
        print("No se modifico nada.")
    else:
        platos[posicion] = cambio
        print("Plato corregido.")
else:
    print("Esa posicion no existe.")

print()
print("INFORMACION ALMACENADA")
print(platos)

# ACTIVIDAD 18. PRUEBAS
#
# PRUEBA 1
# DATOS UTILIZADOS: platos Hamburguesa, Perro y Alitas; consultar la posicion
#   1; agregar Mazorcada; corregir la posicion 0 por Hamburguesa doble.
# RESULTADO ESPERADO: la lista queda con cuatro platos y el primero cambiado.
# RESULTADO OBTENIDO: correcto, mostro los cuatro platos con el cambio.
#
# PRUEBA 2
# DATOS UTILIZADOS: consultar la posicion 7 de una lista de tres platos.
# RESULTADO ESPERADO: un aviso de que la posicion no existe, sin que el
#   programa se caiga.
# RESULTADO OBTENIDO: correcto, mostro "Esa posicion no existe".
#
# PRUEBA 3
# DATOS UTILIZADOS: dejar vacio el plato nuevo, solo dar Enter.
# RESULTADO ESPERADO: no agregar nada y avisarlo.
# RESULTADO OBTENIDO: correcto, la lista quedo igual.
#
# PRUEBA 4
# DATOS UTILIZADOS: platos Limonada, Gaseosa y Cerveza; corregir la posicion
#   2 por Cerveza artesanal.
# RESULTADO ESPERADO: el ultimo plato de la lista cambia.
# RESULTADO OBTENIDO: correcto.
#
# En la primera version el programa se caia al escribir una posicion que no
# existia. Se reviso donde ocurria, se agregaron las comparaciones con
# len(platos) y se volvio a ejecutar.
