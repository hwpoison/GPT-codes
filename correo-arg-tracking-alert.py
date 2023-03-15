import time

import requests
from bs4 import BeautifulSoup
from win10toast import ToastNotifier

url = "<URL>"

# Configurar la instancia de ToastNotifier
toaster = ToastNotifier()

# Obtener la página web
response = requests.get(url)
html = response.content

# Analizar el HTML de la página
soup = BeautifulSoup(html, 'html.parser')

# Buscar la tabla de seguimiento
tabla_seguimiento = soup.find('div', {'id': 'resultado'}).find('table')

# Almacenar la tabla previa para compararla con la nueva
tabla_previa = tabla_seguimiento

while True:
    # Esperar 10 segundos antes de volver a revisar la página
    time.sleep(10)

    # Obtener la página web
    response = requests.get(url)
    html = response.content

    # Analizar el HTML de la página
    soup = BeautifulSoup(html, 'html.parser')

    # Buscar la tabla de seguimiento
    tabla_seguimiento = soup.find('div', {'id': 'resultado'}).find('table')

    # Obtener todos los elementos <tr> dentro de la tabla
    filas = tabla_seguimiento.find_all('tr')

    # Seleccionar el último elemento de la lista de filas
    ultima_fila = filas[1]

    # Obtener el contenido de cada celda de la última fila
    celdas = ultima_fila.find_all('td')
    fecha = celdas[0].text.strip()
    planta = celdas[1].text.strip()
    historia = celdas[2].text.strip()
    estado = celdas[3].text.strip()

    # Comparar la tabla previa con la nueva
    if tabla_seguimiento != tabla_previa:
        print('¡La tabla de seguimiento ha sido actualizada!')
        # Enviar una alerta o realizar cualquier acción necesaria
        tabla_previa = tabla_seguimiento
        toaster.show_toast("Nueva actualización!", f"{ historia } en { planta }", duration=250)
