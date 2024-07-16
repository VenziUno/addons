import ast
import json
import requests
import time
import hashlib
import hmac
import math
import base64
from datetime import datetime, timedelta
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError

class LazadaGetProduct(models.TransientModel):
    _name = 'lazada.get.product'
    _description = 'Lazada Get Product'
    
    name = fields.Char('Name')
    shop_id = fields.Many2one('lazada.shop', 'Lazada Shop id')

    def create_product(self): 
        company = self.env.company

        lazada_product_obj = self.env['lazada.product']
        brand_obj = self.env['lazada.brand']
        product_obj = self.env['product.product']
        category_obj = self.env['lazada.category']
        product_template_attr_val_obj = self.env['product.template.attribute.value']
        lazada_product_var_obj = self.env['lazada.product.variant']
        product_template_obj = self.env['product.template']
        attribute_val_obj = self.env['product.attribute.value']
        pt_attribute_line_obj = self.env['product.template.attribute.line']
        attribute_obj = self.env['product.attribute']
        price_list_line_obj = self.env['product.pricelist.item']
        
        data = self
        if not data.shop_id:
            raise UserError(_('Please select your shop!'))

        shop = data.shop_id
        url = shop.region_id.url
        method = 'GET'
        access_token = shop.access_token
        request = '/products/get'
        log_line_values = []
        limit = 50
        offset =  0
        
        def _create_attachment(product_tmpl_id, url):
            attactment_id = False
            response = requests.get(url)
            if response.status_code == 200:
                image_data = base64.b64encode(response.content)
                attactment_id = self.env['ir.attachment'].create({
                    'name': url.split('/')[-1],
                    'type': 'binary',
                    'datas': image_data,
                    'mimetype': 'image/jpeg',
                    'res_model': 'product.template',
                    'res_id': product_tmpl_id,
                }).id
            return attactment_id
        continue_get = True
        while continue_get: 
            params = {
                'limit': f'{limit}',
                'offset': f'{offset}',
            }
            response = company.lazada_sdk(url=url, params=params, request=request, method=method, access_token=access_token)
            bodys = response.body
            
            code = bodys['code']
            if code != '0':
                log_line_values.append((0, 0, {
                    'name': 'Get Product',
                    'url': url,
                    'request': request,
                    'method': method,
                    'access_token': access_token,
                    'error_responses': bodys['message'],
                    'state': 'failed',
                }))
            if bodys['data'].get('products',False):
                for product in bodys['data'].get('products',[]):
                    product_exist = lazada_product_obj.search([('item_id', '=', product['item_id']),('shop_id', '=', shop.id)])
                    if product_exist.product_tmpl_id:
                        request_item = '/product/item/get'
                        paramss = {
                            'item_id': product['item_id']
                        }
                        response = company.lazada_sdk(url=url, request=request_item,params=paramss, method=method, access_token=access_token)
                        body = response.body
                        data = body.get('data')
                        prod_val = {}
                        product_tmpl_id = product_exist.product_tmpl_id
                        brand_exist = brand_obj.search([('name','=',data['attributes'].get('brand',False))])
                        category_exist = category_obj.search([('lazada_category_id','=', data['primary_category'])])
                        
                        if brand_exist:
                            brand_id = brand_exist
                        else: 
                            brand_id = brand_obj.create({
                                'name':data['attributes'].get('brand',False),
                            })
                            
                        if category_exist:
                            category_id = category_exist
                        else: 
                            category_id = category_obj.create({
                                'name': "-",
                            })
                        if product_tmpl_id.name != data.get('name'):
                            prod_val['name'] = data['attributes'].get('name')
                        if product_tmpl_id.lazada_brand_id != brand_id:
                            prod_val['lazada_brand_id'] = brand_id.id
                        if product_tmpl_id.lazada_category_id != category_id:
                            prod_val['lazada_category_id'] = category_id.id
                        if product_tmpl_id.lazada_desc != data['attributes'].get('description'):
                            prod_val['lazada_desc'] = data['attributes'].get('description')
                        if data.get('skus'):
                            if product_tmpl_id.lz_package_height != data.get('skus')[0].get('package_height'):
                                prod_val['lz_package_height'] = data.get('skus')[0].get('package_height',False)
                            if product_tmpl_id.lz_package_length != data.get('skus')[0].get('lz_package_length'):
                                prod_val['lz_package_length'] = data.get('skus')[0].get('lz_package_length',False)
                            if product_tmpl_id.lz_package_weight != data.get('skus')[0].get('package_weight'):
                                prod_val['lz_package_weight'] = data.get('skus')[0].get('package_weight',False)
                            if product_tmpl_id.weight != data.get('skus')[0].get('product_weight'):
                                prod_val['weight'] = data.get('skus')[0].get('product_weight',False)
                                
                        upload_product_tt_image_ids = []
                        for img in data['skus'][0].get('Images'):
                            img_url = img
                            attactment_id = _create_attachment(product_tmpl_id.id, img_url)
                            upload_product_tt_image_ids.append((4, attactment_id))        
                        product_tmpl_id.action_delete_all_lazada_img()
                        prod_val['upload_product_tt_image_ids'] = upload_product_tt_image_ids
                        product_tmpl_id.with_context(tiktok_get_product=True).write(prod_val)
                        
                        list_sku = []
                        for attr in range(len(data.get('variation'))):
                            attr += 1
                            atribute = data.get('variation').get(f"Variation{attr}")
                            name=atribute.get('name')
                            value_name=atribute.get('options')

                            attribute_id = attribute_obj.search([('name','=',name)], limit=1)
                            if not attribute_id:
                                attribute_id = attribute_obj.create({'name': name})
                            
                            for val in value_name :
                                attribute_val_id = attribute_val_obj.search([('name','=',val),('attribute_id','=',attribute_id.id)], limit=1)
                                if not attribute_val_id:
                                    attribute_val_id = attribute_val_obj.create({'name':val, 'attribute_id':attribute_id.id})

                                pt_attr = pt_attribute_line_obj.search([('attribute_id','=',attribute_id.id),('product_tmpl_id','=',product_tmpl_id.id)])

                                if not pt_attr:
                                    pt_attr = pt_attribute_line_obj.create({'product_tmpl_id':product_tmpl_id.id,'attribute_id': attribute_id.id,'value_ids': [(6, 0, [attribute_val_id.id])]})
                                else:
                                    pt_attr.write({
                                        'value_ids': [(4, attribute_val_id.id, 0)]
                                    })
                            
                        list_product_sku = []
                        for variant in product_tmpl_id.product_variant_ids:
                            for sku_detail in data.get('skus'):                      
                                if list(x.product_attribute_value_id.name for x in variant.product_template_variant_value_ids) == list(sku_detail.get('saleProp').values()):
                                    datas = sku_detail
                                    break
                            variant.write({
                                'lazada_seller_sku': datas.get('SellerSku'),
                                'lst_price': datas.get('price'),
                                'is_sync_lazada': True,
                            })
                                
                            lazada_product_var_obj.create({
                                'shop_id': shop.id,
                                'variation_id': datas['SkuId'],
                                'seller_sku': datas.get('SellerSku'),
                                'shop_sku': datas.get('ShopSku'),
                                'product_id': variant.id
                            })
                            
                            price_list_line_id = price_list_line_obj.search([('pricelist_id','=',company.lazada_pricelist_id.id),('product_id','=',variant.id)])
                            if price_list_line_id :    
                                price_list_line_obj.create({
                                    'fixed_price': datas.get('price'),
                                    'min_quantity': 1,
                                    'product_id': variant.id,
                                    'product_tmpl_id': product_tmpl_id.id,
                                    'pricelist_id': company.lazada_pricelist_id.id
                                })
                            else :
                                continue
                    else: 
                        time.sleep(1)
                        request_item = '/product/item/get'
                        paramss = {
                        'item_id': product['item_id']
                        }
                        response = company.lazada_sdk(url=url, request=request_item,params=paramss, method=method, access_token=access_token)
                        body = response.body
                        data = body.get('data')
                                            
                        product_values = {}              
                        brand_exist = brand_obj.search([('name','=',data['attributes'].get('brand',False))])
                        category_exist = category_obj.search([('lazada_category_id','=', data['primary_category'])])
                        if brand_exist:
                            brand_id = brand_exist
                        else: 
                            brand_id = brand_obj.create({
                                'name':data['attributes'].get('brand',False),
                            })
                        if category_exist:
                            category_id = category_exist
                        else: 
                            category_id = category_obj.create({
                                'name': "-",
                            })
                                
                        product_values['name'] = data['attributes'].get('name',False)    
                        product_values['lazada_brand_id'] = brand_id.id
                        product_values['lazada_category_id'] = category_id.id
                        product_values['lazada_desc'] = data['attributes'].get('description',False)
                        if data.get('skus'):
                            product_values['lz_package_height'] = data.get('skus')[0].get('package_height')
                            product_values['lz_package_length'] = data.get('skus')[0].get('package_length')
                            product_values['lz_package_weight'] = data.get('skus')[0].get('package_weight')
                            product_values['weight'] = data.get('skus')[0].get('product_weight')
                        product_values['is_lazada'] = True  
                                            
                        product_tmpl_id = product_template_obj.create(product_values)
                        upload_product_tt_image_ids = []
                        for img in data['skus'][0].get('Images'):
                            img_url = img
                            attactment_id = _create_attachment(product_tmpl_id.id, img_url)
                            upload_product_tt_image_ids.append((4, attactment_id))
                        
                        lazada_product_obj.create({
                            'shop_id': shop.id,
                            'item_id': data.get('item_id'),
                            'product_tmpl_id': product_tmpl_id.id
                        })
                            
                        list_sku = []
                        for attr in range(len(data.get('variation'))):
                            attr += 1
                            atribute = data.get('variation').get(f"Variation{attr}")
                            name=atribute.get('name')
                            value_name=atribute.get('options')

                            attribute_id = attribute_obj.search([('name','=',name)], limit=1)
                            if not attribute_id:
                                attribute_id = attribute_obj.create({'name': name})
                            
                            for val in value_name :
                                attribute_val_id = attribute_val_obj.search([('name','=',val),('attribute_id','=',attribute_id.id)], limit=1)
                                if not attribute_val_id:
                                    attribute_val_id = attribute_val_obj.create({'name':val, 'attribute_id':attribute_id.id})

                                pt_attr = pt_attribute_line_obj.search([('attribute_id','=',attribute_id.id),('product_tmpl_id','=',product_tmpl_id.id)])

                                if not pt_attr:
                                    pt_attr = pt_attribute_line_obj.create({'product_tmpl_id':product_tmpl_id.id,'attribute_id': attribute_id.id,'value_ids': [(6, 0, [attribute_val_id.id])]})
                                else:
                                    pt_attr.write({
                                        'value_ids': [(4, attribute_val_id.id, 0)]
                                    })
                            
                        list_product_sku = []
                        for variant in product_tmpl_id.product_variant_ids:
                            for sku_detail in data.get('skus'):                      
                                if list(x.product_attribute_value_id.name for x in variant.product_template_variant_value_ids) == list(sku_detail.get('saleProp').values()):
                                    datas = sku_detail
                                    break
                            variant.write({
                                'lazada_seller_sku': datas.get('SellerSku'),
                                'lst_price': datas.get('price'),
                                'is_sync_lazada': True,
                            })
                                
                            lazada_product_var_obj.create({
                                'shop_id': shop.id,
                                'variation_id': datas['SkuId'],
                                'seller_sku': datas.get('SellerSku'),
                                'shop_sku': datas.get('ShopSku'),
                                'product_id': variant.id
                            })
                                
                            price_list_line_obj.create({
                                'fixed_price': datas.get('price'),
                                'min_quantity': 1,
                                'product_id': variant.id,
                                'product_tmpl_id': product_tmpl_id.id,
                                'pricelist_id': company.lazada_pricelist_id.id
                            })
                offset += limit
            else:
                continue_get = False
