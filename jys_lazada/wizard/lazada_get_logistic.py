import ast
import json
import requests
import time
import hashlib
import hmac
import math
from datetime import datetime, timedelta
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError

class LazadaGetLogistic(models.TransientModel):
    _name = 'lazada.get.logistic'
    _description = 'Lazada Get Logistic'
    
    name = fields.Char('Name')
    shop_id = fields.Many2one('lazada.shop', 'Lazada Shop id')

    def create_logistic(self): 
        company = self.env.company
        logistic_obj = self.env['lazada.logistic']
        delivery_obj = self.env['delivery.carrier']
        data = self
        if not data.shop_id:
            raise UserError(_('Please select your shop!'))

        shop = data.shop_id
        url = shop.region_id.url
        method = 'GET'
        access_token = shop.access_token
        request = '/shipment/providers/get'

        response = company.lazada_sdk(url=url, request=request,method=method, access_token=access_token)
        body = response.body
                
        for logistic in body['data'].get('shipment_providers',[]):
            logistic_exist = logistic_obj.search([('name', '=', logistic['name'])])
            delivery_exist = delivery_obj.search([('name', '=', logistic['name'])])
            if logistic_exist and delivery_exist:
                continue
            else:
                if not logistic_exist:
                    lazada_logisctic_id = logistic_obj.create({
                        'name': logistic.get('name','-'),
                        'is_cod': True if logistic.get('cod', False) else False,
                        'is_default': True if logistic.get('is_default', False) else False,
                        'is_api_integration': True if logistic.get('api_integration', False) else False,
                    })
                else:
                    lazada_logisctic_id = logistic_exist
                if not delivery_exist:
                    delivery_obj.create({
                        'name': logistic.get('name',False),
                        'lazada_logisctic_id' : lazada_logisctic_id.id,
                        'product_id' : company.lazada_logistic_product_id.id,
                        'is_lazada': True
                    })
