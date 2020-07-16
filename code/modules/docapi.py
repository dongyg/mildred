#!/usr/bin/env python
#-*- encoding: utf-8 -*-

from config import *

from . import mdocker, mcompose, mdb

urls_rest = (
    '',             'CtrlIndex',
    '/',            'CtrlIndex',
    # '/whoami',                       'CtrlWhoAmI',
    '/server/bind',                  'CtrlServerBind',
    '/server/swbind',                'CtrlServerSwitchBind',
    '/server/vscode',                'CtrlServerVsCode',
    '/server/devices',               'CtrlServerDevices',
    '/server/info',                  'CtrlServerInfo',
    '/server/swstat',                'CtrlServerStatSwitch',
    '/server/stat/second',           'CtrlServerStatSecond',
    '/server/stat/minute',           'CtrlServerStatMinute',
    '/server/alerts',                'CtrlServerAlertList',
    '/message/new',                  'CtrlMessageNews',
    '/message/unrdcnt',              'CtrlMessageUnread',
    '/message/all',                  'CtrlMessageList',
    '/message/(.+)/',                'CtrlMessageInfo',
    '/containers',                   'CtrlContainerList',
    '/container/(.+)/',              'CtrlContainerGet',
    '/container/(.+)/start',         'CtrlContainerStart',
    '/container/(.+)/restart',       'CtrlContainerRestart',
    '/container/(.+)/stop',          'CtrlContainerStop',
    '/container/(.+)/remove',        'CtrlContainerRemove',
    '/container/(.+)/inspect',       'CtrlContainerInspect',
    '/container/(.+)/logs/tail',     'CtrlContainerLogsTail',
    '/container/(.+)/logs/forward',  'CtrlContainerLogsForward',
    '/container/(.+)/logs/backward', 'CtrlContainerLogsBackward',
    '/container/(.+)/stat/second',   'CtrlContainerStatSecond',
    '/container/(.+)/stat/minute',   'CtrlContainerStatMinute',
    '/images',                       'CtrlImageList',
    '/image/(.+)/remove',            'CtrlImageRemove',
    '/reachable/port',               'CtrlReachablePort',
    '/reachable/http',               'CtrlReachableHttp',
    '/composes',                     'CtrlComposeList',
    '/composes/files',               'CtrlFileList',
    '/composes/(.+)/',               'CtrlComposeInfo',
    # '/compose/test',                 'CtrlComposeTest',
    '/compose/(.+)/up',              'CtrlComposeUp',
    '/compose/(.+)/down',            'CtrlComposeDown',
    '/compose/(.+)/start',           'CtrlComposeStart',
    '/compose/(.+)/restart',         'CtrlComposeRestart',
    '/compose/(.+)/stop',            'CtrlComposeStop',
    '/compose/(.+)/remove',          'CtrlComposeRemove',
    '/static/.*',                    'CtrlStaticFiles',
    '/.*',          'CtrlViewController',
)
app_api = web.application(urls_rest, locals())

class CtrlIndex:
    def GET(self):
        if mdb.get_syskey('ENABLE_BIND', '0') == '1':
            ipaddress = web.ctx.env.get('HTTP_X_REAL_IP') or web.ctx.env.get('REMOTE_ADDR') or 'Unknown'
            protocol = web.ctx.get('protocol') or 'http'
            realhome = web.ctx.get('realhome') or 'unknown'
            if web.ctx.env.get('HTTP_X_FORWARDED_PROTO') and web.ctx.env['HTTP_X_FORWARDED_PROTO']!=protocol:
                realhome = realhome.replace(protocol, web.ctx.env['HTTP_X_FORWARDED_PROTO'])
            req_uri = web.ctx.env.get('REQUEST_URI', 'path')
            dockinfo = mdocker.get_dkinfo()
            dcmpinfo = mcompose.compose_info()
            render = variant.get_render('index')
            import qrcode, base64
            from io import BytesIO
            img = qrcode.make(realhome)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            pagedata = {
                "realhome": realhome,
                "req_uri": req_uri,
                "dkok": "errmsg" not in dockinfo,
                "dcok": dcmpinfo[0].find('not found')<0,
                "stok": os.path.isdir('../storage'),
                "ssok": not realhome.startswith('https://') and not web.validipaddr(web.ctx.get('host')), # http://domainname couldn't be access from ios
                "imgd": img_str,
            }
            return render(pagedata)
        else:
            return web.notfound()

