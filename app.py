#!/usr/bin/python3
from PIL import Image
from multiprocessing.connection import Client
from threading import Thread
import time
from queue import Queue
import os
import datetime
import imageio
from numpy import uint8
import ast

# Cargo configuracion de las camaras desde el archivo
# config_camaras.conf

#Variable boba
A=156

with open('config_camaras_dev.conf', 'r') as file:
    camaras = ast.literal_eval(file.read())

q = Queue(6)


class capturaRpi:
    def __init__(self, img, iso, sp, framerate, camName, crop, timestamp=None):
        self.imagen = img
        self.iso = iso
        self.shutter_speed = sp
        self.framerate = float(framerate)
        self.camName = platform.node()
        self.crop = crop
        self.timestamp = timestamp


class RPCProxy:
    def __init__(self, connection):
        self._connection = connection

    def timeit(f):
        def timed(*a, **kw):
            ti = time.time()
            result = f(*a, **kw)
            tf = time.time()
            print('Tiempo: {}'.format(tf-ti))
            return result
        return timed

    def __getattr__(self, name):
        def do_rpc(*args, **kwargs):
            self._connection.send((name, args, kwargs))
            result = self._connection.recv()
            if isinstance(result, Exception):
                raise result
            return result
        return do_rpc


def timeit(f):
    def timed(*a, **kw):
        ti = time.time()
        result = f(*a, **kw)
        tf = time.time()
        print('Tiempo: {}'.format(tf-ti))
        return result
    return timed


@timeit
def capturarThread(q, cam):
    q.put_nowait(cam.capturar())


def capturarImagenes(q):
    fecha = datetime.datetime.today().strftime('%Y_%m_%d_%H')
    mainDir = 'capturas_{}'.format(fecha)
    if not os.path.exists(mainDir):
        os.makedirs(mainDir)
    hilos = []
    for cam in camaras:
        hilos.append(Thread(target=capturarThread,
                            args=(q, camaras[cam]['cam'])))
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    imgs = []
    while not q.qsize() == 0:
        img = q.get()
        imgs.append(img)
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
        grid_color = [255, 255, 255]
        #grid_color = [0, 0, 0]
        img_enh = img.imagen.copy()
        img_enh[::dx,:,:] = grid_color
        img_enh[:,::dy,:] = grid_color
        img_pil=Image.fromarray(img_enh.astype(uint8))
        img_pil=img_pil.point(lambda i: i*3)
        img_pil.save('{}/ultima_{}.jpg'.format(mainDir, img.camName), quality=80)
        with open('{}/{}/log.txt'.format(mainDir, img.camName), 'a') as file:
            file.write('{};{};{};{};{};{}\n'.format(img.camName,
                                                    img.iso,
                                                    img.shutter_speed,
                                                    img.framerate,
                                                    img.timestamp,
                                                    img.crop))
    return imgs


def initCameras(camaras):
    for cam in camaras:
        camaras[cam]['conn'] = Client(camaras[cam]['url'], authkey=b'peekaboo')
        camaras[cam]['cam'] = RPCProxy(camaras[cam]['conn'])
        camaras[cam]['cam'].set_crop(camaras[cam]['crop'])
        camaras[cam]['cam'].set_date(str(datetime.datetime.today()))
        camaras[cam]['cam'].inicializar(camaras[cam]['iso'], camaras[cam]['shutter_speed'])
    return camaras


initCameras(camaras)

while True:
    try:
        capturarImagenes(q)
    except KeyboardInterrupt:
        break
