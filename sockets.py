#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

def set_listener( entity, data ):
    ''' do something with the update ! '''

myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return flask.redirect('/static/index.html', code=301)

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    while True:
        msg = ws.receive()
        if (msg != None):
            package = json.loads(msg)
            # for each k,v set it to myword
            for k, v in package.items():
                myWorld.set(k, v)
        else:
            break
    return None

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # source https://github.com/abramhindle/WebSocketsExamples/blob/master/broadcaster.py from prof
    client = Client()
    clients.append(client)
    g = gevent.spawn( read_ws, ws, client )    
    print("Subscribing")
    try:
        while True:
            # block here
            msg = client.get()
            print("Got a message!")
            ws.send(msg)
    except Exception as e:# WebSocketError as e:
        print ("WS Error %s" % e)
    finally:
        clients.remove(client)
        gevent.kill(g)
    return None


# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    key_value = flask_post_json().items()
    for key,value in key_value:
        myWorld.update(entity,key,value)
    updated =  flask.jsonify(myWorld.get(entity)) 
    response = flask.make_response(updated)

    return response

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    world = flask.jsonify(myWorld.world())
    response = flask.make_response(world)

    return response

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    entity = flask.jsonify(myWorld.get(entity)) 
    response = flask.make_response(entity)

    return response


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    myWorld.clear()
    world = flask.jsonify(myWorld.world())
    response = flask.make_response(world)
    
    return response


if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
