#!/usr/bin/python3
from multiprocessing.connection import Listener
from threading import Thread
#import picamera.array
import time
import datetime
import numpy as np
from PIL import Image

class falsaCamara(object):
    def __init__(self, iso=100, sp=50000, framerate=0.1, resolution=(3280, 2464)):
        self.framerate = framerate
        self.iso = iso
        self.resolution = resolution
        self.shutter_speed = sp
        self.MAX_RESOLUTION = (3280, 2464)
    
    def start_preview(self):
        pass

    def close(self):
        pass

    
class capturaRpi:
    def __init__(self, img, iso, sp, framerate, camName, crop=None, timestamp=None):
        self.imagen = img
        self.iso = iso
        self.shutter_speed = sp
        self.framerate = float(framerate)
        self.camName = camName 
        self.crop = crop
        self.timestamp = timestamp


class RPCHandler:
    def __init__(self):
        self._functions = {'inicializar': self.inicializar,
                           'capturar': self.capturar,
                           'set_iso': self.set_iso,
                           'set_shutter_speed': self.set_shutter_speed,
                           'close': self.close,
                           'get_iso': self.get_iso,
                           'get_shutter_speed': self.get_shutter_speed,
                           'set_date': self.set_date,
                           'set_crop': self.set_crop}

    def register_function(self, func):
        self._functions[func.__name__] = func

    def handle_connection(self, connection):
        try:
            while True:
                func_name, args, kwargs = connection.recv()
                print(func_name, args, kwargs)
                try:
                    r = self._functions[func_name](*args, **kwargs)
                    connection.send(r)
                except Exception as e:
                    connection.send(e)
        except EOFError:
            pass

    def inicializar(self, iso=800, sp=1500000):
        try:
            self.cam = falsaCamara()
            self.cam.resolution = self.cam.MAX_RESOLUTION
            self.cam.iso = iso
            self.cam.framerate = float(1.0/(sp/(10**6)))
            self.cam.shutter_speed = sp
            time.sleep(2)
            self.cam.start_preview()
            self.cam.exposure_mode = 'off'
        except:
            return 'Camara ya inicializada'

    def capturar(self):
        time.sleep(2)
        timestamp = datetime.datetime.today()
        imagen = capturaRpi(np.random.randint(0,255,size=(500,1000,3)), self.cam.iso,
                            self.cam.shutter_speed, self.cam.framerate, 'camara2', crop=(self.xi,self.xf,self.yi,self.yf),
                            timestamp=timestamp)
        return imagen

    def set_iso(self, iso):
        self.cam.iso = iso

    def get_iso(self):
        return self.cam.iso

    def set_shutter_speed(self, sp):
        self.cam.shutter_speed = sp

    def get_shutter_speed(self):
        return self.cam.shutter_speed

    def close(self):
        self.cam.close()

    def set_crop(self, crop):
        self.xi=crop[0]
        self.xf=crop[1]
        self.yi=crop[2]
        self.yf=crop[3]
        print(crop)
    
    def set_date(self, date):
        return 'Date set'

def rpc_server(handler, address, authkey):
    sock = Listener(address, authkey=authkey)
    while True:
        client = sock.accept()
        t = Thread(target=handler.handle_connection, args=(client,))
        t.deamon = True
        t.start()

handler = RPCHandler()

rpc_server(handler, ('localhost', 5000), authkey=b'peekaboo')