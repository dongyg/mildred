#!/usr/bin/env python
#-*- encoding: utf-8 -*-

from config import *
from . import mdb, mdocker

dclient = variant.dclient

################################################################################
def callShell(cmd):
    import subprocess,traceback,platform
    try:
        p = subprocess.Popen(args=cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (stdoutput,erroutput) = p.communicate()
        retval = stdoutput
    except Exception as e:
        traceback.print_exc()
        retval = ''
    if platform.system()=='Windows':
        retval = unicode(retval, 'gbk')
    return retval.strip().decode('utf8')

def execShell(cmd):
    from subprocess import check_output
    out = check_output(cmd.split(' '), universal_newlines=True)

def iterateShellCall(cmd):
    import subprocess, io
    proc = subprocess.Popen(args=cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):
        yield line

def iterateTest(count):
    for x in range(1,count):
        yield "%s"%x
        time.sleep(0.5)

################################################################################
def escape_ansi1(value):
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', value)

def escape_ansi2(line):
    import re
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)

def escape_ansi3(somebytesvalue):
    ansi_escape_8bit = re.compile(
        br'(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])'
    )
    return ansi_escape_8bit.sub(b'', somebytesvalue)

################################################################################
def get_mac_address():
    import uuid
    mac = uuid.UUID(int = uuid.getnode()).hex[-12:]
    return ":".join([mac[e:e+2] for e in range(0,11,2)])

def get_selfcontainer():
    macadr = get_mac_address()
    for cobj in dclient.api.containers():
        cmac = ''
        if cobj['HostConfig']['NetworkMode'] in cobj['NetworkSettings']['Networks']:
            cmac = cobj['NetworkSettings']['Networks'][cobj['HostConfig']['NetworkMode']]['MacAddress']
        elif 'bridge' in cobj['NetworkSettings']['Networks']:
            cmac = cobj['NetworkSettings']['Networks']['bridge']['MacAddress']
        if cmac and cmac==macadr:
            return cobj
    return {}

def list_files(folder):
    import platform
    retval = []
    if variant.inside_container and not folder:
        cobj = get_selfcontainer()
        for item in cobj.get('Mounts',[]):
            n = item['Destination']
            if not n.endswith('docker.sock') and (platform.system().lower()!='windows' and not n.startswith('.')):
                if os.path.isdir(n):
                    retval.append([n,'d'])
                elif os.path.isfile(n):
                    retval.append([n,'f'])
        retval.sort()
        return retval
    elif not os.path.isabs(folder) or folder=='':
        folder = utils.prefixStorageDir(folder)
    for n in os.listdir(folder):
        if not n.endswith('docker.sock') and (platform.system().lower()!='windows' and not n.startswith('.')):
            if os.path.isdir(os.path.join(folder,n)):
                retval.append((n, 'd'))
            elif os.path.isfile(os.path.join(folder,n)) and n.lower().endswith(('.yaml','.yml')):
                retval.append((n, 'f'))
    return retval

COMPOSE_HINT = '''docker-compose is running in a Mildred container. docker-compose up could fail in some cases because it's in a container.\n
* Please pay attention to the configuration of docker-compose.yml, eg: volumes.'''

def compose_info():
    version = callShell('docker-compose version')
    version = version.split(',')[0].replace('docker-compose version','').strip()
    return [version, COMPOSE_HINT if variant.inside_container else '']

def compose_images(fname):
    retval = []
    if not os.path.isfile(fname): return retval
    retdat = callShell('docker-compose -f %s --no-ansi images -q'%fname)
    iids = [y for x in retdat.split('\r\n') for y in x.split('\n')]
    try:
        retdic = mdocker.tree_image()
        for imgid in iids:
            iobj = retdic.get(imgid)
            if not iobj: iobj = retdic.get('sha256:'+imgid)
            if iobj:
                retval.append(iobj)
    except Exception as e:
        pass
    return retval

def compose_containers(fname):
    retval = []
    if not os.path.isfile(fname): return retval
    retdat = callShell('docker-compose -f %s --no-ansi ps -q'%fname)
    cids = [y for x in retdat.split('\r\n') for y in x.split('\n')]
    try:
        retval = [mdocker.dict_container(x) for x in dclient.api.containers(all=True) if x["Id"] in cids]
    except Exception as e:
        pass
    return retval

########################################
def compose_test(count):
    fi = iterateTest(count)
    return fi

def compose_up(fname):
    retval = iterateShellCall('docker-compose -f %s --no-ansi up -d'%fname)
    return retval

def compose_down(fname):
    retval = iterateShellCall('docker-compose -f %s --no-ansi down'%fname)
    return retval

def compose_start(fname):
    retval = iterateShellCall('docker-compose -f %s --no-ansi start'%fname)
    return retval

def compose_stop(fname):
    retval = iterateShellCall('docker-compose -f %s --no-ansi stop'%fname)
    return retval

def compose_restart(fname):
    retval = iterateShellCall('docker-compose -f %s --no-ansi restart'%fname)
    return retval

def compose_remove(fname):
    retval = iterateShellCall('docker-compose -f %s --no-ansi rm -f'%fname)
    return retval