class CtrlWhoAmI:
    def GET(self):
        ipaddress = web.ctx.env.get('HTTP_X_REAL_IP') or web.ctx.env.get('REMOTE_ADDR') or 'Unknown'
        protocol = web.ctx.get('protocol') or 'http'
        realhome = web.ctx.get('realhome') or 'unknown'
        if web.ctx.env.get('HTTP_X_FORWARDED_PROTO') and web.ctx.env['HTTP_X_FORWARDED_PROTO']!=protocol:
            realhome = realhome.replace(protocol, web.ctx.env['HTTP_X_FORWARDED_PROTO'])
        req_uri = web.ctx.env.get('REQUEST_URI', 'path')
        retval = "Hello %s, you are accessing %s%s"%(ipaddress, realhome, req_uri)
        return retval

class SignatureHooker:
    def checkSignature(self):
        web.header("Content-Type", "text/json")
        params = web.input(lid='')
        retsig = mdb.check_signature(params.lid, params.get('timestamp'), params.get('nonce'), params.get('sig'))
        if 'errmsg' in retsig and retsig['errmsg']:
            web.header('DOCKER_ERRMSG', retsig['errmsg'])
            raise web.notfound('{}')

################################################################################
class CtrlServerBind:
    def GET(self):
        if mdb.get_syskey('ENABLE_BIND', '0') != '1':
            return formator.json_string({'errmsg': 'Binding disabled'})
        params = web.input(lid='')
        web.header("Content-Type", "text/json")
        dkinfo = mdocker.get_dkinfo()
        if 'errmsg' in dkinfo:
            return formator.json_string(dkinfo)
        if not params.lid:
            return formator.json_string({'errmsg': 'Invalid request'})
        otp = utils.getRandomNumber(6)
        variant.binding_otps = {params.lid: otp}
        utils.outMessage('Binding OTP: %s'%otp)
        return formator.json_string({})
    def POST(self):
        if mdb.get_syskey('ENABLE_BIND', '0') != '1':
            return formator.json_string({'errmsg': 'Binding disabled'})
        params = web.input(lid='', otp='', did='', dname='', pexp=None, rurl='')
        web.header("Content-Type", "text/json")
        dkinfo = mdocker.get_dkinfo()
        if 'errmsg' in dkinfo:
            return formator.json_string(dkinfo)
        if not params.lid:
            return formator.json_string({'errmsg': 'Invalid request'})
        if not params.otp:
            return formator.json_string({'errmsg': 'Invalid request'})
        if variant.binding_otps.get(params.lid) != params.otp:
            return formator.json_string({'errmsg': 'Invalid OTP'})
        realhome = params.rurl
        sid = dkinfo.get('ID', realhome)
        sname = dkinfo.get('Name', realhome)
        osname = dkinfo.get('OperatingSystem', 'Unknown')
        retval = mdb.set_license_bind(params.lid, params.did, params.dname, sid, sname, realhome, params.pexp, osname)
        variant.binding_otps.pop(params.lid,None)
        return formator.json_string(retval)
    def PUT(self):
        SignatureHooker.checkSignature(self)
        params = web.input(lid='', rurl='')
        if not params.lid:
            return formator.json_string({'errmsg': 'Invalid request'})
        realhome = params.rurl
        retval = mdb.relocate_license(params.lid, realhome)
        return formator.json_string(retval)
    def DELETE(self):
        SignatureHooker.checkSignature(self)
        params = web.input(lid='')
        if not params.lid:
            return formator.json_string({'errmsg': 'Invalid request'})
        retval = mdb.del_license_bind(params.lid)
        return formator.json_string(retval)

