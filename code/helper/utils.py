#!/usr/bin/env python
#-*- encoding: utf-8 -*-

import sys, json, types, random, traceback, os, re, hashlib
from datetime import datetime, date, timedelta
import time

def get_all_functions(module):
    functions = {}
    for f in [module.__dict__.get(a) for a in dir(module) if isinstance(module.__dict__.get(a), types.FunctionType)]:
        functions[f.__name__] = f
    return functions

def getRandomString(size):
    import string
    return ''.join(random.choice(string.ascii_letters+string.digits) for i in range(size))

def getRandomNumber(size):
    import string
    return ''.join(random.choice(string.digits) for i in range(size))

def base64ToBase64url(base64):
    # '+' -> '-'
    # '/' -> '_'
    # '=' -> ''
    return base64.replace('+','-').replace('/','_').replace('=','')

def base64urlToBase64(base64url):
    # '-' -> '+'
    # '_' -> '/'
    # append '='
    retval = base64url.replace("-", "+").replace("_", "/")
    if len(retval)%4 != 0:
        retval = retval + '='*(4-len(retval)%4)
    return retval

def outMessage(msg, end='\n'):
    sys.stdout.write(msg+end)
    sys.stdout.flush()

def get_sha1(string1):
    return hashlib.sha1(string1.encode('utf8')).hexdigest()

def get_md5(string1):
    return hashlib.md5(string1.encode('utf8')).hexdigest()

def copy_dict(sd, keys=[]):
    import copy
    if not keys:
        return copy.copy(sd)
    else:
        return dict([(key, val) for key, val in sd.items() if key in keys])

def check_port(address, port, timeout=5):
    if not isinstance(port, int):
        if not str(port).isdigit():
            return False
        port = int(port)
    import socket
    socket.setdefaulttimeout(timeout or 5)
    s = socket.socket()
    try:
        s.connect((address,port))
        return True
    except Exception as e:
        return False
    finally:
        s.close

def check_http(url, timeout=15):
    import urllib
    import urllib.parse
    import urllib.request
    import ssl
    try:
        if url.lower().startswith('https'):
            context = ssl._create_unverified_context()
            resp = urllib.request.urlopen(url, context=context)
        else:
            resp = urllib.request.urlopen(url)
        return resp.status, resp.reason
    except Exception as e:
        return 555, str(e)

def prefixStorageDir(folder):
    if not os.path.isdir('../storage'):
        os.mkdir('../storage')
    if folder.startswith('/'):
        folder = '../storage' + folder
    else:
        folder = os.path.join('../storage', folder)
    return folder

################################################################################
def test():
    print('test.utils')

