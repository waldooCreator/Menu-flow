# Guia 4 - Actividad 7. Trabajando con cadenas
# Walter Esteban Velasco

print("DATOS DE LA PERSONA")
print()

nombre = input("Nombre: ")
apellido = input("Apellido: ")
ciudad = input("Ciudad: ")

nombre_completo = nombre + " " + apellido

print()
print("Hola, " + nombre_completo + ".")
print("Tu nombre tiene " + str(len(nombre)) + " caracteres.")
print("La primera letra de tu nombre es " + nombre[0] + ".")
print("Vives en " + ciudad + ".")
