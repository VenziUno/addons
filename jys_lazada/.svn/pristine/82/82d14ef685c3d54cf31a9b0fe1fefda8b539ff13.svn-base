import time
import json
import requests
import hashlib
import hmac
import PyPDF2 # type: ignore
import io
import base64
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse # type: ignore

class LazadaGetBrand(models.TransientModel):
    _name = 'lazada.get.brand'
    _description = 'Lazada get Brand'

    name = fields.Char('Name')
    shop_id = fields.Many2one('lazada.shop', 'Lazada Shop id')
    
    def create_brand(self): 
        company = self.env.company
        brand_obj = self.env['lazada.brand']
        data = self
        if not data.shop_id:
            raise UserError(_('Please select your shop!'))

        shop = data.shop_id
        url = shop.region_id.url
        method = 'GET'
        access_token = shop.access_token
        request = '/category/brands/query'
        startRow = 0
        pageSize = 200
        log_line_values = []

        continue_get = True
        while continue_get:
            params = {
                'startRow': startRow,
                'pageSize': pageSize
            }

            response = company.lazada_sdk(url=url, request=request, params=params, method=method, access_token=access_token)
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
                
            if body['data'].get('module', False):
                for brand in body['data'].get('module', False):
                    brand_exist = brand_obj.search([('lazada_brand_id', '=', brand['brand_id'])])
                    if brand_exist:
                        continue
                    else:
                        brand_obj.create({
                            'name': brand.get('name',False),
                            'name_en': brand.get('name_en',False),
                            'global_identifier': brand.get('global_identifier', False),
                            'lazada_brand_id':brand.get('brand_id',False),
                        })

                startRow += pageSize
            else:
                continue_get = False
                

