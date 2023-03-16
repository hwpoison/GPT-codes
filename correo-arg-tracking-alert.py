import time

import requests
from bs4 import BeautifulSoup
from win10toast import ToastNotifier

url = "<URL>"

# Configurar la instancia de ToastNotifier
toaster = ToastNotifier()

previous_content = None

while True:
        print("Checking...")
        # Obtener la página web
        response = requests.get(url)
        html = response.content

        # Analizar el HTML de la página
        soup = BeautifulSoup(html, 'html.parser')

        # Buscar la tabla de seguimiento
        tracking_table = soup.find('div', {'id': 'resultado'}).find('table')

        # Obtener todos los elementos <tr> dentro de la tabla
        fields = tracking_table.find_all('tr')

        # Seleccionar el último elemento de la lista de fields
        last_field = fields[1]

        # Obtener el contenido de cada celda de la última fila
        fields = last_field.find_all('td')
        date = fields[0].text.strip()
        location = fields[1].text.strip()
        history = fields[2].text.strip()
        status = fields[3].text.strip()

        # Comparar la tabla previa con la nueva
        if previous_content is None:
            previous_content = tracking_table
        elif tracking_table != previous_content:
            print('¡La tabla de seguimiento ha sido actualizada!')
            # Enviar una alerta o realizar cualquier acción necesaria
            previous_content = tracking_table
            toaster.show_toast("Nueva actualización!", f"{ history } en { location }", duration=500)
        else:
            print("Nothing new for the moment...")
        # Esperar 30 segundos antes de volver a revisar la página
        time.sleep(30)
