#!/usr/bin/env python
#-*- encoding: utf-8 -*-


from datetime import datetime
from config import *
from . import mdb, apush


dclient = variant.dclient

def get_dkinfo():
    try:
        dclient.ping()
    except Exception as e:
        return {"errmsg": str(e)}
    dkinfo = dclient.info()
    cpu_usage, mem_usage = get_cm_usage()
    retval = {
        'URI': '',
        'ID': utils.get_sha1(dkinfo['ID']),
        'Name': dkinfo['Name'],
        'ProductLicense': dkinfo.get('ProductLicense',''),
        'ServerVersion': dkinfo['ServerVersion'],
        'SystemTime': formator.get_ts_from_utcstr(dkinfo['SystemTime']),
        'NCPU': dkinfo['NCPU'], 'CpuUsage': cpu_usage,
        'MemTotal': dkinfo['MemTotal'], 'MemUsage': mem_usage,
        'OperatingSystem': dkinfo['OperatingSystem'],
        'OSType': dkinfo['OSType'],
        'Images': dkinfo['Images'],
        'Containers': dkinfo['Containers'],
    }
    return retval


def dict_container(cobj):
    if isinstance(cobj, docker.models.containers.Container):
        return {
            'short_id': cobj.short_id,
            'name': cobj.name,
            'image': cobj.attrs['Config']['Image'],
            'status': cobj.status,
            'Created': int(formator.get_ts_from_utcstr(cobj.attrs['Created'])),
            'StartedAt': formator.get_docker_status(cobj.attrs['State']['Running'], cobj.attrs['State']['ExitCode'], cobj.attrs['State']['StartedAt']),
            'ports': ','.join(set([x.split('/')[0] for x in cobj.ports.keys()])),
        }
    elif isinstance(cobj, dict):
        return {
            'short_id': cobj['Id'][:10],
            'name': cobj['Names'][0][1:],
            'image': cobj['Image'],
            'status': cobj['State'],
            'Created': cobj['Created'],
            'StartedAt': cobj['Status'],
            'ports': ','.join(set(['%s'%(x['PublicPort']) for x in cobj['Ports'] if 'PublicPort' in x and 'Type' in x])),
        }
    else:
        return {}

def list_container():
    try:
        retval = [dict_container(x) for x in dclient.api.containers(all=True)]
    except Exception as e:
        retval = []
    return retval

def exists_container(cname):
    try:
        retval = [x for x in dclient.api.containers(all=True) if x['Names'][0][1:]==cname]
    except Exception as e:
        retval = []
    return bool(retval)

def get_container(cname):
    try:
        return dict_container(get_dct_container(cname))
    except Exception as e:
        traceback.print_exc()
        return {"errmsg":e}

def get_dct_container(cname):
    try:
        retval = [x for x in dclient.api.containers(all=True) if x['Names'][0][1:]==cname]
    except Exception as e:
        retval = []
    if not retval:
        raise docker.errors.NotFound("No such container: %s"%cname)
    else:
        return retval[0]

def start_container(cname):
    try:
        dclient.containers.get(cname).start()
        return dict_container(get_dct_container(cname))
    except Exception as e:
        traceback.print_exc()
        return {"errmsg":e}

def restart_container(cname):
    try:
        dclient.containers.get(cname).restart()
        return dict_container(get_dct_container(cname))
    except Exception as e:
        traceback.print_exc()
        return {"errmsg":e}

def stop_container(cname):
    try:
        dclient.containers.get(cname).stop()
        return dict_container(get_dct_container(cname))
    except Exception as e:
        traceback.print_exc()
        return {"errmsg":e}

def remove_container(cname):
    try:
        dclient.api.remove_container(cname, v=True, force=True)
        return {"errmsg":""}
    except Exception as e:
        traceback.print_exc()
        return {"errmsg":e}

