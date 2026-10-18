# Guia 4 - Actividad 12. Agregar y eliminar
# Walter Esteban Velasco

productos = ["Hamburguesa clasica", "Salchipapa"]

print("PRODUCTOS DEL MENU")

productos.append("Perro caliente")
productos.append("Alitas BBQ")

print()
print("Despues de agregar dos productos:")
print(productos)

# La salchipapa sale de la carta porque no se esta vendiendo.
productos.remove("Salchipapa")

print()
print("Despues de eliminar la salchipapa:")
print(productos)

productos.append("Mazorcada")

print()
print("Resultado final:")
print(productos)