class CtrlServerSwitchBind:
    def POST(self):
        SignatureHooker.checkSignature(self)
        mdb.set_syskey('ENABLE_BIND', 1)
        return formator.json_string({})
    def DELETE(self):
        SignatureHooker.checkSignature(self)
        mdb.set_syskey('ENABLE_BIND', 0)
        return formator.json_string({})

class CtrlServerVsCode:
    def POST(self):
        SignatureHooker.checkSignature(self)
        params = web.input(lid='', url='')
        retval = mdb.set_codeserver(params.lid, params.url)
        return formator.json_string(retval)

class CtrlServerDevices:
    def GET(self):
        SignatureHooker.checkSignature(self)
        retval = mdb.list_devices()
        return formator.json_string({'body':retval})
    def DELETE(self):
        SignatureHooker.checkSignature(self)
        params = web.input(did='',dlid='')
        retval = mdb.del_device(params.did, params.dlid)
        return formator.json_string(retval)

class CtrlServerInfo(SignatureHooker):
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input(lid='')
        realhome = web.ctx.get('realhome', 'host')
        retval = mdocker.get_dkinfo()
        if "errmsg" in retval:
            return formator.json_string(retval)
        else:
            sname, cserver, surl = mdb.get_serverinfo(params.lid)
            retval['URI'] = surl or realhome
            retval['Name'] = sname or retval['Name']
            retval['code_server'] = cserver
            retval['msg_counts'] = mdb.count_message1(params.lid)
            retval['msg_news'] = mdb.list_newmsg(params.lid, '--sys--')
            retval['enable_bind'] = mdb.get_syskey('ENABLE_BIND', '0')
            retval['enable_stat'] = variant.enable_stat
            retval['inside_container'] = variant.inside_container
            retval['licinfo'] = {
                'push_expire': variant.pubkeys.get(params.lid,{}).get('push_expire')
            }
            return formator.json_string({'body':retval})
    def POST(self):
        SignatureHooker.checkSignature(self)
        params = web.input(lid='', sname='')
        retval = mdb.set_servername(params.lid, params.sname)
        return formator.json_string(retval)
    def PUT(self):
        SignatureHooker.checkSignature(self)
        params = web.input(lid='', pexp='')
        retval = mdb.set_pushexpire(params.lid, params.pexp)
        return formator.json_string(retval)

class CtrlServerStatSwitch:
    def POST(self):
        SignatureHooker.checkSignature(self)
        mdb.set_syskey('ENABLE_STAT', 1)
        variant['enable_stat'] = '1'
        variant.deamon_thread = threading.Thread(target=mdocker.stat_daemon, args=(), daemon=True)
        variant.deamon_thread.start()
        return formator.json_string({})
    def DELETE(self):
        SignatureHooker.checkSignature(self)
        mdb.set_syskey('ENABLE_STAT', 0)
        variant['enable_stat'] = '0'
        return formator.json_string({})

class CtrlServerStatSecond:
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input(ts='')
        cnames = [x['name'] for x in mdocker.list_container()]
        if params.ts and formator.isFloat(params.ts):
            ff = lambda val : [x for x in val if x[0]>float(params.ts)]
            retval = dict([(cname,ff(val)) for cname, val in variant.secdata.items() if cname in cnames])
        else:
            retval = dict([(cname,val) for cname, val in variant.secdata.items() if cname in cnames])
        return formator.json_string({'body':retval})