def inspect_container(cname):
    try:
        cobj = dclient.containers.get(cname)
        cdct = get_dct_container(cname)
        nets = [(key, val) for key, val in utils.copy_dict(cobj.attrs['NetworkSettings'], ['IPAddress', 'Gateway']).items()]
        if (not nets or not nets[0] or not nets[0][1] ) and cobj.attrs['HostConfig']['NetworkMode'] in cobj.attrs['NetworkSettings']['Networks']:
            nets = [(key, val) for key, val in utils.copy_dict(cobj.attrs['NetworkSettings']['Networks'][ cobj.attrs['HostConfig']['NetworkMode'] ], ['IPAddress', 'Gateway']).items()]
        return {"body":{
            'Cmd': cdct['Command'],
            'Env': [x.split('=') for x in cobj.attrs['Config']['Env']],
            'Mounts': [utils.copy_dict(x, ['Source', 'Destination', 'Mode']) for x in cobj.attrs['Mounts']],
            'Networks': nets,
            'Ports': [(key, '%s:%s'%(val[0]['HostIp'],val[0]['HostPort'])) for key, val in cobj.attrs['NetworkSettings']['Ports'].items() if val],
        }}
    except Exception as e:
        traceback.print_exc()
        return {"errmsg":e}


def logs_container_tail(cname, lines):
    try:
        retdat = dclient.api.logs(cname, tail=lines, timestamps=True).decode().strip()
        retdat = [x3.strip().split(' ', 1) for x1 in retdat.split('\n') for x2 in x1.split('\r') for x3 in x2.split('\r\n') if x3.strip()]
        return {'body':retdat}
    except Exception as e:
        traceback.print_exc()
        return {'errmsg':str(e)}

def logs_container_forward(cname, lines, tsbase):
    from datetime import datetime, timedelta
    try:
        cdct = get_dct_container(cname)
        if len(tsbase)==30 and tsbase.startswith('20') and tsbase.endswith('Z'):
            dtbase = datetime.fromisoformat(tsbase[:26])
        else:
            dtbase = datetime.fromisoformat(tsbase)
        retdat = recurse_forward(cname, cdct['Created'], dtbase, lines, -1, [])
        retdat = [x for x in retdat if x[0]<tsbase]
        retval = retdat[-lines:]
        return {'body':retval}
    except Exception as e:
        traceback.print_exc()
        return {'errmsg':str(e)}

def recurse_forward(cname, createtime, dtbase, lines, movedays, retval=[]):
    from datetime import datetime, timedelta
    dt1, dt2 = dtbase+timedelta(days=movedays), dtbase+timedelta(seconds=1)
    retdat = dclient.api.logs(cname, timestamps=True, since=dt1, until=dt2).decode().strip()
    retdat = [x3.strip().split(' ', 1) for x1 in retdat.split('\n') for x2 in x1.split('\r') for x3 in x2.split('\r\n') if x3.strip()]
    retval = retdat + retval
    if (lines=='all' or len(retval) < int(lines)) and dt2.timestamp() > createtime:
        retval = recurse_forward(cname, createtime, dt1, lines, movedays*2, retval)
    return retval

def logs_container_backward(cname, lines, tsbase):
    from datetime import datetime, timedelta
    try:
        cdct = get_dct_container(cname)
        if len(tsbase)==30 and tsbase.startswith('20') and tsbase.endswith('Z'):
            dtbase = datetime.fromisoformat(tsbase[:26])
        else:
            dtbase = datetime.fromisoformat(tsbase)
        lastdata = logs_container_tail(cname, 1)
        tslast = lastdata['body'][0][0] if lastdata.get('body') else ''
        retdat = recurse_backward(cname, tslast, dtbase, lines, 1, [])
        retdat = [x for x in retdat if x[0]>tsbase]
        retval = retdat[:lines]
        return {'body':retval}
    except Exception as e:
        traceback.print_exc()
        return {'errmsg':str(e)}

def recurse_backward(cname, tslast, dtbase, lines, movedays, retval=[]):
    from datetime import datetime, timedelta
    dt1, dt2 = dtbase, dtbase+timedelta(days=movedays)
    retdat = dclient.api.logs(cname, timestamps=True, since=dt1, until=dt2).decode().strip()
    retdat = [x3.strip().split(' ', 1) for x1 in retdat.split('\n') for x2 in x1.split('\r') for x3 in x2.split('\r\n') if x3.strip()]
    retval = retval + retdat
    if (lines=='all' or len(retval) < int(lines)) and (len(retval)>0 and retval[-1][0]<tslast):
        retval = recurse_backward(cname, tslast, dt2, lines, movedays*2, retval)
    return retval


