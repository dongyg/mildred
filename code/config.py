#!/usr/bin/env python
#-*- encoding: utf-8 -*-

import os, sys, base64, time, traceback, json, random, importlib, hashlib, threading, re
import web
import docker

web.config.debug = False

K_LOGS_DEFAULT_LINES = 20

web.config.vars = web.Storage({
    'option': web.Storage({}),
    'dclient': docker.from_env(),
    'deamon_thread': None,
    'inside_container': bool(os.environ.get('RUNNING_INSIDE_CONTAINER')),
    'enable_stat': '0',
    'binding_otps': {},
    'pubkeys': {},
    'logiers': {},
    'logthds': {},
    'staters': {},
    'mindata': {},
    'secdata': {},
    'alertlg': {},
    'alertcm': {},
    'alertph': {},
})
variant = web.config.vars

from helper import formator, utils, console

render_globals = utils.get_all_functions(formator)
render = web.template.render('views', cache=not web.config.debug, globals=render_globals)

def get_render(inpath, view=render):
    return getattr(view, inpath) or web.notfound

def get_client_ip():
    ipaddress = 'Unknown'
    if not web.ctx.env:
        return ipaddress
    ipaddress = web.ctx.env.get('HTTP_X_FORWARDED_FOR')
    ipaddress = ipaddress.split(',')[0] if ipaddress else ''
    if ipaddress:
        return ipaddress
    ipaddress = web.ctx.env.get('HTTP_X_REAL_IP', web.ctx.env.get('REMOTE_ADDR', 'Unknown'))

web.config.vars['get_render'] = get_render