class CtrlServerStatMinute:
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input(ts='')
        cnames = [x['name'] for x in mdocker.list_container()]
        if params.ts and formator.isFloat(params.ts):
            ff = lambda val : [x for x in val if x[0]>float(params.ts)]
            retval = dict([(cname,ff(val)) for cname, val in variant.mindata.items() if cname in cnames])
        else:
            retval = dict([(cname,val) for cname, val in variant.mindata.items() if cname in cnames])
        return formator.json_string({'body':retval})

################################################################################
class CtrlServerAlertList:
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input(lid='', cname='')
        retdat = mdb.list_alert(params.lid, params.cname)
        return formator.json_string({'body':retdat})
    def POST(self):
        SignatureHooker.checkSignature(self)
        params = web.input(alid='',lid='',cname='',altype='',alstr='',alval='',enabled='',push='',level='')
        retval = mdb.set_alert(params)
        return formator.json_string(retval)
    def DELETE(self):
        SignatureHooker.checkSignature(self)
        params = web.input(alid='')
        retval = mdb.del_alert(params.alid)
        return formator.json_string(retval)

class CtrlMessageNews:
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input(lid='', cname='')
        retdat = mdb.list_newmsg(params.lid, params.cname)
        retcnt = mdb.count_message1(params.lid, params.cname).get(params.cname, [0,0])[1]
        return formator.json_string({'body':retdat, 'unread':retcnt})

class CtrlMessageUnread:
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input(lid='', cname='')
        retcnt = mdb.count_message1(params.lid, params.cname).get(params.cname, [0,0])
        return formator.json_string({'body':retcnt})

class CtrlMessageList:
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input(lid='', cname='', alid='', skey='', isrd='', offset=0, limit=20)
        retdat = mdb.list_message(params.lid, params.cname, params.alid, params.skey, params.isrd, params.offset, params.limit)
        total = 0
        if params.offset == 0 or params.offset == '0':
            total = mdb.count_message2(params.lid, params.cname, params.skey)
        return formator.json_string({'body':retdat, 'total':total})
    def POST(self):
        SignatureHooker.checkSignature(self)
        params = web.input(mid='', isread=2)
        retval = mdb.set_message(params.mid, params.isread)
        return formator.json_string(retval)
    def DELETE(self):
        SignatureHooker.checkSignature(self)
        params = web.input(mid='', mids='')
        retval = {}
        if params.mid:
            retval = mdb.del_message(params.mid)
        if params.mids:
            for mid in params.mids.split(","):
                retval = mdb.del_message(mid)
        return formator.json_string(retval)

class CtrlMessageInfo:
    def GET(self, msgid):
        SignatureHooker.checkSignature(self)
        params = web.input()
        retval = mdb.get_message(msgid)
        return formator.json_string({'body':retval})

################################################################################
class CtrlContainerList:
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input(lid='')
        retval = mdocker.list_container()
        return formator.json_string({'body':retval, 'msg_counts':mdb.count_message1(params.lid)})

class CtrlContainerGet:
    def GET(self, cname):
        SignatureHooker.checkSignature(self)
        retval = mdocker.get_container(cname)
        return formator.json_string(retval)

class CtrlContainerStart:
    def POST(self, cname):
        SignatureHooker.checkSignature(self)
        retval = mdocker.start_container(cname)
        return formator.json_string(retval)

class CtrlContainerRestart:
    def POST(self, cname):
        SignatureHooker.checkSignature(self)
        retval = mdocker.restart_container(cname)
        return formator.json_string(retval)

class CtrlContainerStop:
    def POST(self, cname):
        SignatureHooker.checkSignature(self)
        retval = mdocker.stop_container(cname)
        return formator.json_string(retval)

class CtrlContainerRemove:
    def DELETE(self, cname):
        SignatureHooker.checkSignature(self)
        retval = mdocker.remove_container(cname)
        return formator.json_string(retval)

class CtrlContainerInspect:
    def GET(self, cname):
        SignatureHooker.checkSignature(self)
        retval = mdocker.inspect_container(cname)
        return formator.json_string(retval)

