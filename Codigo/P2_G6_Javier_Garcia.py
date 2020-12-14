__author__ = 'Javier Garcia Rubio'

import _thread
import threading
import time

import redis as redis
from bson import ObjectId
from bson.json_util import dumps
from pymongo import MongoClient
from geopy.geocoders import Nominatim
from geojson import Point
from math import sin, cos, sqrt, atan2, radians
import json


def getCityGeoJSON(adress):
    """ Devuelve las coordenadas de una direcciion a partir de un str de la direccion
    Argumentos:
        adress (str) -- Direccion
    Return:
        (str) -- GeoJSON
    """

    geolocator = Nominatim(user_agent="P2_G6_Javier_Garcia.py")
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

    def save(self):
        # TODO
        if hasattr(self, '_id'):
            for key in vars(self):
                if key in self.modified_atributes:
                    self.db.update_one({'_id': self._id}, {'$set': {key: getattr(self, key)}})
        else:
            new_tuple = {}
            for key in vars(self):
                if key in self.modified_atributes:
                    new_tuple.update({key: getattr(self, key)})

            self.db.insert_one(new_tuple)

        self.modified_atributes.clear

    def update(self, **kwargs):
        # TODO
        self.modified_atributes = []
        print(kwargs)
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

        #ADM, REQ VAR
        with open(vars_path) as file:
            cls.required_vars = file.readline().split()
            cls.admissible_vars = file.readline().split()

    @classmethod
    def getById(cls, id):
        # REDIS
        #id es la query
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


class Pack(object):
    def __init__(self, **kwargs):
        pass

    @classmethod
    def init_class(cls, redis_db):
        # Conexion con bases de datos
        cls.redis_db = redis_db

    @classmethod
    def postPack(cls, service, userid, cont):
        if service != 1:
            userid = userid + str(cont)
            pipeline.set("compra", userid)
            pipeline.expire("compra", 60)
        else:
            pipeline.set("compra", userid)


    @classmethod
    def execPack(cls):
        return pipeline.execute()


# Define a function for the thread
def print_thread(threadName, delay, service, id):
    count = 0
    while count < 5:
        time.sleep(delay)
        count += 1
        print(threadName +"\nNumero: " + str(count) + "\nSercicio " + ("Principal\n" if service == 1 else "No Principal\n"))
        # TEST EMPAQUETADO
        Pack.postPack(2, id, count)
    print(Pack.execPack())




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

# NO SE
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

if __name__ == '__main__':
    # TODO
    database_json = "Database1.json"
    client = MongoClient()

    db = client.practica
    redis_db = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    pipeline = redis_db.pipeline()

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

    # TODO: si pongo db.compras da error no se porque

    Compra.init_class(db['compras'],redis_db, "CompraVariables.txt")
    Cliente.init_class(db['clientes'], redis_db, "ClienteVariables.txt")
    Producto.init_class(db['productos'], redis_db, "ProductoVariables.txt")
    Proveedor.init_class(db['proveedores'], redis_db, "ProveedorVariables.txt")

    # TEST DE MEMORY CACHE
    # redis_test = Compra.getById(Q1)
    # print(redis_test)
    # Pack.init_class(redis_db)

    # TEST EMPAQUETADO
    query_javi_id = [{"$match":{"nombre":"Javier"}},{"$group":{"_id":"$_id"}}]
    query_sergio_id = [{"$match":{"nombre":"Sergio"}},{"$group":{"_id":"$_id"}}]
    query_pablo_id = [{"$match":{"nombre":"Pablo"}},{"$group":{"_id":"$_id"}}]

    cursor = Cliente.query(query_javi_id)
    javi_id = str(cursor.next()).split("_id: ")[1].replace("\n", "")

    cursor = Cliente.query(query_sergio_id)
    sergio_id = str(cursor.next()).split("_id: ")[1].replace("\n", "")

    cursor = Cliente.query(query_pablo_id)
    pablo_id = str(cursor.next()).split("_id: ")[1].replace("\n", "")



    # CREAR 3 HILOS
    t1 = threading.Thread(target=print_thread, args=("Compra Javier", 2, 1, javi_id))
    t2 = threading.Thread(target=print_thread, args=("Compra Sergio", 4, 2, sergio_id))
    t3 = threading.Thread(target=print_thread, args=("Compra Pablo", 4, 2, pablo_id))

    t1.start()
    t2.start()
    t3.start()

    t1.join()
    t2.join()
    t3.join()
    # _thread.start_new_thread(print_thread, ("Compra Javier", 2, 1, javi_id))
    # _thread.start_new_thread(print_thread, ("Compra Sergio", 4, 2, sergio_id))
    # _thread.start_new_thread(print_thread, ("Compra Pablo", 4, 2, pablo_id))


    # cursorClient = Compra.query(Q1)
    # cursorClient = Proveedor.query(Q2)
    # cursorClient = Producto.query(Q3)
    # cursorClient = Compra.query([{'$limit': 10}]) # test
    # cursorClient = Compra.query(Q4)
    # cursorClient = Proveedor.query(Q5) # no la tengo
    # cursorClient = Compra.query(Q6)
    # cursorClient = Proveedor.query(Q7)
    # cursorClient = Compra.query(Q8)
    # print(Q1)
    # cursorClient = Proveedor.query([{'$match':{'nombre':'Pedro'}}])
    # print(cursorClient.next())

    # TODO: Esto es para ver que el update funciona

    # Proveedor.update(Proveedor, nombre='Pedro', direcciones_almacenes=[{"direccion":
    #     {
    #         "nombre": "calle de Tribaldos 40,Madrid",
    #         "coordinates": [23, 12]
    #     }
    # }], codigo='d333')
    # Proveedor.save(Proveedor)
    # Producto.update(Producto, nombre='iphone 10', proveedor='hola', precio_sin_iva=10,
    #                 descuento_por_rango_de_fechas='hola', dimensiones='hola', peso='hola',
    #                 precio_con_iva=15, coste_de_envio=5, proveedores_almacen={
    #         "nombre": "calle de Tribaldos 40,Madrid",
    #         "coordinates": [23, 12]
    #     })
    # Producto.save(Producto)

    # TODO: Esto es para checkear el update
    # cursorClient = Proveedor.query([{'$match':{'nombre':'Pedro'}}])
    # print(cursorClient.next())
    # while cursorClient.alive:
    #     print(cursorClient.next())
