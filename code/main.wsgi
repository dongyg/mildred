#!/usr/bin/env python
#-*- encoding: utf-8 -*-


import os, sys, _thread, signal
app_root = os.path.dirname(__file__)
if app_root.strip()!='':
    sys.path.append(app_root)
    os.chdir(app_root)

from config import *
web.config.debug = not variant.inside_container

from modules import docapi, webapp, mdocker, mdb

def sig_handler(signum, frame):
    raise SystemExit()

def main():
    urls = []
    urls.extend([
        '/mildred', docapi.app_api,
        '',         webapp.app_www,
    ])
    app = web.application(urls, globals(), autoreload=False)
    return app

if __name__ == '__main__':
    mdb.initDBConnection()
    signal.signal(signal.SIGTERM, sig_handler)
    app = main()
    if variant.enable_stat == '1':
        variant.deamon_thread = threading.Thread(target=mdocker.stat_daemon, args=(), daemon=True)
        variant.deamon_thread.start()
    if variant.inside_container:
        app.run()
    else:
        _thread.start_new_thread(app.run,())
        console.embed()
    mdocker.stat_closeall()
    print('Bye.')

