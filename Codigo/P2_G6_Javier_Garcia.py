__author__ = 'Javier Garcia Rubio'

import _thread
import threading
import time
import asyncio

import redis as redis
from bson import ObjectId
from bson.json_util import dumps
from pymongo import MongoClient
from geopy.geocoders import Nominatim
from geojson import Point
from math import sin, cos, sqrt, atan2, radians
import json
import aioredis
import random


def getCityGeoJSON(adress):
    """ Devuelve las coordenadas de una direcciion a partir de un str de la direccion
    Argumentos:
        adress (str) -- Direccion
    Return:
        (str) -- GeoJSON
    """

    geolocator = Nominatim(user_agent="P2_G6_Javier_Garcia_Sergio_Esteban.py")
    location = geolocator.geocode(adress, timeout=20)
    # TODO
    # Devolver GeoJSON de tipo punto con la latitud y longitud almacenadas
    # en las variables location.latitude y location.longitude
    location_point = Point((location.longitude, location.latitude))

    return location_point


class ModelCursor(object):
    def __init__(self, model_class, command_cursor):
        self.model_class = model_class
        self.command_cursor = command_cursor

    def next(self):
        return self.model_class(**self.command_cursor.next())

    @property
    def alive(self):
        return self.command_cursor.alive


class Model(object):
    required_vars = []
    admissible_vars = []
    db = None
    redis_db = None
    query_update = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

        for key in self.required_vars:
            if key not in kwargs:
                pass
                # raise Exception("Error")

    def __str__(self):
        string = ""
        for key, value in self.__dict__.items():
            string += (key + ": " + str(value) + "\n")
        return string

    # IMPLEMENTAR EK GET BYID

    def save(self):
        # TODO
        if hasattr(self, '_id'):
            for key in vars(self):
                if key in self.modified_atributes:
                    self.db.update_one({'_id': self._id}, {'$set': {key: getattr(self, key)}})
                    # self.redis_db.set(str(self._id), json_data)
                    # self.redis_db.expire(str(self._id), 86400)

        else:
            new_tuple = {}
            for key in vars(self):
                if key in self.modified_atributes:
                    new_tuple.update({key: getattr(self, key)})

            self.db.insert_one(new_tuple)
        name_for_match = self.query_update.get("nombre")
        # AÑADIDO PARA EL ERROR 1
        if name_for_match == None:
            name_for_match = self.query_update.get("producto")
            query = [{'$match': {'producto': name_for_match}}]
        else:
            query = [{'$match': {'nombre': name_for_match}}]
        self.getById(query)
        self.modified_atributes.clear

    def update(self, **kwargs):
        # TODO
        self.modified_atributes = []
        # print(kwargs)
        self.query_update = kwargs
        for key, value in kwargs.items():
            if key is 'direcciones_de_facturacion':
                for item in value:
                    item['direccion']['coordinates'] = getCityGeoJSON(item['direccion']['nombre'])

            if key is 'direcciones_de_envio':
                for item in value:
                    item['direccion']['coordinates'] = getCityGeoJSON(item['direccion']['nombre'])

            if key not in self.required_vars:
                if key not in self.admissible_vars:
                    raise Exception("Error")

            self.modified_atributes.append(key)
            setattr(self, key, value)

    @classmethod
    def init_class(cls, db, redis_db, vars_path="model_name.vars"):
        """ Inicializa las variables de clase en la inicializacion del sistema.
        Argumentos:
            db (MongoClient) -- Conexion a la base de datos.
            vars_path (str) -- ruta al archivo con la definicion de variables
            del modelo.
        """
        cls.db = db
        # REDIS
        cls.redis_db = redis_db
        cls.redis_db.config_set('maxmemory-policy', 'volatile-ttl')
        cls.redis_db.config_set('maxmemory', '150mb')

        # ADM, REQ VAR
        with open(vars_path) as file:
            cls.required_vars = file.readline().split()
            cls.admissible_vars = file.readline().split()

    @classmethod
    def getById(cls, id):
        # REDIS
        # id es la query
        print("ID: ", id)
        print("From redis")
        data = cls.redis_db.get(str(id))
        print(data)
        if data is None:
            print("From mongo")
            data = ModelCursor(cls, cls.db.aggregate(id))

            # si data es none
            if data is None:
                return None

            # Update redis
            else:
                print("Update redis")
                x = str(data.next())
                # print(x)
                json_data = json.dumps(x.replace("\n", ","))
                # print(json_data)
                # json_data = dumps(list(data.next()), indent=2)
                cls.redis_db.set(str(id), json_data)
        # AÑADIDO PARA SOLUCIONAR EL ERROR 2
        cls.redis_db.expire(str(id), 86400)
        return data