class CtrlContainerLogsTail:
    def GET(self, cname):
        SignatureHooker.checkSignature(self)
        params = web.input(l='')
        lines = int(params.l) if params.l.isdigit() else ('all' if params.l=='all' else K_LOGS_DEFAULT_LINES)
        retval = mdocker.logs_container_tail(cname, lines=lines)
        return formator.json_string(retval)

class CtrlContainerLogsForward:
    def GET(self, cname):
        SignatureHooker.checkSignature(self)
        params = web.input(l='', ts='')
        lines = int(params.l) if params.l.isdigit() else ('all' if params.l=='all' else K_LOGS_DEFAULT_LINES)
        retval = mdocker.logs_container_forward(cname, lines=lines, tsbase=params.ts)
        return formator.json_string(retval)

class CtrlContainerLogsBackward:
    def GET(self, cname):
        SignatureHooker.checkSignature(self)
        params = web.input(l='', ts='')
        lines = int(params.l) if params.l.isdigit() else ('all' if params.l=='all' else K_LOGS_DEFAULT_LINES)
        retval = mdocker.logs_container_backward(cname, lines=lines, tsbase=params.ts)
        return formator.json_string(retval)

class CtrlContainerStatSecond:
    def GET(self, cname):
        SignatureHooker.checkSignature(self)
        params = web.input(ts='')
        if cname not in variant.secdata:
            return '{"errmsg": "No such container: %s"}'%cname
        if params.ts and formator.isFloat(params.ts):
            retval = [x for x in variant.secdata[cname] if x[0]>float(params.ts)]
        else:
            retval = variant.secdata[cname]
        return formator.json_string({'body':retval, 'length':len(retval)})

class CtrlContainerStatMinute:
    def GET(self, cname):
        SignatureHooker.checkSignature(self)
        params = web.input(ts='')
        if cname not in variant.mindata:
            return '{"errmsg": "No such container: %s"}'%cname
        if params.ts and params.ts != "0" and params.ts != "0.0" and formator.isFloat(params.ts):
            retval = [x for x in variant.mindata[cname] if x[0]>float(params.ts)]
        else:
            retval = variant.mindata[cname]
        return formator.json_string({'body':retval, 'length':len(retval)})

class CtrlContainerStatHistory:
    def GET(self, cname):
        #TODO:
        SignatureHooker.checkSignature(self)
        params = web.input(ts1='', ts2='')

################################################################################
class CtrlImageList:
    def GET(self):
        SignatureHooker.checkSignature(self)
        retval = mdocker.list_image()
        return formator.json_string({'body':retval})

class CtrlImageRemove:
    def DELETE(self, iname):
        SignatureHooker.checkSignature(self)
        retval = mdocker.remove_image(iname)
        return formator.json_string(retval)


################################################################################
class CtrlReachablePort:
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input(tg='')
        retval = {}
        if params.tg:
            ipport = params.tg.split(":")
            if len(ipport) == 2 and web.validipaddr(ipport[0]) and web.validipport(ipport[1]):
                if not utils.check_port(ipport[0], ipport[1]):
                    retval = {'errmsg': 'Unreachable'}
            else:
                retval = {'errmsg': 'Invalid ip:port'}
        else:
            retval = {'errmsg': 'Invalid ip:port'}
        return formator.json_string(retval)

class CtrlReachableHttp:
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input(tg='')
        retval = {}
        if params.tg or not params.tg.lower().startswith(('http:','https:')):
            retdat = utils.check_http(params.tg)
            if retdat[0]>=400:
                retval = {'errmsg': retdat[1]}
        else:
            retval = {'errmsg': 'Invalid URL'}
        return formator.json_string(retval)


