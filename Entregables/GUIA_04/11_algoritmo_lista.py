# Guia 4 - Actividad 14. Algoritmo para trabajar con una lista
# Walter Esteban Velasco

# ANALISIS
#
# PROBLEMA: la cocina necesita saber que platos lleva listos en el turno, y
#   hoy eso se lleva de memoria o en un papel que se pierde.
# DATOS DE ENTRADA: el nombre de cada plato que sale listo.
# DATOS QUE SE ALMACENARAN: una lista con los platos entregados en el turno.
# PROCESO: guardar cada plato en la lista y contarlos.
# RESULTADO: la lista de lo que salio y cuantos platos fueron.
# PASOS PARA SOLUCIONARLO:
#   1. Crear una lista vacia.
#   2. Pedir el nombre de cada plato que sale de la cocina.
#   3. Agregarlo a la lista.
#   4. Mostrar la lista y la cantidad.

# ALGORITMO
#
# INICIO
#   Crear una lista vacia de platos entregados.
#   Solicitar el primer plato y agregarlo a la lista.
#   Solicitar el segundo plato y agregarlo a la lista.
#   Solicitar el tercer plato y agregarlo a la lista.
#   Mostrar la lista.
#   Contar los elementos y mostrar la cantidad.
# FIN

# PSEUDOCODIGO
#
# INICIO
#   entregados = lista vacia
#   LEER plato
#   AGREGAR plato A entregados
#   LEER plato
#   AGREGAR plato A entregados
#   LEER plato
#   AGREGAR plato A entregados
#   ESCRIBIR entregados
#   ESCRIBIR "Platos entregados: ", cantidad de entregados
# FIN

# IMPLEMENTACION

entregados = []

print("PLATOS ENTREGADOS EN EL TURNO")
print()

plato = input("Plato entregado: ")
entregados.append(plato)

plato = input("Plato entregado: ")
entregados.append(plato)

plato = input("Plato entregado: ")
entregados.append(plato)

print()
print("Entregados en este turno:")
print(entregados)
print("Cantidad: " + str(len(entregados)))
