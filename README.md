# Control Camaras-rpi

Control de camaras RaspberryPi v2.1 por RPC con python.

El script cameraServer.py corre en las placas RaspberryPi, conviene configurar la placa para que inicie el script en el booteo.

En el archivo config_camaras.conf se guarda en un diccionario todos los datos y parametros de las camaras instaladas.

La aplicacion app.py se corre desde cualquier PC en la misma red de las camaras y captura imágenes de manera continua al tiempo que
las va graficando, por un lado la version en crudo de la captura y una version "mejorada" para visualizar haces tenues.