################################################################################
class CtrlComposeList:
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input()
        cmpsinfo = mcompose.compose_info()
        retval = {'body': mdb.list_compose(), 'cmpsver':cmpsinfo[0], 'cmpstip':cmpsinfo[1]}
        return formator.json_string(retval)
    def POST(self):
        SignatureHooker.checkSignature(self)
        params = web.input(fpath='')
        retval = mdb.add_compose(params.fpath)
        return formator.json_string(retval)
    def PUT(self):
        SignatureHooker.checkSignature(self)
        params = web.input(cmpsid='', alias='')
        retval = mdb.set_compose(params.cmpsid, params.alias)
        return formator.json_string(retval)
    def DELETE(self):
        SignatureHooker.checkSignature(self)
        params = web.input(cmpsid='')
        retval = mdb.del_compose(params.cmpsid)
        return formator.json_string(retval)

class CtrlFileList:
    def GET(self):
        SignatureHooker.checkSignature(self)
        params = web.input(folder='')
        retval = mcompose.list_files(params.folder)
        return formator.json_string({'body': retval})

class CtrlComposeInfo:
    def GET(self, cmpsid):
        SignatureHooker.checkSignature(self)
        params = web.input()
        cpobj = mdb.get_compose(cmpsid)
        if not cpobj:
            return formator.json_string({'errmsg': 'No such compose file'})
        fpath = utils.prefixStorageDir(cpobj.FILEPATH) if not os.path.isabs(cpobj.FILEPATH) else cpobj.FILEPATH
        cpobj['images'] = mcompose.compose_images(fpath)
        cpobj['containers'] = mcompose.compose_containers(fpath)
        return formator.json_string({'body': cpobj})

########################################
def needAddChunkedHeader():
    server = web.ctx.environ.get('SERVER_SOFTWARE', '')
    port1 = web.ctx.environ.get('SERVER_PORT', '')
    host = web.ctx.environ.get('HTTP_HOST', '').split(':')
    port2 = host[1] if len(host)==2 else '80'
    if server.find('Cheroot')>=0:
        if variant.inside_container:
            cobj = get_selfcontainer()
            if port2 in [x['PublicPort'] for x in cobj['Ports'] if 'PublicPort' in x]:
                return True
            return False
        else:
            return port1 == port2
    else:
        return False

class CtrlComposeTest:
    def GET(self):
        # SignatureHooker.checkSignature(self)
        # These headers make it work in browsers
        # web.header('Content-type','text/html')
        web.header('Content-type','application/octet-stream')
        if needAddChunkedHeader():
            # Only set this header if you're running web.py's builtin http server.
            web.header('Transfer-Encoding','chunked')
        fi = mcompose.compose_test(100)
        while True:
            try:
                retval = next(fi)
                print(retval)
                yield retval
            except StopIteration:
                break

class CtrlComposeUp:
    def POST(self, cmpsid):
        SignatureHooker.checkSignature(self)
        params = web.input()
        cpobj = mdb.get_compose(cmpsid)
        if not cpobj:
            return 'No such compose file'
        fpath = utils.prefixStorageDir(cpobj.FILEPATH) if not os.path.isabs(cpobj.FILEPATH) else cpobj.FILEPATH
        retval = mcompose.compose_up(fpath)
        web.header('Content-type','application/octet-stream')
        if needAddChunkedHeader():
            web.header('Transfer-Encoding','chunked')
        while True:
            try:
                yield next(retval)
            except StopIteration:
                break

class CtrlComposeDown:
    def POST(self, cmpsid):
        SignatureHooker.checkSignature(self)
        params = web.input()
        cpobj = mdb.get_compose(cmpsid)
        if not cpobj:
            return 'No such compose file'
        fpath = utils.prefixStorageDir(cpobj.FILEPATH) if not os.path.isabs(cpobj.FILEPATH) else cpobj.FILEPATH
        retval = mcompose.compose_down(fpath)
        web.header('Content-type','application/octet-stream')
        if needAddChunkedHeader():
            web.header('Transfer-Encoding','chunked')
        while True:
            try:
                yield next(retval)
            except StopIteration:
                break

