#!/usr/bin/python3
from multiprocessing.connection import Listener
from threading import Thread
import picamera.array
import time
import datetime
from PIL import Image
from io import BytesIO
import platform
from subprocess import call

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
                           'set_crop': self.set_crop,
                           'set_date': self.set_date
                           }
        self._cropped = False

    def timeit(f):
        def timed(*a, **kw):
            ti = time.time()
            result = f(*a, **kw)
            tf = time.time()
            print('tiempo: {}'.format(tf-ti))
            return result
        return timed

    def register_function(self, func):
        self._functions[func.__name__] = func

    def handle_connection(self, connection):
        try:
            while True:
                func_name, args, kwargs = connection.recv()
                try:
                    r = self._functions[func_name](*args, **kwargs)
                    connection.send(r)
                except Exception as e:
                    connection.send(e)
        except EOFError:
            pass

    def inicializar(self, iso=100, sp=45000):
        try:
            self.cam = picamera.PiCamera()
            self.cam.resolution = self.cam.MAX_RESOLUTION
            self.cam.iso = iso
            self.cam.framerate = float(1.0/(sp/(10**6)))
            self.cam.shutter_speed = sp
            time.sleep(2)
            self.cam.start_preview()
            self.cam.exposure_mode = 'off'
        except:
            return 'Camara ya inicializada'

    @timeit
    def capturar(self):
        with picamera.array.PiRGBArray(self.cam) as self.stream:
            timestamp = datetime.datetime.today()#.strftime('%Y%m%d%H%M%S')
            self.cam.capture(self.stream, 'rgb')
            if not self._cropped:
                imagen = capturaRpi(self.stream.array[:,:,:], self.cam.iso,
                                    self.cam.shutter_speed, self.cam.framerate, platform.node(),
                                    timestamp=timestamp)
            else:
                im = self.stream.array[self.xi:self.xf,self.yi:self.yf,:]
                imagen = capturaRpi(im[:,:,:], self.cam.iso,
                                    self.cam.shutter_speed, self.cam.framerate, platform.node(),
                                    crop=(self.xi,self.xf,self.yi,self.yf),timestamp=timestamp)
            return imagen

    def set_iso(self, iso):
        self.cam.iso = iso
        return 'Iso seteado en: {}'.format(self.cam.iso)

    def get_iso(self):
        return self.cam.iso

    def set_shutter_speed(self, sp):
        self.cam.shutter_speed = sp
        self.cam.framerate = float(1.0/(sp/(10**6)))
        return 'Shutter speed: {}'.format(self.cam.shutter_speed)

    def get_shutter_speed(self):
        return self.cam.shutter_speed

    def close(self):
        self.cam.close()

    def set_crop(self, crop):
        assert len(crop)==4
        self._cropped = True
        self.xi = crop[0]
        self.xf = crop[1]
        self.yi = crop[2]
        self.yf = crop[3]
        print('Crop -> X[{}:{}] Y[{}:{}]'.format(self.xi,self.xf,self.yi,self.yf))
        return 'Crop -> X[{}:{}] Y[{}:{}]'.format(self.xi,self.xf,self.yi,self.yf)

    def set_date(self, date):
        call(["date", "-s", date])
        return 'Date set to {}'.format(date)

def rpc_server(handler, address, authkey):
    sock = Listener(address, authkey=authkey)
    while True:
        client = sock.accept()
        t = Thread(target=handler.handle_connection, args=(client,))
        t.deamon = True
        t.start()

handler = RPCHandler()

rpc_server(handler, ('0.0.0.0', 5000), authkey=b'peekaboo')
