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

class LazadaGetCategory(models.TransientModel):
    _name = 'lazada.get.category'
    _description = 'Lazada Get Category'
    
    name = fields.Char('Name')
    shop_id = fields.Many2one('lazada.shop', 'Lazada Shop id')
    

    def create_category(self): 
        company = self.env.company
        category_obj = self.env['lazada.category']
        history_obj = self.env['lazada.history.api']
        data = self
        if not data.shop_id:
            raise UserError(_('Please select your shop!'))

        shop = data.shop_id
        url = shop.region_id.url
        method = 'GET'
        access_token = shop.access_token
        
        request = '/category/tree/get'
        language_code = "id_ID"
        inserted_count = 0
        updated_count = 0
        affected_count = 0
        skipped_count = 0
        affected_list = ''
        skipped_list = ''
        additional_info = ''
        context = {}
        timest = int(time.time()) 
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('jys_lazada.view_lazada_history_api_popup')
        view_id = view_ref and view_ref[1] or False
               
        params = {
            'language_code': language_code,
        }
        
        response = company.lazada_sdk(url=url, request=request, params=params, method=method, access_token=access_token)
        body = response.body
        code = body['code']
        if code != '0':

            history_id = history_obj.create({
                'name': 'Get Category',
                'shop_id': shop.id,
                'skipped_list': body['message'],
                'timestamp': timest,
                'state': 'failed',
            }).id
            
            return {
                'name': 'History API',
                'type': 'ir.actions.act_window',
                'res_model': 'lazada.history.api',
                'res_id': history_id,
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'new',
                'context': context
            }

        for category in body['data']:
            category_exist = category_obj.search([('lazada_category_id', '=', category['category_id'])])
            parent_category = False
            if category_exist:
                continue
            else:
                parent_category = category_obj.create({
                    'name': category.get('name',False),
                    'lazada_category_id': category.get('category_id', False),
                })

                if category.get('children', False):
                    parent_category_2 = False
                    for children_category in category['children']:
                        category_exist = category_obj.search([('lazada_category_id', '=', children_category['category_id'])])
                        if category_exist:
                            continue
                        else:
                            parent_category_2 = category_obj.create({
                                'name': children_category.get('name',False),
                                'is_leaf': children_category.get('leaf',False),
                                'is_var': children_category.get('var',False),
                                'parent_id': parent_category.id,
                                'lazada_category_id': children_category.get('category_id',False),
                            })

                        if children_category.get('children', False):
                            parent_category_3 = False
                            for children_category_2 in children_category['children']:
                                category_exist = category_obj.search([('lazada_category_id', '=', children_category_2['category_id'])])
                                if category_exist:
                                    continue
                                else:
                                    parent_category_3 = category_obj.create({
                                        'name': children_category_2.get('name',False),
                                        'is_leaf': children_category_2.get('leaf',False),
                                        'is_var': children_category_2.get('var',False),
                                        'parent_id': parent_category_2.id,
                                        'lazada_category_id': children_category_2.get('category_id',False),     
                                    })

                                if children_category_2.get('children', False):
                                    for children_category_3 in children_category_2['children']:
                                        category_exist = category_obj.search([('lazada_category_id', '=', children_category_3['category_id'])])
                                        if category_exist:
                                            continue
                                        else:
                                            category_obj.create({
                                                'name': children_category_3.get('name',False),
                                                'is_leaf': children_category_3.get('leaf',False),
                                                'is_var': children_category_3.get('var',False),
                                                'parent_id': parent_category_3.id,
                                                'lazada_category_id': children_category_3.get('category_id',False),     
                                            })