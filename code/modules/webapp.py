#!/usr/bin/env python
#-*- encoding: utf-8 -*-

from config import *

urls_view = (
    '',             'CtrlIndex',
    '/',            'CtrlIndex',
)
app_www = web.application(urls_view, locals())

class CtrlIndex:
    def GET(self):
        web.seeother('/mildred')

class CtrlViewController(object):
    def GET(self):
        render = variant.get_render(web.ctx.path[1:])
        pagedata = {"realhome": web.ctx.get('realhome', '')}
        if render:
            return render(pagedata)
        else:
            return web.notfound()


