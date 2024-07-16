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

class LazadaGetAttribute(models.TransientModel):
    _name = 'lazada.get.attribute'
    _description = 'Lazada get Attribute'

    name = fields.Char('Name')
    shop_id = fields.Many2one('lazada.shop', 'Lazada Shop id')
    
    def create_attribute(self): 
        company = self.env.company
        attribute_obj = self.env['lazada.attribute']
        attribute_val_obj = self.env['lazada.attribute.value']
        
        category_obj = self.env['lazada.category']
        data = self
        if not data.shop_id:
            raise UserError(_('Please select your shop!'))

        shop = data.shop_id
        url = shop.region_id.url
        method = 'GET'
        access_token = shop.access_token
        request = '/category/attributes/get'
        language_code = "id_ID"
        log_line_values = []
                        
        for category_id in category_obj.search([]):
            params = {
                'primary_category_id': category_id.lazada_category_id,
                'language_code': language_code,
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
            if body.get('data', False):
                for att in body.get('data',[]):
                    attribute_exist = attribute_obj.search([('name', '=', att['name'])])
                    if attribute_exist:
                        continue
                    else:
                        attribute_id = attribute_obj.create({
                            'lazada_name': att.get('name', False),
                            'name': att.get('name', False),
                            'input_type': att.get('input_type', False),
                            'attribute_type': att.get('attribute_type', False),
                            'is_sale_prop': att.get('is_sale_prop', False),
                            'is_key_prop': att['advanced'].get('is_key_prop', False),
                            'is_key_prop': att.get('is_mandatory', False), 
                            'category_id': category_id.id,
                        })            
                        for val in att.get('options',[]):
                            attribute_val_obj.create({
                                'attribute_id': attribute_id.id,
                                'name': val.get('name')
                            })