class Cliente(Model):
    @classmethod
    def query(cls, query):
        """ Devuelve un cursor de modelos
        """
        model_cursor = ModelCursor(cls, cls.db.aggregate(query))
        return model_cursor


class Compra(Model):
    @classmethod
    def query(cls, query):
        """ Devuelve un cursor de modelos
        """
        model_cursor = ModelCursor(cls, cls.db.aggregate(query))
        return model_cursor


class Producto(Model):
    @classmethod
    def query(cls, query):
        """ Devuelve un cursor de modelos
        """
        model_cursor = ModelCursor(cls, cls.db.aggregate(query))
        return model_cursor


class Proveedor(Model):
    @classmethod
    def query(cls, query):
        """ Devuelve un cursor de modelos
        """
        cursor = cls.db.aggregate(query)
        cursor_custom = ModelCursor(Proveedor, cursor)
        return cursor_custom

# Compras
# Q1: Listado de todas las compras de un cliente
Q1 = [{'$match': {'cliente.nombre': 'Javier'}},
      {'$project':
           {'producto.nombre': 1,
            'cliente.nombre': 1,
            'direccion_de_envio': 1,
            'fecha_de_compra': 1,
            'precio_de_compra': 1}}]

# Proveedores
Q2 = [{'$lookup': {'from': 'productos', 'localField': 'codigo', 'foreignField': 'proveedor.codigo', 'as': 'prod'}},
      {'$unwind': '$codigo'},
      {'$match': {'prod.nombre': 'iphone 8'}},
      {'$project':
           {'_id': '$_id',
            'nombre': '$nombre',
            'direcciones_almacenes': '$direcciones_almacenes',
            'codigo': '$codigo'}}]
# Productos
# project producto 0 para excluir
Q3 = [{'$lookup': {'from': 'compras', 'localField': 'nombre', 'foreignField': 'producto.nombre', 'as': 'productos'}},
      {'$unwind': '$productos'},
      {'$match': {'productos.cliente.nombre': 'Javier'}},
      {'$project': {'productos': 0}},
      {'$group':
           {'_id': '$_id',
            'nombre': {'$first': '$nombre'},
            'proveedor': {'$first': '$proveedor.nombre'},
            'precio_sin_iva': {'$first': '$precio_sin_iva'},
            'descuento_por_rango_de_fechas': {'$first': '$descuento_por_rango_de_fechas'},
            'dimensiones': {'$first': '$dimensiones'}, 'peso': {'$first': '$peso'}}}]

# Compras
# FUNCIONA EN CONSOLA DE MONGO AQUI NO
# Q4 = [{'$match': {'$and': [{'fecha_de_compra': '2018-02-02T00:00:00.000Z'},
#                            {'cliente.nombre': 'Javier'}]}},
#       {'$project': {'fecha_de_compra': 1,
#                     'cliente.nombre': 1,
#                     'peso_total': {'$sum': '$producto.peso'},
#                     'volumen_total': {'$sum': {'$multiply': ['$producto.dimensiones.Altura',
#                                                              '$producto.dimensiones.Anchura',
#                                                              '$producto.dimensiones.Profundidad']}}}},
#       {'$group': {'_id': "null",
#                   'peso_total': {'$sum': '$peso_total'},
#                   'volumen_total': {'$sum': '$volumen_total'},
#                   'numero_compras': {'$sum': 1}}}]

Q4 = [{'$match':
           {'$and': [{'fecha_de_compra': '2018-02-02T00:00:00.000Z'}, {'cliente.nombre': 'Javier'}]}},
      {'$project':
           {'fecha_de_compra': 1,
            'cliente.nombre': 1,
            'peso_total': {'$sum': '$producto.peso'}
               , 'volumen_total': {'$sum': {'$multiply': ['$producto.dimensiones.Altura'
               , '$producto.dimensiones.Anchura',
                                                          '$producto.dimensiones.Profundidad']}}}},
      {'$group':
           {'_id': "$_id",
            'producto': {'$first': '$producto.nombre'},
            'cliente': {'$first': '$cliente.nombre'},
            'precio_de_compra': {'$first': '$producto.precio_de_compra'},
            'fecha_de_compra': {'$first': '$producto.fecha_de_compra'},
            'direccion_de_envio': {'$first': '$cliente.direccion_de_envio'},
            'peso_total': {'$sum': '$peso_total'},
            'volumen_total': {'$sum': '$volumen_total'},
            'numero_compras': {'$sum': 1}}}]


