#!/usr/bin/env python
from __future__ import print_function

import os
import sys
import signal
import xmlrpclib
import pprint
import syslog
import socket
import time
import json
import traceback
import yaml
import requests

from enum import Enum
from cmd import Cmd

class ConnectionLost(Exception): pass
class JsonRpcError(Exception): pass

class JsonRpcProxy: # https://pypi.python.org/pypi/JsonRpc-Netstrings/0.2-dev
    def __init__(self, addr, timeout = 5, version="2.0"):
        if addr.find(':'):
            (self.host,self.port) = addr.split(':')
            self.port = int(self.port)
        else:
            self.host = addr
            self.port = 7080
        self._version = version
        self._timeout = timeout
        self.connect()

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self._timeout)
        self.socket.connect((self.host, self.port))
        self._incrementor = 1

    def close(self):
        self.socket.close()

    def call_remote(self, method, params={}, retries=0):
        self._incrementor += 1
        jsonrpc_request = {"jsonrpc": self._version, "id": self._incrementor, "method": method, "params": params}
        string = json.dumps(jsonrpc_request)
        jsonrpc = str(len(string)) + ":" + string + ","

        try:
            #print 'Sending message: %s' % jsonrpc
            self.socket.send(jsonrpc)
            byte_length = self.socket.recv(1, socket.MSG_WAITALL)

            if not byte_length:
                raise ConnectionLost()

            while byte_length[-1] != ':':
                #print 'Receiving byte length (next char)...'
                byte_length += self.socket.recv(1)

            byte_length = int(byte_length[:-1])

            #print 'Got byte length:', byte_length

            response_string = ''
            while len(response_string) < byte_length:
                #print 'Receiving bytedata bytes...'
                response_string += str(self.socket.recv(byte_length-len(response_string)))
            response = json.loads(response_string)
        # except ConnectionLost:
        #     self.connect()
        #     return self.call_remote(method, params)
        except Exception, e:
            traceback_string = traceback.format_exc()
            syslog.syslog('{}'.format(traceback_string))
            raise e

        if not response['id'] == self._incrementor:
            raise JsonRpcError('Bad sequence ID ({}, expected {})'.format(response['id'], self._incrementor))

        last_char = self.socket.recv(1)

        if last_char != ',':
            raise JsonRpcError("Expected a comma as a jsonrpc terminator!")

        if 'result' in response:
            return response['result']
        elif 'error' in response:
            raise JsonRpcError(response['error'])
        else:
            raise JsonRpcError('Unknow error. Response: {}'.format(response))

if len(sys.argv) < 2:
	print("usage: %s host:port\n\texample %s 127.0.0.1:7080" % (sys.argv[0],sys.argv[0]))
	raise SystemExit

def f(j, depth, args, desc):
	print('    '*depth + ' '.join(args[:-1])+" (%s)"%desc)
	data = j.call_remote('yeti.'+args[0],args[1:])
	if not isinstance(data, list):
		return
	for d in data:
		f(j,depth+1,args[:-1]+[d[0],'_list'],d[1])

j = JsonRpcProxy(sys.argv[1],3000)
f(j,0,['_list'],'root')