def avg(l):
    r = [x for x in l if x != None]
    if len(r) == 0:
        return 0
    else:
        return sum(r)/len(r)

def nsum(l):
    r = [x for x in l if x != None]
    return sum(r)

def container_exists_byname(cname):
    return cname in [cobj['Names'][0][1:] for cobj in dclient.api.containers(all=True)]

def get_stat_mindata(ts='0'):
    cnames = [x['name'] for x in list_container()]
    if ts and formator.isFloat(ts):
        ff = lambda val : [x for x in val if x[0]>float(ts)]
        retval = dict([(cname,ff(val)) for cname, val in variant.mindata.items() if cname in cnames])
    else:
        retval = dict([(cname,val) for cname, val in variant.mindata.items() if cname in cnames])
    return retval

def get_cm_usage(cname=''):
    alldata = get_stat_mindata()
    retdat1 = [datas[-1][1] for key, datas in alldata.items() if (key==cname or cname=='') and len(datas)>0 and len(datas[-1])==12]
    retdat2 = [datas[-1][2] for key, datas in alldata.items() if (key==cname or cname=='') and len(datas)>0 and len(datas[-1])==12]
    return sum(retdat1), sum(retdat2)

def get_top6_mindata(ts='0'):
    from functools import cmp_to_key
    alldata = get_stat_mindata(ts)
    top6name = []
    for cname in alldata.keys():
        top6name.append([cname, alldata[cname][-1][2] if len(alldata[cname])>0 and len(alldata[cname][-1])>2 else 0])
    top6name.sort(key=cmp_to_key(lambda a, b: b[1]-a[1]))
    retval = {}
    count = 1
    for cname, fake in top6name:
        retval[cname] = alldata.pop(cname, [])
        count += 1
        if count>=6: break
    timearray = []
    for cname, tmpl in alldata.items():
        timearray.extend([x[0] for x in tmpl])
    timearray = list(set(timearray))
    timearray.sort()
    retval['Others'] = {}
    for cname, tmpl in alldata.items():
        for curritem in tmpl:
            currtime = curritem[0]
            saveitem = retval['Others'].get(currtime)
            if not saveitem:
                retval['Others'][currtime] = curritem
            else:
                retval['Others'][currtime] = [
                    currtime,
                    round(saveitem[1] + curritem[1], 2),
                    saveitem[2] + curritem[2],
                    saveitem[3] + curritem[3],
                    saveitem[4] + curritem[4],
                    saveitem[5] + curritem[5],
                    saveitem[6] + curritem[6],
                    saveitem[7] + curritem[7],
                    saveitem[8] + curritem[8],
                    saveitem[9] + curritem[9],
                    saveitem[10] + curritem[10],
                    saveitem[11] + curritem[11],
                ]
    retval['Others'] = list(retval['Others'].values())
    retval['Others'].sort(key=cmp_to_key(lambda a, b: a[0]-b[0]))
    return retval

def stat_container(cname):
    ster = variant.staters[cname]
    try:
        return next(ster)
    except StopIteration as e:
        traceback.print_exc()
        utils.outMessage(cname)
        if container_exists_byname(cname):
            ster = dclient.api.stats(cname, decode=True)
            variant.staters[cname] = ster
        else:
            variant.staters.pop(cname)
    except docker.errors.NotFound as e:
        traceback.print_exc()
        utils.outMessage(cname)
        variant.staters.pop(cname)
    except Exception as e:
        traceback.print_exc()
        utils.outMessage(cname)
        variant.staters.pop(cname)

