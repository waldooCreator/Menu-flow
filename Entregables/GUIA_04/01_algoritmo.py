# Guia 4 - Actividades 1, 2, 3 y 4
# Walter Esteban Velasco

# ACTIVIDAD 1. ANALISIS DE PROBLEMAS
#
# Situacion 1: cobrar un domicilio
# PROBLEMA: al cobrar un domicilio hay que sumarle el valor del envio a lo
#   que valen los platos, y el mesero lo hace de memoria.
# DATOS DE ENTRADA: valor de los platos, valor del envio.
# PROCESO: sumar los dos valores.
# RESULTADO: el total que debe pagar el cliente.
# PASOS PARA SOLUCIONARLO:
#   1. Pedir el valor de los platos.
#   2. Pedir el valor del envio.
#   3. Sumarlos.
#   4. Mostrar el total.
#
# Situacion 2: saber si el efectivo alcanza
# PROBLEMA: el cliente paga en efectivo y hay que saber si el billete alcanza
#   y cuanto se le devuelve.
# DATOS DE ENTRADA: total de la cuenta, dinero recibido.
# PROCESO: comparar el dinero recibido con el total y restar.
# RESULTADO: el vuelto, o el aviso de que falta plata.
# PASOS PARA SOLUCIONARLO:
#   1. Pedir el total.
#   2. Pedir el dinero recibido.
#   3. Si el recibido es mayor o igual al total, restar y mostrar el vuelto.
#   4. Si no, avisar cuanto falta.
#
# Situacion 3: cuanto se demoro un pedido
# PROBLEMA: no se sabe cuanto tiempo pasa entre que un pedido entra a cocina
#   y sale listo.
# DATOS DE ENTRADA: minuto en que entro, minuto en que salio.
# PROCESO: restar los dos minutos.
# RESULTADO: el tiempo que tardo la preparacion.
# PASOS PARA SOLUCIONARLO:
#   1. Pedir el minuto de entrada.
#   2. Pedir el minuto de salida.
#   3. Restar.
#   4. Mostrar el tiempo.

# ACTIVIDAD 2. ALGORITMO (situacion 1)
#
# INICIO
#   Solicitar el valor de los platos.
#   Solicitar el valor del envio.
#   Sumar el valor de los platos y el valor del envio.
#   Mostrar el total a pagar.
# FIN

# ACTIVIDAD 3. PSEUDOCODIGO
#
# INICIO
#   LEER platos
#   LEER envio
#   total = platos + envio
#   ESCRIBIR "Total a pagar: ", total
# FIN

# ACTIVIDAD 4. EL PSEUDOCODIGO EN PYTHON

print("CALCULO DEL TOTAL DE UN DOMICILIO")
print()

platos = int(input("Valor de los platos: "))
envio = int(input("Valor del envio: "))

total = platos + envio

print()
print("Platos: " + str(platos))
print("Envio: " + str(envio))
print("Total a pagar: " + str(total))