Q5 = []

# Compras
# Funciona en mongo shell

Q6 = [{'$group': {'_id': '$producto.proveedores_almacen.nombre',
                  'count': {'$sum': 1},
                  'volumen_facturacion': {'$sum': {'$sum': ['$producto.precio_con_iva', '$producto.coste_de_envio']}}}},
      {'$lookup': {'from': 'proveedores', 'localField': '_id', 'foreignField': 'direcciones_almacenes.direccion.nombre',
                   'as': 'proveedor'}},
      {'$unwind': '$proveedor'},
      {'$group': {'_id': '$proveedor',
                  'volumen_facturacion': {'$sum': '$volumen_facturacion'}}},
      {'$sort': {'volumen_facturacion': -1}},
      {'$limit': 3}]

Q6 = [{'$group':
           {'_id': '$producto.proveedores_almacen.nombre',
            'count': {'$sum': 1},
            'volumen_facturacion':
                {'$sum':
                     {'$sum': ['$producto.precio_con_iva',
                               '$producto.coste_de_envio']}}}},
      {'$lookup': {'from': 'proveedores',
                   'localField': '_id',
                   'foreignField': 'direcciones_almacenes.direccion.nombre',
                   'as': 'proveedor'}},
      {'$unwind': '$proveedor'},
      {'$group': {'_id': '$proveedor',
                  'volumen_facturacion': {'$sum': '$volumen_facturacion'},
                  'producto': {'$first': '$producto.nombre'},
                  'cliente': {'$first': '$cliente.nombre'},
                  'precio_de_compra': {'$first': '$producto.precio_de_compra'},
                  'fecha_de_compra': {'$first': '$fecha_de_compra'},
                  'direccion_de_envio': {'$first': '$direccion_de_envio'}}},
      {'$sort': {'volumen_facturacion': -1}},
      {'$limit': 3}]

# proveedores
# hacer esto antes
# db.proveedores.createIndex({'direcciones_almacenes.direccion.coordinates':'2dsphere'})
Q7 = [{'$geoNear': {'near': {'type': 'Point',
                             'coordinates': [-3.7, 40, 41]},
                    'spherical': 1,
                    'distanceField': 'distancia_diferencia',
                    'maxDistance': 100000}},
      {'$sort': {'distancia_diferencia': 1}}]

# compra
# hacer esto antes
# db.compras.createIndex({'direccion_de_envio.coordinates':'2dsphere'})
Q8 = [{'$match': {'direccion_de_envio.coordinates': {'$geoWithin': {'$geometry'
                                                                    : {'type': 'Polygon',
                                                                       'coordinates': [[[-3.67202335, 40.4097376],
                                                                                        [-3.67246794310811, 40.4108392],
                                                                                        [-3.6742479, 40.4094157],
                                                                                        [-3.67202335,
                                                                                         40.4097376]]]}}}}}]



def main_thread(redis_db, ids, prio):
    while True:
        print("main")
        # threading.Thread(target=empaquetar(redis_db, ids, prio)).start()
        pack = redis_db.blpop(keys=["Compra"], timeout=0)
        id = pack[1].split("|")[0]
        prio = pack[1].split("|")[1]
        print(id)
        print(prio)
        # threading.Thread(target=empaquetar(redis_db, ids, prio)).start()
        if pack is not None:
            threading.Thread(target=worker(redis_db), name=id+1).start()


# def empaquetar(redis_db, pack):
#     redis_db.rpush(pack[0], pack[1])

def empaquetar(redis_db, id, prio):
    print("pack")
    push = id+"|"+str(prio)
    redis_db.rpush("Compra", push)


