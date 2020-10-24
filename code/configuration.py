#!/usr/bin/env python
#-*- encoding: utf-8 -*-

import os, sys
app_root = os.path.dirname(__file__)
if app_root.strip()!='':
    sys.path.append(app_root)
    os.chdir(app_root)

from config import *
web.config.debug = False

from modules import mdb

if __name__ == '__main__':
    if len(sys.argv)==2 and sys.argv[1] in ('--binding-on', '--binding-off'):
        mdb.initDBConnection()
        if sys.argv[1]=='--binding-on':
            mdb.set_syskey('ENABLE_BIND', 1)
            print('Binding turned on')
        elif sys.argv[1]=='--binding-off':
            mdb.set_syskey('ENABLE_BIND', 0)
            print('Binding turned off')
    else:
        print('''
Usage:
  python configuration.py option
Options:
  --binding-on
  --binding-ff
''')