class CtrlComposeStart:
    def POST(self, cmpsid):
        SignatureHooker.checkSignature(self)
        params = web.input()
        cpobj = mdb.get_compose(cmpsid)
        if not cpobj:
            return 'No such compose file'
        fpath = utils.prefixStorageDir(cpobj.FILEPATH) if not os.path.isabs(cpobj.FILEPATH) else cpobj.FILEPATH
        retval = mcompose.compose_start(fpath)
        web.header('Content-type','application/octet-stream')
        if needAddChunkedHeader():
            web.header('Transfer-Encoding','chunked')
        while True:
            try:
                yield next(retval)
            except StopIteration:
                break

class CtrlComposeRestart:
    def POST(self, cmpsid):
        SignatureHooker.checkSignature(self)
        cpobj = mdb.get_compose(cmpsid)
        if not cpobj:
            return 'No such compose file'
        fpath = utils.prefixStorageDir(cpobj.FILEPATH) if not os.path.isabs(cpobj.FILEPATH) else cpobj.FILEPATH
        retval = mcompose.compose_restart(fpath)
        web.header('Content-type','application/octet-stream')
        if needAddChunkedHeader():
            web.header('Transfer-Encoding','chunked')
        while True:
            try:
                yield next(retval)
            except StopIteration:
                break

class CtrlComposeStop:
    def POST(self, cmpsid):
        SignatureHooker.checkSignature(self)
        params = web.input()
        cpobj = mdb.get_compose(cmpsid)
        if not cpobj:
            return 'No such compose file'
        fpath = utils.prefixStorageDir(cpobj.FILEPATH) if not os.path.isabs(cpobj.FILEPATH) else cpobj.FILEPATH
        retval = mcompose.compose_stop(fpath)
        web.header('Content-type','application/octet-stream')
        if needAddChunkedHeader():
            web.header('Transfer-Encoding','chunked')
        while True:
            try:
                yield next(retval)
            except StopIteration:
                break

class CtrlComposeRemove:
    def POST(self, cmpsid):
        SignatureHooker.checkSignature(self)
        params = web.input()
        cpobj = mdb.get_compose(cmpsid)
        if not cpobj:
            return 'No such compose file'
        fpath = utils.prefixStorageDir(cpobj.FILEPATH) if not os.path.isabs(cpobj.FILEPATH) else cpobj.FILEPATH
        retval = mcompose.compose_remove(fpath)
        web.header('Content-type','application/octet-stream')
        if needAddChunkedHeader():
            web.header('Transfer-Encoding','chunked')
        while True:
            try:
                yield next(retval)
            except StopIteration:
                break


################################################################################
class CtrlStaticFiles:
    def GET(self):
        inpath = web.ctx.path[1:]
        if not os.path.isfile(inpath):
            raise web.notfound()
        contentTypes = {'.js':'application/javascript','.css':'text/css','.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.gif':'image/gif',
                        '.eot':'', '.svg':'', '.woff':'application/x-font-woff', '.woff2':'application/x-font-woff', '.ttf':'', '.otf':'', '.json':'', '.md':'', '.mdown':''}
        extName = os.path.splitext(inpath)[1].lower()
        if extName not in contentTypes.keys():
            raise web.notfound()
        ctype = contentTypes.get(extName,"application/octet-stream; charset=UTF-8")
        try:
            f = open(inpath, 'rb')
        except IOError:
            raise web.notfound()
        web.header("Content-Type", ctype if ctype else "application/octet-stream; charset=UTF-8")
        fs = os.fstat(f.fileno())
        web.header("Content-Length", str(fs[6]))
        content = f.read()
        f.close()
        return content


################################################################################
class CtrlViewController(object):
    def GET(self):
        web.header("Content-Type", "text/json")
        return formator.json_string({'errmsg': 'API not exists. Please upgrade Mildred Container to the newest version.'})