def worker(redis_db):
    fin_pack = False
    threads = []
    print("worker")
    while not fin_pack:
        pack = redis_db.blpop(keys=["Compra"], timeout=60)
        print(pack[0])
        id = pack[1].split("|")[0]
        prio = pack[1].split("|")[1]
        print(id)
        print(prio)
        if pack is not None:
            threading.Thread(target=worker(redis_db), name=id + 1).start()
            print("Empaquetando...")
            newThread = threading.Thread(target=crearHilo(id, prio))
            threads.append(newThread)
            newThread.start()

            print("Empaquetado")
        else:
            fin_pack = True


def crearHilo(ids, prio):
    print("Empàquetando para usuario con id: " + str(ids) + "\n con prioridad " + str(prio))


if __name__ == '__main__':
    # TODO
    database_json = "Database1.json"
    client = MongoClient()

    db = client.practica
    redis_db = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    with open(database_json, 'r') as insertItems:
        model_data = json.loads(insertItems.read())

    # db['compras'].drop()
    # for item in model_data["compras"]:
    #     item['direccion_de_envio']['coordinates'] = getCityGeoJSON(item['direccion_de_envio']['nombre'])
    #     db['compras'].insert_one(item)
    #
    # db['clientes'].drop()
    # for item in model_data["clientes"]:
    #     for value in item['direcciones_de_facturacion']:
    #         value['direccion']['coordinates'] = getCityGeoJSON(value['direccion']['nombre'])
    #
    #     for value in item['direcciones_de_envio']:
    #         value['direccion']['coordinates'] = getCityGeoJSON(value['direccion']['nombre'])
    #     db['clientes'].insert_one(item)
    #
    # db['productos'].drop()
    # for item in model_data["productos"]:
    #     item['proveedores_almacen']['coordinates'] = getCityGeoJSON(item['proveedores_almacen']['nombre'])
    #     db['productos'].insert_one(item)
    #
    # db['proveedores'].drop()
    # for item in model_data["proveedores"]:
    #     for value in item['direcciones_almacenes']:
    #         value['direccion']['coordinates'] = getCityGeoJSON(value['direccion']['nombre'])
    #     db['proveedores'].insert_one(item)

    Compra.init_class(db['compras'], redis_db, "CompraVariables.txt")
    Cliente.init_class(db['clientes'], redis_db, "ClienteVariables.txt")
    Producto.init_class(db['productos'], redis_db, "ProductoVariables.txt")
    Proveedor.init_class(db['proveedores'], redis_db, "ProveedorVariables.txt")

    # TEST DE MEMORY CACHE
    # redis_test = Compra.getById(Q1)
    # print(redis_test)
    # Pack.init_class(redis_db)

    #######################################################################
    # Proveedor.update(Proveedor, nombre='Pedro', direcciones_almacenes=[{"direccion":
    #     {
    #         "nombre": "calle de Tribaldos 40,Madrid",
    #         "coordinates": [23, 12]
    #     }
    # }], codigo='d333')
    # Proveedor.save(Proveedor)
    #######################################################################
    # TEST EMPAQUETADO
    query_javi_id = [{"$match": {"nombre": "Javier"}}, {"$group": {"_id": "$_id"}}]
    query_sergio_id = [{"$match": {"nombre": "Sergio"}}, {"$group": {"_id": "$_id"}}]
    query_pablo_id = [{"$match": {"nombre": "Pablo"}}, {"$group": {"_id": "$_id"}}]

    cursor = Cliente.query(query_sergio_id)
    sergio_id = str(cursor.next()).split("_id: ")[1].replace("\n", "")

    cursor = Cliente.query(query_pablo_id)
    pablo_id = str(cursor.next()).split("_id: ")[1].replace("\n", "")

    cursor = Cliente.query(query_javi_id)
    javi_id = str(cursor.next()).split("_id: ")[1].replace("\n", "")

    print("hilo")
    t = []
    d = threading.Thread(target=main_thread, args=(redis_db, javi_id, 1))
    # d.setDaemon(True)
    # threading.Thread(target=empaquetar(redis_db, ids, prio)).start()
    thread_pack = threading.Thread(target=empaquetar, args=(redis_db, javi_id, 1))
    thread_pack_2 = threading.Thread(target=empaquetar, args=(redis_db, pablo_id, 2))
    thread_pack_3 = threading.Thread(target=empaquetar, args=(redis_db, sergio_id, 1))

    t.append(d)

    t.append(thread_pack)
    t.append(thread_pack_2)
    t.append(thread_pack_3)
    t[0].start()
    t[1].start()
    t[3].start()
    t[2].start()