def stat_transfer(cname, sdat):
    rdat = None
    if sdat and sdat.get('pids_stats') and sdat.get('cpu_stats'):
        cs = sdat['cpu_stats']
        ds = sdat.get('blkio_stats',{}).get('io_service_bytes_recursive',[])
        ldat = variant.secdata[cname][-1] if variant.secdata[cname] else []
        stime = formator.get_ts_from_utcstr(sdat['read'])
        if stime==0 and ldat:
            stime = ldat[0]+1
        rdat = [
            stime,
            round(cs['cpu_usage']['total_usage']/cs['system_cpu_usage']*100,2),
            sdat['memory_stats']['usage'],
            round(sdat['memory_stats']['usage']/sdat['memory_stats']['limit']*100,2),
            sdat['networks']['eth0']['rx_bytes'] if 'networks' in sdat else 0,
            sdat['networks']['eth0']['tx_bytes'] if 'networks' in sdat else 0,
            None,
            None,
            sum([x['value'] for x in ds if x['op']=='Read']),
            sum([x['value'] for x in ds if x['op']=='Write']),
            None,
            None,
        ]
        if ldat:
            rdat[6] = rdat[4]-ldat[4] if rdat[4]>=ldat[4] else rdat[4]
            rdat[7] = rdat[5]-ldat[5] if rdat[5]>=ldat[5] else rdat[5]
            rdat[10] = rdat[8]-ldat[8] if rdat[8]>=ldat[8] else rdat[8]
            rdat[11] = rdat[9]-ldat[9] if rdat[9]>=ldat[9] else rdat[9]
        variant.secdata[cname].append(rdat)
    return rdat

def stat_carry2minute(cname):
    if not variant.secdata[cname]: return
    st1 = variant.secdata[cname][0][0]
    st2 = variant.secdata[cname][-1][0]
    if st2-st1>60:
        tmpl = []
        cmin = datetime.fromtimestamp(variant.secdata[cname][0][0]).minute
        lmin = cmin
        while len(variant.secdata[cname])>0 and lmin==cmin:
            tmpl.append(variant.secdata[cname].pop(0))
            if len(variant.secdata[cname])>0:
                cmin = datetime.fromtimestamp(variant.secdata[cname][0][0]).minute
        if tmpl:
            tsec = datetime.fromtimestamp(tmpl[0][0]).second
            mdat = [
                tmpl[0][0]-tsec,
                round(avg([x[1] for x in tmpl]),2),
                round(avg([x[2] for x in tmpl])),
                round(avg([x[3] for x in tmpl]),2),
                tmpl[-1][4],
                tmpl[-1][5],
                nsum([x[6] for x in tmpl]),
                nsum([x[7] for x in tmpl]),
                tmpl[-1][8],
                tmpl[-1][9],
                nsum([x[10] for x in tmpl]),
                nsum([x[11] for x in tmpl]),
            ]
            variant.mindata[cname].append(mdat)
            return mdat

def stat_carry2hour(cname):
    if not variant.mindata[cname]: return
    st1 = variant.mindata[cname][0][0]
    st2 = variant.mindata[cname][-1][0]
    if st2-st1>2*3600 or time.time()-st1>2*3600:
        tmpl = []
        hmin = datetime.fromtimestamp(variant.mindata[cname][0][0]).hour
        lmin = hmin
        while len(variant.mindata[cname])>0 and lmin==hmin:
            tmpl.append(variant.mindata[cname].pop(0))
            if len(variant.mindata[cname])>0:
                hmin = datetime.fromtimestamp(variant.mindata[cname][0][0]).hour
        if tmpl:
            tmin = datetime.fromtimestamp(tmpl[0][0]).minute
            tsec = datetime.fromtimestamp(tmpl[0][0]).second + tmin*60
            hdat = [
                tmpl[0][0]-tsec,
                round(avg([x[1] for x in tmpl]),2),
                round(avg([x[2] for x in tmpl])),
                round(avg([x[3] for x in tmpl]),2),
                tmpl[-1][4],
                tmpl[-1][5],
                nsum([x[6] for x in tmpl]),
                nsum([x[7] for x in tmpl]),
                tmpl[-1][8],
                tmpl[-1][9],
                nsum([x[10] for x in tmpl]),
                nsum([x[11] for x in tmpl]),
            ]
            mdb.insert_stats(cname, hdat)

def stat_run_once():
    for cname in list(variant.staters.keys()):
        sdat = stat_container(cname)
        stat_transfer(cname, sdat)
        mdat = stat_carry2minute(cname)
        alert_watch_2345(cname, mdat)
        if mdat and variant.alertcm.get('--sys--'):
            cpusum = sum([v[-1][1] for v in variant.mindata.values() if v])
            memsum = sum([v[-1][2] for v in variant.mindata.values() if v])
            fakemdat = [time.time(), cpusum, memsum]
            alert_watch_2345('--sys--', fakemdat)
        stat_carry2hour(cname)

