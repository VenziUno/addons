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

class LazadaGetWarehouse(models.TransientModel):
    _name = 'lazada.get.warehouse'
    _description = 'Lazada Get Warehouse'
    
    name = fields.Char('Name')
    shop_id = fields.Many2one('lazada.shop', 'Lazada Shop id')

    def create_warehouse(self): 
        company = self.env.company
        warehouse_obj = self.env['lazada.warehouse']
        data = self
        if not data.shop_id:
            raise UserError(_('Please select your shop!'))

        shop = data.shop_id
        url = shop.region_id.url
        method = 'GET'
        access_token = shop.access_token
        request = '/fbl/icp_warehouse/list'
        log_line_values = []
        
        warehouse_type = ['Inbound','outbound', 'Seller']
        for type_ in warehouse_type:
            params = {'warehouse_type': type_}
            
            response = company.lazada_sdk(url=url, request=request,params=params,method=method, access_token=access_token)
            body = response.body
            
            code = body['code']
            if code != '0':
                log_line_values.append((0, 0, {
                    'name': 'Get Brands',
                    'url': url,
                    'request': request,
                    'params': params,
                    'method': method,
                    'access_token': access_token,
                    'error_responses': body['message'],
                    'state': 'failed',
                }))
                
            for warehouse in body.get('data', False):
                warehouse_exist = warehouse_obj.search([('code', '=', warehouse['warehouse_code'])])
                if warehouse_exist:
                    continue
                else:
                    warehouse_obj.create({
                        'name': warehouse.get('warehouse_name',False),
                        'code': warehouse.get('warehouse_code',False),
                    })

                