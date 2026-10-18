# Guia 4 - Actividad 13. Registro de informacion
# Walter Esteban Velasco

# Registro de los platos que pide una mesa. Es lo que hace el mesero cuando
# toma el pedido: va anotando uno por uno y al final revisa cuantos van.

pedido = []

print("REGISTRO DE UN PEDIDO")
print()

plato = input("Primer plato: ")
pedido.append(plato)

plato = input("Segundo plato: ")
pedido.append(plato)

plato = input("Tercer plato: ")
pedido.append(plato)

print()
print("PEDIDO REGISTRADO")
print(pedido)
print()
print("Platos registrados: " + str(len(pedido)))