def stat_init():
    stat_keepiters()
    cnames = variant.staters.keys()
    fpath = utils.prefixStorageDir('stats.cache')
    if os.path.isfile(fpath):
        with open(fpath) as fobj:
            savdat = formator.json_object(fobj.read())
            if 'secdata' in savdat:
                variant.secdata = savdat.get('secdata', {})
                for key in list(variant.secdata.keys()):
                    if key not in cnames:
                        variant.secdata.pop(key)
            else:
                variant.secdata = dict([(x, []) for x in variant.staters.keys()])
            if 'mindata' in savdat:
                variant.mindata = savdat.get('mindata', {})
                for key in list(variant.mindata.keys()):
                    if key not in cnames:
                        variant.mindata.pop(key)
            else:
                variant.mindata = dict([(x, []) for x in variant.staters.keys()])

def stat_closeall():
    variant.staters = {}
    savdat = formator.json_string({'secdata': variant.secdata, 'mindata':variant.mindata})
    with open(utils.prefixStorageDir('stats.cache'),'w+') as fobj:
        fobj.write(savdat)

def stat_keepiters():
    for cobj in dclient.api.containers(all=True):
        cname = cobj['Names'][0][1:]
        if cname not in variant.staters:
            variant.staters[cname] = dclient.api.stats(cname, decode=True)
        if cname not in variant.secdata:
            variant.secdata[cname] = []
        if cname not in variant.mindata:
            variant.mindata[cname] = []

def logs_classall():
    variant.logiers = {}

def logs_keepiters():
    needskey = list(variant.alertlg.keys())
    for key in list(variant.logiers.keys()):
        if key not in needskey:
            variant.logiers[key].close()
            variant.logiers.pop(key)
    for cname in needskey:
        if cname not in variant.logiers:
            try:
                cobj = get_container(cname)
                if cobj.get('status') == 'running':
                    variant.logiers[cname] = dclient.api.logs(cname, stream=True, timestamps=True, tail=0)
            except Exception as e:
                traceback.print_exc()
        if cname not in variant.logthds:
            variant.logthds[cname] = threading.Thread(target=logs_run_once, args=(cname,), daemon=True)
            variant.logthds[cname].start()

def logs_run_once(cname):
    while True:
        if cname not in variant.logiers: break
        if cname not in variant.alertlg: break
        time.sleep(0.1)
        try:
            logtxt = variant.logiers[cname].next().decode()
            logtxt = logtxt.split(' ',1)
            timestamp = logtxt[0] if len(logtxt)==2 else ''
            content = logtxt[1] if len(logtxt)==2 else logtxt[0]
            for aobj in variant.alertlg[cname]:
                needtest = 'LASTRUNTIME' not in aobj or time.time()-aobj.LASTRUNTIME>60
                if not needtest:
                    continue
                match = re.match(aobj.ALSTR, content)
                aobj.LASTRUNTIME = time.time()
                if (match or content.find(aobj.ALSTR)>=0) and (content.find('INSERT INTO DM_MESSAGE')<0):
                    aobj.LASTALERTTIME = aobj.LASTRUNTIME
                    aobj.ALERTCOUNT = aobj.get('ALERTCOUNT', 0) + 1
                    testmsg = {"ALID": aobj.ALID, "ISPUSHED": aobj.ALPUSH if aobj.ALPUSH==1 else 0, "MSGSTAMP":formator.get_ts_from_utcstr(timestamp)}
                    testmsg["MSGBODY"] = "%s Log keyword found: %s\n\n%s %s"%(cname, aobj.ALSTR, timestamp, content)
                    msgret = mdb.new_message(testmsg)
                    lobj = variant.pubkeys.get(aobj.LICENSEID,{})
                    if not msgret.get('errmsg') and aobj.ALPUSH==1 and lobj.get('push_expire',0)>time.time():
                        try:
                            pshret = apush.pushNotification(aobj.LICENSEID,
                                lobj.get('SERVERID',''),
                                lobj.get('DEVICEID',''),
                                '%s Log alert'%lobj.get('SERVERNAME',''),
                                testmsg["MSGBODY"], 'domapp://message/%s?lid=%s'%(msgret['MSGID'],aobj.LICENSEID))
                        except Exception as e:
                            utils.outMessage(str(e))
        except Exception as e:
            variant.logiers.pop(cname, None)
            traceback.print_exc()
            utils.outMessage(str(e))
    variant.logiers.pop(cname, None)
    variant.logthds.pop(cname, None)

