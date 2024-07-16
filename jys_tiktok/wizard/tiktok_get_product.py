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

class TiktokGetProduct(models.TransientModel):
    _name = 'tiktok.get.product'
    _description = 'Tiktok Get Products'

    shop_id = fields.Many2one('tiktok.shop', 'Shop')

    def action_confirm(self):
        company_obj = self.env['res.company']
        product_tmpl_obj = self.env['product.template']
        product_obj = self.env['product.product']
        pricelist_line_obj = self.env['product.pricelist.item']
        tiktok_product_obj = self.env['tiktok.product']
        tiktok_product_var_obj = self.env['tiktok.product.variant']
        tiktok_product_img_obj = self.env['tiktok.product.image']
        tiktok_warehouse_obj = self.env['tiktok.warehouse']
        brand_obj = self.env['tiktok.brand']
        category_obj = self.env['tiktok.category']
        attribute_obj = self.env['product.attribute']
        attribute_val_obj = self.env['product.attribute.value']
        pt_attribute_line_obj = self.env['product.template.attribute.line']
        company = self.env.company
        shop = self.shop_id
        access_token = shop.tiktok_token
        tiktok_id = shop.shop_id
        chiper = str(shop.tiktok_chiper)
        domain = company.tiktok_api_domain
        app = company.tiktok_client_id
        key = company.tiktok_client_secret
        timest = int(time.time())
        page_size = 100
        sign = ''
        page_token = ''

        path = "/product/202312/products/search"
        headers = {
            'x-tts-access-token': str(access_token), 
            "Content-type": "application/json"
        }
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

        while True:
            base_url = f"{domain}{path}?app_key={app}&timestamp={timest}&shop_cipher={chiper}&page_size={page_size}"

            params = []
            if page_token:
                params.append(f"page_token={page_token}")

            url = f"{base_url}&{'&'.join(params)}"
            sign = company_obj.cal_sign(url, key, headers)
            url = f"{base_url}&sign={sign}&{'&'.join(params)}"

            res = requests.post(url, headers=headers)
            values = res.json()
            for prod in values.get('data').get('products',[]):
                if prod.get('status',False) == 'DELETED':
                    continue
                prod_url = f"{domain}/product/202309/products/{prod.get('id')}?app_key={app}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"
                sign = company_obj.cal_sign(prod_url, key, headers)
                prod_url = f"{domain}/product/202309/products/{prod.get('id')}?app_key={app}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"

                res = requests.get(prod_url, headers=headers)
                prod_values = res.json()
                tiktok_product_id = tiktok_product_obj.search([('shop_id','=',shop.id),('item_id','=',prod.get('id'))])
                if not tiktok_product_id.product_tmpl_id:
                    product_values = {}
                    data = prod_values.get('data')
                    name = data.get('title')
                    brand_id = data.get('brand').get('id')
                    category_id = data.get('category_chains')[-1].get('id')

                    product_values['name'] = name
                    product_values['is_tiktok'] = True
                    product_values['detailed_type'] = 'product'
                    product_values['tiktok_description'] = data.get('description')

                    brand = brand_obj.search([('brand_id','=',brand_id)], limit=1)
                    if brand:
                        product_values['tiktok_brand_id'] = brand.id
                    else:
                        brand = brand_obj.create({
                            'name': data.get('brand').get('name'),
                            'brand_id': data.get('brand').get('id')
                        })
                        product_values['tiktok_brand_id'] = brand.id

                    category = category_obj.search([('tiktok_category_id','=',int(category_id))], limit=1)
                    if category:
                        product_values['tiktok_category_id'] = category.id
                    else:
                        category = category_obj.create({
                            'name': data.get('category_chains')[-1].get('local_name'),
                            'is_leaf': data.get('category_chains')[-1].get('is_leaf'),
                            'tiktok_parent_id': int(data.get('category_chains')[-1].get('parent_id')),
                            'tiktok_category_id': int(data.get('category_chains')[-1].get('id'))
                        })
                        product_values['tiktok_category_id'] = category.id

                    if data.get('package_dimensions'):
                        product_values['pack_dimension_unit'] = data.get('package_dimensions').get('unit')
                        product_values['tiktok_height'] = data.get('package_dimensions').get('height')
                        product_values['tiktok_width'] = data.get('package_dimensions').get('width')
                        product_values['tiktok_length'] = data.get('package_dimensions').get('length')

                    
                    if data.get('package_weight'):
                        product_values['pack_weight_unit'] = data.get('package_weight').get('unit')
                        product_values['pack_weight_value'] = data.get('package_weight').get('value')


                    product_tmpl_id = product_tmpl_obj.create(product_values)

                    upload_product_tt_image_ids = []
                    for img in data.get('main_images'):
                        img_url = img.get('urls')[0]
                        attactment_id = _create_attachment(product_tmpl_id.id, img_url)
                        upload_product_tt_image_ids.append((4, attactment_id))

                    #AFTER CREATE PRODUCT
                    tiktok_product_obj.create({
                        'shop_id': shop.id,
                        'item_id': prod.get('id'),
                        'product_tmpl_id': product_tmpl_id.id
                    })

                    list_sku = []
                    for sku in data.get('skus'):
                        for attr in sku.get('sales_attributes'):
                            attr_name = attr.get('name')
                            value_name = attr.get('value_name')

                            attribute_id = attribute_obj.search([('name','=',attr_name)], limit=1)
                            if not attribute_id:
                                attribute_id = attribute_obj.create({'name':attr_name})

                            attribute_val_id = attribute_val_obj.search([('name','=',value_name),('attribute_id','=',attribute_id.id)], limit=1)
                            if not attribute_val_id:
                                attribute_val_id = attribute_val_obj.create({'name':value_name, 'attribute_id':attribute_id.id})

                            pt_attr = pt_attribute_line_obj.search([('attribute_id','=',attribute_id.id),('product_tmpl_id','=',product_tmpl_id.id)], limit=1)
                            if not pt_attr:
                                product_tmpl_id.write({
                                    'attribute_line_ids': [(0, 0, {
                                        'attribute_id': attribute_id.id,
                                        'value_ids': [(6, 0, [attribute_val_id.id])]
                                    })]
                                })
                            else:
                                pt_attr.write({
                                    'value_ids': [(4, attribute_val_id.id, 0)]
                                })



                        list_sku.append((sku.get('seller_sku'),sku.get('price').get('sale_price'),sku.get('id'),sku.get('inventory')[0].get('warehouse_id')))
                    var = 0
                    warehouse_id = False
                    for pp in product_tmpl_id.product_variant_ids:
                        pp.write({
                            'tiktok_variation_sku': list_sku[var][0],
                            'lst_price': float(list_sku[var][1])
                        })

                        tiktok_product_var_id = tiktok_product_var_obj.search([('shop_id','=',shop.id),('variation_id','=',list_sku[var][2]),('product_id','=',pp.id)])
                        if not tiktok_product_var_id:
                            tiktok_product_var_obj.create({
                                'shop_id': shop.id,
                                'variation_id': list_sku[var][2],
                                'product_id': pp.id
                            })

                        pricelist_line_id = pricelist_line_obj.search([('pricelist_id','=',company.tiktok_pricelist_id.id),('product_id','=',pp.id)])
                        if not pricelist_line_id:
                            pricelist_line_obj.create({
                                'pricelist_id': company.tiktok_pricelist_id.id,
                                'product_tmpl_id': product_tmpl_id.id,
                                'product_id': pp.id,
                                'min_quantity': 1,
                                'fixed_price': float(list_sku[var][1])
                            })
                        warehouse_id = list_sku[var][3]
                        var +=1

                    tiktok_warehouse_id = tiktok_warehouse_obj.search([('warehouse_id','=',warehouse_id)], limit=1)
                    if tiktok_warehouse_id:
                        product_tmpl_id.write({'tiktok_warehouse_id':tiktok_warehouse_id.id})
                    product_tmpl_id.with_context(tiktok_get_product=True).write({'upload_product_tt_image_ids':upload_product_tt_image_ids})

                else:
                    product_values = {}
                    product_tmpl_id = tiktok_product_id.product_tmpl_id
                    data = prod_values.get('data')
                    name = data.get('title')
                    brand_id = data.get('brand').get('id')
                    category_id = data.get('category_chains')[-1].get('id')

                    if product_tmpl_id.name != name:
                        product_values['name'] = name
                    if product_tmpl_id.tiktok_description != data.get('description'):
                        product_values['tiktok_description'] = data.get('description')

                    brand = brand_obj.search([('brand_id','=',brand_id)], limit=1)
                    if brand:
                        if product_tmpl_id.tiktok_brand_id != brand:
                            product_values['tiktok_brand_id'] = brand.id
                    else:
                        brand = brand_obj.create({
                            'name': data.get('brand').get('name'),
                            'brand_id': data.get('brand').get('id')
                        })
                        if product_tmpl_id.tiktok_brand_id != brand:
                            product_values['tiktok_brand_id'] = brand.id

                    category = category_obj.search([('tiktok_category_id','=',int(category_id))], limit=1)
                    if category:
                        if product_tmpl_id.tiktok_category_id != category:
                            product_values['tiktok_category_id'] = category.id
                    else:
                        category = category_obj.create({
                            'name': data.get('category_chains')[-1].get('local_name'),
                            'is_leaf': data.get('category_chains')[-1].get('is_leaf'),
                            'tiktok_parent_id': int(data.get('category_chains')[-1].get('parent_id')),
                            'tiktok_category_id': int(data.get('category_chains')[-1].get('id'))
                        })
                        if product_tmpl_id.tiktok_category_id != category:
                            product_values['tiktok_category_id'] = category.id

                    if data.get('package_dimensions'):
                        if product_tmpl_id.pack_dimension_unit != data.get('package_dimensions').get('unit'):
                            product_values['pack_dimension_unit'] = data.get('package_dimensions').get('unit')
                        if product_tmpl_id.tiktok_height != data.get('package_dimensions').get('height'):
                            product_values['tiktok_height'] = data.get('package_dimensions').get('height')
                        if product_tmpl_id.tiktok_width != data.get('package_dimensions').get('width'):
                            product_values['tiktok_width'] = data.get('package_dimensions').get('width')
                        if product_tmpl_id.tiktok_length != data.get('package_dimensions').get('length'):
                            product_values['tiktok_length'] = data.get('package_dimensions').get('length')

                    
                    if data.get('package_weight'):
                        if product_tmpl_id.pack_weight_unit != data.get('package_weight').get('unit'):
                            product_values['pack_weight_unit'] = data.get('package_weight').get('unit')
                        if product_tmpl_id.pack_weight_value != data.get('package_weight').get('value'):
                            product_values['pack_weight_value'] = data.get('package_weight').get('value')


                    upload_product_tt_image_ids = []
                    for img in data.get('main_images'):
                        img_url = img.get('urls')[0]
                        attactment_id = _create_attachment(product_tmpl_id.id, img_url)
                        upload_product_tt_image_ids.append((4, attactment_id))

                    list_sku = []
                    for sku in data.get('skus'):
                        for attr in sku.get('sales_attributes'):
                            attr_name = attr.get('name')
                            value_name = attr.get('value_name')

                            attribute_id = attribute_obj.search([('name','=',attr_name)], limit=1)
                            if not attribute_id:
                                attribute_id = attribute_obj.create({'name':attr_name})

                            attribute_val_id = attribute_val_obj.search([('name','=',value_name),('attribute_id','=',attribute_id.id)], limit=1)
                            if not attribute_val_id:
                                attribute_val_id = attribute_val_obj.create({'name':value_name, 'attribute_id':attribute_id.id})

                            pt_attr = pt_attribute_line_obj.search([('attribute_id','=',attribute_id.id),('product_tmpl_id','=',product_tmpl_id.id)], limit=1)
                            if not pt_attr:
                                product_tmpl_id.write({
                                    'attribute_line_ids': [(0, 0, {
                                        'attribute_id': attribute_id.id,
                                        'value_ids': [(6, 0, [attribute_val_id.id])]
                                    })]
                                })
                            else:
                                pt_attr.write({
                                    'value_ids': [(4, attribute_val_id.id, 0)]
                                })



                        list_sku.append((sku.get('seller_sku'),sku.get('price').get('sale_price'),sku.get('id'),sku.get('inventory')[0].get('warehouse_id')))
                    var = 0
                    warehouse_id = False
                    for pp in product_tmpl_id.product_variant_ids:
                        pp.write({
                            'tiktok_variation_sku': list_sku[var][0],
                            'lst_price': float(list_sku[var][1])
                        })
                        tiktok_product_var_id = tiktok_product_var_obj.search([('shop_id','=',shop.id),('variation_id','=',list_sku[var][2]),('product_id','=',pp.id)])
                        if not tiktok_product_var_id:
                            tiktok_product_var_obj.create({
                                'shop_id': shop.id,
                                'variation_id': list_sku[var][2],
                                'product_id': pp.id
                            })
                        pricelist_line_id = pricelist_line_obj.search([('pricelist_id','=',company.tiktok_pricelist_id.id),('product_id','=',pp.id)])
                        if not pricelist_line_id:
                            pricelist_line_obj.create({
                                'pricelist_id': company.tiktok_pricelist_id.id,
                                'product_tmpl_id': product_tmpl_id.id,
                                'product_id': pp.id,
                                'min_quantity': 1,
                                'fixed_price': float(list_sku[var][1])
                            })
                        warehouse_id = list_sku[var][3]
                        var +=1

                    tiktok_warehouse_id = tiktok_warehouse_obj.search([('warehouse_id','=',warehouse_id)], limit=1)
                    if tiktok_warehouse_id:
                        if product_tmpl_id.tiktok_warehouse_id != tiktok_warehouse_id:
                            product_values['tiktok_warehouse_id'] = tiktok_warehouse_id.id
                    product_tmpl_id.action_delete_all_tiktok_img()
                    product_values['upload_product_tt_image_ids'] = upload_product_tt_image_ids
                    product_tmpl_id.with_context(tiktok_get_product=True).write(product_values)


            if values.get('data').get('next_page_token'):
                page_token = values.get('data').get('next_page_token')
            if not values.get('data').get('next_page_token'):
                break