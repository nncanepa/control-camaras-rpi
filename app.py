#!/usr/bin/python3
from PIL import Image
from multiprocessing.connection import Client
import multiprocessing as mp
import time
import os
import datetime
import imageio
from numpy import uint8
import ast
from concurrent import futures
from matplotlib import pyplot as plt
from queue import Queue
import numpy as np

# Cargo configuracion de las camaras desde el archivo
# config_camaras.conf

with open('config_camaras_dev.conf', 'r') as file:
    camaras = ast.literal_eval(file.read())


class capturaRpi:
    '''
    Clase para las capturas de imagenes del acelerador.
    Guarda el array en si, mas los parametros de captura y
    nombre de camara.
    '''
    def __init__(self, img, iso, sp, framerate, camName, crop=None, timestamp=None):
        self.imagen = img
        self.iso = iso
        self.shutter_speed = sp
        self.framerate = float(framerate)
        self.camName = camName 
        self.crop = crop
        self.timestamp = timestamp


class RPCProxy:
    '''
    Clase para ejecutar de manera remota comandos en las
    Raspberry Pi como si las tuvieramos localmente conectadas.
    Se inicializa con la conexion a cada camara. Luego recibe
    las funciones que se quieren ejecutar junto con sus parametros
    y los envia a las Raspberry Pi.
    En caso de una Exception en la RPi, nos la devuelve como tal y hace
    un raise de la excepcion.
    Para ver la contraparte de esta funcion referirse a cameraServer.py
    que es el script que se corre en las placas.
    '''
    def __init__(self, connection):
        self._connection = connection

    def __getattr__(self, name):
        def do_rpc(*args, **kwargs):
            self._connection.send((name, args, kwargs))
            result = self._connection.recv()
            if isinstance(result, Exception):
                raise result
            return result
        return do_rpc


def capturarImagenes():
    '''
    Funcion que incia captura en hilos separados de todas las camaras
    listadas en la configuracion (ver config_camaras.conf).
    Genera un pool de hilos disponibles y espera que todas devuelvan la
    imagen a medida que van terminando la captura.
    Cuando terminan de capturar se guardan las imagenes en una carpeta para
    cada camara, junto con una imagen "mejorada" para la visualizacion en
    la carpeta base.
    '''
    imgs=[]
    fecha = datetime.datetime.today().strftime('%Y_%m_%d_%H')
    mainDir = 'capturas_{}'.format(fecha)
    if not os.path.exists(mainDir):
        os.makedirs(mainDir)
    executor = futures.ThreadPoolExecutor(max_workers=2)
    wait_for =[executor.submit(camaras[cam]['cam'].capturar, ) for cam in camaras]
    for f in futures.as_completed(wait_for):
        imgs.append(f.result())
    executor.shutdown()
    imgsCrudas = imgs.copy()
    imgsEnhanced = []
    while imgs:
        img = imgs.pop()
        if not os.path.exists('{}/{}'.format(mainDir, img.camName)):
            os.makedirs('{}/{}'.format(mainDir, img.camName))
        imageio.imwrite('{}/{}/{}__{}_{}.jpg'.format(mainDir,
                                                     img.camName,
                                                     img.timestamp.strftime('%Y%m%d%H%M%S'),
                                                     img.iso,
                                                     img.shutter_speed),
                        img.imagen.astype(uint8),
                        quality=90)
        dx, dy =36, 36
        #grid_color = [255, 255, 255]
        grid_color = [0, 0, 0]
        img_enh = img.imagen.copy()
        img_enh[::dx,:,:] = grid_color
        img_enh[:,::dy,:] = grid_color
        img_pil=Image.fromarray(img_enh.astype(uint8))
        img_pil=img_pil.point(lambda i: i*3)
        imgsEnhanced.append([img_pil, img.camName])
        img_pil.save('{}/ultima_{}.jpg'.format(mainDir, img.camName), quality=80)
        with open('{}/{}/log.txt'.format(mainDir, img.camName), 'a') as file:
            file.write('{};{};{};{};{};{}\n'.format(img.camName,
                                                    img.iso,
                                                    img.shutter_speed,
                                                    img.framerate,
                                                    img.timestamp,
                                                    img.crop))
    return imgsCrudas, imgsEnhanced



def initCameras(camaras):
    '''
    Funcion que inicializa la conexion con todas las camaras listadas
    en config_camaras.conf, y luego setea los parametros de captura
    junto con la fecha actual de la maquina de control.
    '''
    for cam in camaras:
        camaras[cam]['conn'] = Client(camaras[cam]['url'], authkey=b'peekaboo')
        camaras[cam]['cam'] = RPCProxy(camaras[cam]['conn'])
        camaras[cam]['cam'].set_crop(camaras[cam]['crop'])
        camaras[cam]['cam'].set_date(str(datetime.datetime.today()))
        camaras[cam]['cam'].inicializar(camaras[cam]['iso'], camaras[cam]['shutter_speed'])
    return camaras

def graficarCrudo(q):
    '''
    Va graficando en un proceso separado las imagenes
    que capturadas. Las imagenes las recibe a traves
    de una cola multiprocessing.Queue()
    '''
    plt.ion()
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1)
    fig.tight_layout()
    while True:
        try:
            imgs = q.get_nowait()
        except:
            try:
                ax1.set_title(imgs[0].camName)
                ax1.imshow(imgs[0].imagen)
                ax2.set_title(imgs[1].camName)
                ax2.imshow(imgs[1].imagen)
                plt.pause(0.001)
            except:
                pass

def graficarEnhanced(q):
    '''
    Va graficando en un proceso separado las imagenes
    que capturadas, retocadas para su mejor visualizacion
    durante la operación. Las imagenes las recibe a traves
    de una cola multiprocessing.Queue()
    '''
    plt.ion()
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1)
    fig.tight_layout()
    while True:
        try:
            imgs = q.get_nowait()
        except:
            try:
                ax1.set_title(imgs[1][1])
                ax1.imshow(np.array(imgs[1][0])[...,:3])
                ax2.set_title(imgs[0][1])
                ax2.imshow(np.array(imgs[0][0])[...,:3])
                plt.pause(0.001)
            except:
                pass


if __name__ == '__main__':
    initCameras(camaras)
    mqCrudas = mp.Queue(4)
    mqEnhanced = mp.Queue(4)
    p1 = mp.Process(target=graficarCrudo, args=(mqCrudas, ), daemon=True)
    p2 = mp.Process(target=graficarEnhanced, args=(mqEnhanced, ), daemon=True)
    p1.start()
    p2.start()
    while True:
        try:
            imgsCrudas, imgsEnhanced = capturarImagenes()
            mqCrudas.put(imgsCrudas)
            mqEnhanced.put(imgsEnhanced)
        except KeyboardInterrupt:
            p1.terminate()
            p2.terminate()
            break