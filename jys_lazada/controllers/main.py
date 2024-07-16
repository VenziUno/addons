from odoo import http
from odoo.http import request, Response
import json
import odoo
from odoo.exceptions import AccessDenied
import uuid

class LazadaAPI(http.Controller):

    @http.route('/lazada/auth/', type='http', auth='public', methods=['GET'], csrf=False)
    def lazada_auth(self, **kwargs):
        cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
        request.update_env(user=odoo.SUPERUSER_ID)
        env = request.env
        code = kwargs.get('code')
        if code:
            env['lazada.history.api'].create({
                'name': 'Code',
                'affected_list': code
            })
            return 'Success, Code received: %s' % code
        return 'Code not found in the callback URL'