def stat_daemon():
    if variant['enable_stat'] != '1': return
    try:
        stat_init()
        utils.outMessage('Start stat_daemon')
        while True:
            if variant['enable_stat'] != '1':
                break
            time.sleep(0.01)
            stat_keepiters()
            stat_run_once()
            logs_keepiters()
        utils.outMessage('Stop stat_daemon')
        stat_closeall()
        logs_classall()
    except (KeyboardInterrupt, SystemExit):
        stat_closeall()
        logs_classall()
        utils.outMessage('Interrupt stat_daemon')

def alert_watch_2345(cname, mdat):

    for aobj in variant.alertcm.get(cname,[])+variant.alertph.get(cname,[]):
        if not mdat and aobj.ALTYPE in (2,3):
            continue
        needtest = 'LASTRUNTIME' not in aobj or time.time()-aobj.LASTRUNTIME>60
        if not needtest:
            continue
        if 'ALERTCOUNT' in aobj:
            if aobj.ALERTCOUNT == 1:
                pass
            elif aobj.ALERTCOUNT == 2:
                needtest = time.time()-aobj.LASTRUNTIME>2*60
            elif aobj.ALERTCOUNT == 3:
                needtest = time.time()-aobj.LASTRUNTIME>5*60
            elif aobj.ALERTCOUNT == 4:
                needtest = time.time()-aobj.LASTRUNTIME>15*60
            elif aobj.ALERTCOUNT == 5:
                needtest = time.time()-aobj.LASTRUNTIME>30*60
            elif aobj.ALERTCOUNT >= 6:
                needtest = datetime.fromtimestamp(time.time()).day != datetime.fromtimestamp(aobj.LASTRUNTIME).day
                if needtest: aobj.ALERTCOUNT = 0
        if not needtest:
            continue
        testisok = True
        testmsg = {"ALID": aobj.ALID, "ISPUSHED": aobj.ALPUSH if aobj.ALPUSH==1 else 0, "MSGSTAMP":mdat[0]}
        testtlt = ''
        if aobj.ALTYPE == 2 and mdat:
            testisok = mdat[1] < aobj.ALVAL
            if not testisok:
                testmsg["MSGBODY"] = "CPU usage %s > the set value %s"%(round(mdat[1],2), aobj.ALVAL)
                testtlt = 'CPU alert'
        if aobj.ALTYPE == 3 and mdat:
            testisok = mdat[2] < aobj.ALVAL*1024*1024
            if not testisok:
                testmsg["MSGBODY"] = "Memory usage %s MB > the set value %s MB"%(round(mdat[2]/1024/1024,2), aobj.ALVAL)
                testtlt = 'Memory alert'
        if aobj.ALTYPE == 4:
            ipport = aobj.ALSTR.split(":")
            timeout = 5
            testisok = utils.check_port(ipport[0], ipport[1], timeout)
            if not testisok:
                testmsg["MSGBODY"] = "Socket port %s unreachable in %d seconds."%(aobj.ALSTR, timeout)
                testtlt = 'Socket alert'
        if aobj.ALTYPE == 5:
            timeout = 15
            retdat = utils.check_http(aobj.ALSTR, timeout)
            testisok = retdat[0]<400
            if not testisok:
                testmsg["MSGBODY"] = "HTTP %s unreachable in %d seconds. %s %s"%(aobj.ALSTR, timeout, retdat[0], retdat[1])
                testtlt = 'Http alert'
        aobj.LASTRUNTIME = time.time()
        if not testisok:
            aobj.LASTALERTTIME = aobj.LASTRUNTIME
            aobj.ALERTCOUNT = aobj.get('ALERTCOUNT', 0) + 1
            testmsg["MSGBODY"] = ('System' if cname=='--sys--' else cname) + ' ' + testmsg["MSGBODY"]
            msgret = mdb.new_message(testmsg)
            lobj = variant.pubkeys.get(aobj.LICENSEID,{})
            if not msgret.get('errmsg') and aobj.ALPUSH==1 and lobj.get('push_expire',0)>time.time():
                try:
                    pshret = apush.pushNotification(aobj.LICENSEID,
                        lobj.get('SERVERID',''),
                        lobj.get('DEVICEID',''),
                        '%s %s'%(lobj.get('SERVERNAME',''), testtlt),
                        testmsg["MSGBODY"], 'domapp://message/%s?lid=%s'%(msgret['MSGID'],aobj.LICENSEID))
                except Exception as e:
                    utils.outMessage(str(e))
        else:
            aobj.pop('ALERTCOUNT', None)


