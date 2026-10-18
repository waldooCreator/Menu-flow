# Guia 4 - Actividad 9. Consulta de elementos
# Walter Esteban Velasco

bebidas = ["Limonada", "Gaseosa", "Jugo de mora", "Cerveza", "Agua", "Cafe"]

print("CONSULTA POR POSICION")
print()
print("Lista: ")
print(bebidas)
print()
print("Primer elemento: " + bebidas[0])
print("Segundo elemento: " + bebidas[1])
print("Ultimo elemento: " + bebidas[-1])
print("Penultimo elemento: " + bebidas[-2])

posicion = int(input("Escribe una posicion entre 0 y 5: "))
print("En esa posicion esta: " + bebidas[posicion])

# La guia pide modificar la lista y volver a consultar.
bebidas[3] = "Cerveza artesanal"
bebidas[5] = "Tinto"

print()
print("Despues de modificar la lista:")
print(bebidas)
print("Ultimo elemento: " + bebidas[-1])
print("Penultimo elemento: " + bebidas[-2])
