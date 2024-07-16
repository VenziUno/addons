import time
import json
import requests
import hashlib, hmac
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse

import lazop
from requests.models import PreparedRequest
req = PreparedRequest()

class ResCompany(models.Model):
    _inherit = "res.company"

    lazada_redirect_url = fields.Char('Lazada Redirect URL')
    lazada_app_key = fields.Char('Lazada App Key')
    lazada_app_secret = fields.Char('Lazada App Secret')

    lazada_shop_ids = fields.One2many('lazada.shop', 'company_id', 'Lazada Shops')

    lazada_pricelist_id = fields.Many2one('product.pricelist','Lazada Pricelist')
    lazada_logistic_product_id = fields.Many2one('product.product', 'Lazada Delivery Product')
    lazada_commission_product_id = fields.Many2one('product.product', 'Lazada Commission Product')
    lazada_rebate_product_id = fields.Many2one('product.product', 'Lazada Rebate Product')

    def lazada_sdk(self, url=None, request=None, params={}, method=None, access_token=None):
        for company in self:
            if not company.lazada_app_key:
                raise UserError(_('Please set your Lazada App Key!'))
            if not company.lazada_app_secret:
                raise UserError(_('Please set your Lazada App Secret!'))
            if not company.lazada_shop_ids:
                raise UserError(_('No shop found! Please configure at least 1 shop to start the integration.'))
            if not url:
                raise UserError(_('Please declare your API URL!'))
            if not request:
                raise UserError(_('Please declare your API Request!'))

            appkey = company.lazada_app_key
            appSecret = company.lazada_app_secret
            client = lazop.LazopClient(url, appkey ,appSecret)
            if method:
                request = lazop.LazopRequest(request, method)
            else:
                request = lazop.LazopRequest(request)

            for param in params:
                if param == 'image':
                    request.add_file_param(param, params[param])
                else:
                    request.add_api_param(param, params[param])


            if access_token:
                response = client.execute(request, access_token)
            else:
                response = client.execute(request)

            return response