def dict_image(iobj, tag='', parents=[], all_container=[]):
    if isinstance(iobj, docker.models.images.Image):
        retval = {
            'id': iobj.id,
            'name': tag or ','.join(iobj.tags),
            'Created': formator.get_ts_from_utcstr(iobj.attrs['Created']),
            'Size': iobj.attrs['Size'],
            'Used': 0,
            'ChildUsed': 0,
            'Running': 0,
            'Containers': [],
            'Parent': parents[0] if parents else {},
            'Children': [],
        }
    elif isinstance(iobj, dict):
        retval = {
            'id': iobj['Id'],
            'name': tag or ','.join(iobj['RepoTags']),
            'Created': iobj['Created'],
            'Size': iobj['Size'],
            'Used': 0,
            'ChildUsed': 0,
            'Running': 0,
            'Containers': [],
            'Parent': parents[0] if parents else {},
            'Children': [],
        }
    else:
        retval = {}
    for c in all_container:
        if isinstance(c, dict) and isinstance(iobj, dict) and (retval['name'].replace(':latest','') == c['Image'].replace(':latest','') or retval['id']==c['ImageID']):
            retval['Containers'].append(dict_container(c))
            retval['Used'] += 1
            if c['State']=='running':
                retval['Running'] += 1
        if isinstance(c, docker.models.containers.Container) and isinstance(iobj, docker.models.images.Image) and retval['name'].replace(':latest','') == c.attrs['Config']['Image'].replace(':latest',''):
            retval['Containers'].append(dict_container(c))
            retval['Used'] += 1
            if c.status=='running':
                retval['Running'] += 1
    return retval

def tree_image():
    retdic = {}
    try:
        all_container = dclient.api.containers(all=True)
        for m in dclient.api.images():
            parents = [{'Created':x['Created'],'name':ptag,'id':x['Id']} for x in dclient.api.history(m['Id']) for ptag in (x['Tags'] or []) if m['Id']!=x['Id']]
            if m['RepoTags']:
                for tag in m['RepoTags']:
                    mdat = dict_image(m, tag, parents, all_container)
                    retdic[mdat['id']] = mdat
            elif m['RepoDigests']:
                tag = m['RepoDigests'][0].split('@')[0] + ':<none>'
                mdat = dict_image(m, tag, parents, all_container)
                retdic[mdat['id']] = mdat
        import copy
        for mid, mdat in retdic.items():
            if mdat['Parent'] and mdat['Parent']['id'] in retdic:
                child = copy.copy(mdat)
                child.pop('Parent',None)
                child.pop('Containers',None)
                child.pop('Used',None)
                child.pop('ChildUsed',None)
                child.pop('Running',None)
                child.pop('Children',None)
                retdic[mdat['Parent']['id']]['Children'].append(child)
                retdic[mdat['Parent']['id']]['ChildUsed'] += mdat['Used']
    except Exception as e:
        traceback.print_exc()
        retdic = {}
    return retdic

def list_image():
    try:
        retdic = tree_image()
        retval = list(retdic.values())
        return retval
    except Exception as e:
        traceback.print_exc()
        return []

def get_image_byid(imgid):
    try:
        retdic = tree_image()
        return retdic.get(imgid,{})
    except Exception as e:
        traceback.print_exc()
        return {}

def get_image_byname(imgname):
    try:
        retdic = tree_image()
        retval = {}
        for key, val in retdic.items():
            if val['name'].split(':')[0]==imgname:
                retval = val
    except Exception as e:
        traceback.print_exc()
        return {}
    else:
        return retval

def remove_image(iname):
    try:
        dclient.api.remove_image(iname)
        return {"errmsg":""}
    except Exception as e:
        traceback.print_exc()
        return {"errmsg":e}



