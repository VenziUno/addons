from odoo import http
from odoo.http import request, Response
import json
import odoo
from odoo.exceptions import AccessDenied
import uuid

class TiktokAPI(http.Controller):

    @http.route('/tiktok/auth/', type='http', auth='public', methods=['GET'], csrf=False)
    def tiktok_auth(self, **kwargs):
        cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
        request.update_env(user=odoo.SUPERUSER_ID)
        env = request.env
        code = kwargs.get('code')
        if code:
            env['tiktok.history.api'].create({
                'name': 'Code',
                'affected_list': code
            })
            return 'Success, Code received: %s' % code
        return 'Code not found in the callback URL'
