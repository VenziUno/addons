import json
import time
import hmac
import hashlib
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import base64
from io import BytesIO
from PIL import Image
import requests
import lazop

class LazadaAddProduct(models.TransientModel):
    _name = 'lazada.add.product'
    _description = 'Lazada Add Product'

    shop_ids = fields.Many2many('lazada.shop', 'lazada_add_product_shop_rel', 'add_wizard_id', 'shop_id', string='Shops')
    shop_id = fields.Many2one('lazada.shop','Shop')

    def action_confirm_xml(self):
        context = self.env.context
        product_tmpl_obj = self.env['product.template']
        product_obj = self.env['product.product']
        product_tmpl_ids = product_tmpl_obj.browse(context.get('active_ids'))
        lazada_product_obj = self.env['lazada.product']
        lazada_product_var_obj = self.env['lazada.product.variant']
        company_obj = self.env['res.company']
        company = self.env.company
        shop = self.shop_id
        url = shop.region_id.url
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        method = 'POST'
        access_token = shop.access_token
        path = '/product/create'

        if not shop:
            raise UserError(_('Please select the Shop.'))

        for product_tmpl in product_tmpl_ids:
            if not product_tmpl.is_lazada:
                raise UserError(_('Kolom Lazada Product mohon dicentang.'))

            lazada_product_id = lazada_product_obj.search([('shop_id', '=', shop.id), ('product_tmpl_id', '=', product_tmpl.id), ('product_tmpl_id.active', '=', True)], limit=1)
            if lazada_product_id:
                raise UserError(_('Produk ini sudah ada di Lazada.'))

            Hazmat = []
            if product_tmpl.is_battery:
                Hazmat.append('Battery')
            if product_tmpl.is_flammable:
                Hazmat.append('Flammable')
            if product_tmpl.is_liquid:
                Hazmat.append('Liquid')
            if product_tmpl.is_none:
                Hazmat.append('None')
            Hazmat = ','.join(Hazmat)

            lazada_product_image_ids = []
            for img in product_tmpl.lazada_product_image_ids:
                if img.uri:
                    lazada_product_image_ids.append(img.uri)
                else:
                    img_path = '/image/upload'
                    img_format = img.name.split('.')[-1]
                    img_bytes = base64.b64decode(img.image)
                    
                    img_params = {
                      'image': (img.name,img_bytes,img_format)
                    }
                    upload = company.lazada_sdk(url=url, request=img_path, params=img_params, method=method, access_token=access_token)
                    img_data = upload.body

                    if img_data.get('data') and img_data.get('data').get('image'):
                        img.write({
                            'uri': img_data.get('data').get('image').get('url')
                        })
                        lazada_product_image_ids.append(img_data.get('data').get('image').get('url'))

            product_tmpl_images = ""
            if lazada_product_image_ids:
                for image in lazada_product_image_ids:
                    product_tmpl_images = product_tmpl_images + '<Image>' + image
                    product_tmpl_images = product_tmpl_images + '</Image>'
            if product_tmpl_images:
                product_tmpl_images = f"""
                <Images>
                    {product_tmpl_images}
                </Images>
                """

            attributes = ""
            if not product_tmpl.lz_package_height or not product_tmpl.lz_package_width or not product_tmpl.lz_package_length or not product_tmpl.lz_package_weight:
                raise UserError(_('Mohon melengkapi data Package.'))
            if len(product_tmpl.name) > 255:
                raise UserError(_('Nama produk melebihi 255 karakter.'))
            if not (product_tmpl.lazada_category_id or product_tmpl.lazada_brand_id):
                raise UserError(_('Mohon Category dan Brand di isi.'))
            attributes += f"<name>{product_tmpl.name}</name>"

            if product_tmpl.lazada_desc:
                if len(product_tmpl.lazada_desc) > 150 or len(product_tmpl.lazada_desc) < 25000:
                    raise UserError(_('Nama description minimal 150 dan maksimal 25000 karakter.'))
                attributes += f"<description>{product_tmpl.lazada_desc}</description>"

            if product_tmpl.lazada_brand_id:
                attributes += f"<brand>{product_tmpl.lazada_brand_id.name}</brand><brand_id>{product_tmpl.lazada_brand_id.lazada_brand_id}</brand_id>"

            if Hazmat:
                attributes += f"<Hazmat>{Hazmat}</Hazmat>"

            sku_list = ""
            product_tmpl_var_images = ""
            for variant in product_tmpl.product_variant_ids:
                lazada_product_var_image_ids = []
                if not (variant.default_code or variant.lazada_seller_sku):
                    raise UserError(_('Internal Reference atau Lazada Seller SKU per variant mohon di isi.'))
                package_content = ""
                if product_tmpl.lz_package_content:
                    package_content = f"<package_content>{product_tmpl.lz_package_content}</package_content>"

                if variant.lazada_product_var_image_ids:
                    for imgs in variant.lazada_product_var_image_ids:
                        if imgs.uri:
                            lazada_product_var_image_ids.append(imgs.uri)
                        else:
                            imgs_path = '/image/upload'
                            imgs_format = imgs.name.split('.')[-1]
                            imgs_bytes = base64.b64decode(imgs.image)
                            
                            imgs_params = {
                              'image': (imgs.name,imgs_bytes,imgs_format)
                            }
                            upload = company.lazada_sdk(url=url, request=imgs_path, params=imgs_params, method=method, access_token=access_token)
                            imgs_data = upload.body

                            if imgs_data.get('data') and imgs_data.get('data').get('image'):
                                imgs.write({
                                    'uri': imgs_data.get('data').get('image').get('url')
                                })
                                lazada_product_var_image_ids.append(imgs_data.get('data').get('image').get('url'))

                    
                    if lazada_product_var_image_ids:
                        for image in lazada_product_var_image_ids:
                            product_tmpl_var_images = product_tmpl_var_images + '<Image>' + image
                            product_tmpl_var_images = product_tmpl_var_images + '</Image>'
                    if product_tmpl_var_images:
                        product_tmpl_var_images = f"""<Images>
                            {product_tmpl_var_images}
                        </Images>"""
                attr_val = ""
                for value in variant.product_template_variant_value_ids:
                    attr_val += f"<{value.attribute_id.name}>{value.name}</{value.attribute_id.name}>"
                sku_list += f"""
                    <Sku>
                        <SellerSku>{variant.default_code or variant.lazada_seller_sku}</SellerSku>
                        <quantity>{int(variant.qty_available)}</quantity>
                        <price>{int(variant.lst_price)}</price>
                        <saleProp>
                            {attr_val}
                        </saleProp>
                        <package_height>{int(product_tmpl.lz_package_height)}</package_height>
                        <package_length>{int(product_tmpl.lz_package_length)}</package_length>
                        <package_width>{int(product_tmpl.lz_package_width)}</package_width>
                        <package_weight>{product_tmpl.lz_package_weight}</package_weight>{package_content}{product_tmpl_var_images}
                    </Sku>"""

            attr_variant = ""
            attr_list = ""
            attr_seq = 1
            for attr in product_tmpl.attribute_line_ids:
                attr_list += f"""<variation{attr_seq}>
                        <name>{attr.attribute_id.name}</name>
                        <hasImage>false</hasImage>
                        <customize>true</customize>
                        <options>
                            {''.join(['<option>'+x.name+'</option>' for x in attr.value_ids])}
                        </options>
                    </variation{attr_seq}>"""
                attr_seq += 1

            if attr_list:
                attr_variant = f"""<variation>
                        {attr_list}
                    </variation>"""
            xml_params = f"""<?xml version="1.0" encoding="UTF-8" ?>
            <Request>
                <Product>
                    <PrimaryCategory>{product_tmpl.lazada_category_id.lazada_category_id}</PrimaryCategory>
                    <AssociatedSku>{product_tmpl.lazada_seller_sku}</AssociatedSku>
                    {attr_variant}
                    {product_tmpl_images}
                    <Attributes>
                        {attributes}
                    </Attributes>
                    <Skus>
                        {sku_list}
                    </Skus>
                </Product>
            </Request>"""
            params = {
                'payload': xml_params
            }
            create = company.lazada_sdk(url=url, request=path, params=params, method=method, access_token=access_token)
            print(create.body)

    def action_confirm(self):
        context = self.env.context
        product_tmpl_obj = self.env['product.template']
        product_obj = self.env['product.product']
        history_obj = self.env['lazada.history.api']
        product_tmpl_ids = product_tmpl_obj.browse(context.get('active_id'))
        lazada_product_obj = self.env['lazada.product']
        lazada_product_var_obj = self.env['lazada.product.variant']
        company_obj = self.env['res.company']
        company = self.env.company
        shop = self.shop_id
        url = shop.region_id.url
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        method = 'POST'
        access_token = shop.access_token
        path = '/product/create'

        updated_count = 0
        affected_count = 0
        skipped_count = 0
        affected_list = ''
        skipped_list = ''
        timest = int(time.time())
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('jys_lazada.view_lazada_history_api_popup')
        view_id = view_ref and view_ref[1] or False

        if not shop:
            raise UserError(_('Please select the Shop.'))

        for product_tmpl in product_tmpl_ids:
            if not product_tmpl.is_lazada:
                raise UserError(_('Kolom Lazada Product mohon dicentang.'))

            lazada_product_id = lazada_product_obj.search([('shop_id', '=', shop.id), ('product_tmpl_id', '=', product_tmpl.id), ('product_tmpl_id.active', '=', True)], limit=1)
            if lazada_product_id:
                raise UserError(_('Produk ini sudah ada di Lazada.'))

            if len(product_tmpl.name) > 255:
                raise UserError(_('Nama produk melebihi 255 karakter.'))

            if not product_tmpl.lz_package_height or not product_tmpl.lz_package_width or not product_tmpl.lz_package_length or not product_tmpl.lz_package_weight:
                raise UserError(_('Mohon melengkapi data Package.'))

            if not (product_tmpl.lazada_category_id or product_tmpl.lazada_brand_id):
                raise UserError(_('Mohon Category dan Brand di isi.'))

            if product_tmpl.lazada_desc:
                if not(len(product_tmpl.lazada_desc) > 150 and len(product_tmpl.lazada_desc) < 25000):
                    raise UserError(_('Nama description minimal 150 dan maksimal 25000 karakter.'))

            sku_list = []

            dict_params = {
                'Request':{
                    'Product':{
                        'PrimaryCategory': str(product_tmpl.lazada_category_id.lazada_category_id),
                        'Attributes':{
                            'name': product_tmpl.name,
                            'description': product_tmpl.lazada_desc,
                        },
                        'Skus': {
                            'Sku': sku_list
                        }
                    }
                }
            }

            Hazmat = []
            if product_tmpl.is_battery:
                Hazmat.append('Battery')
            if product_tmpl.is_flammable:
                Hazmat.append('Flammable')
            if product_tmpl.is_liquid:
                Hazmat.append('Liquid')
            if product_tmpl.is_none:
                Hazmat.append('None')
            Hazmat = ','.join(Hazmat)
            if Hazmat:
                dict_params['Request']['Product']['Attributes']['Hazmat'] = Hazmat 

            lazada_product_image_ids = []
            for img in product_tmpl.lazada_product_image_ids:
                if img.uri:
                    lazada_product_image_ids.append(img.uri)
                else:
                    img_path = '/image/upload'
                    img_format = img.name.split('.')[-1]
                    img_bytes = base64.b64decode(img.image)
                    
                    img_params = {
                      'image': (img.name,img_bytes,img_format)
                    }
                    upload = company.lazada_sdk(url=url, request=img_path, params=img_params, method=method, access_token=access_token)
                    img_data = upload.body

                    if img_data.get('data') and img_data.get('data').get('image'):
                        img.write({
                            'uri': img_data.get('data').get('image').get('url')
                        })
                        lazada_product_image_ids.append(img_data.get('data').get('image').get('url'))

            if lazada_product_image_ids:
                dict_params['Request']['Product']['Images'] = {
                    'Image': lazada_product_image_ids
                }

            if product_tmpl.lazada_brand_id:
                dict_params['Request']['Product']['Attributes']['brand'] = product_tmpl.lazada_brand_id.name
                dict_params['Request']['Product']['Attributes']['brand_id'] = product_tmpl.lazada_brand_id.lazada_brand_id

            
            for variant in product_tmpl.product_variant_ids:
                lazada_product_var_image_ids = []
                if not (variant.default_code or variant.lazada_seller_sku):
                    raise UserError(_('Internal Reference atau Lazada Seller SKU per variant mohon di isi.'))

                if variant.lazada_product_var_image_ids:
                    for imgs in variant.lazada_product_var_image_ids:
                        if imgs.uri:
                            lazada_product_var_image_ids.append(imgs.uri)
                        else:
                            imgs_path = '/image/upload'
                            imgs_format = imgs.name.split('.')[-1]
                            imgs_bytes = base64.b64decode(imgs.image)
                            
                            imgs_params = {
                              'image': (imgs.name,imgs_bytes,imgs_format)
                            }
                            upload = company.lazada_sdk(url=url, request=imgs_path, params=imgs_params, method=method, access_token=access_token)
                            imgs_data = upload.body

                            if imgs_data.get('data') and imgs_data.get('data').get('image'):
                                imgs.write({
                                    'uri': img_data.get('data').get('image').get('url')
                                })
                                lazada_product_var_image_ids.append(img_data.get('data').get('image').get('url'))

                sku_params = {
                    'SellerSku': variant.default_code or variant.lazada_seller_sku,
                    'quantity': str(variant.qty_available),
                    'price': str(variant.lst_price),
                    'package_height': str(product_tmpl.lz_package_height),
                    'package_length': str(product_tmpl.lz_package_length),
                    'package_width': str(product_tmpl.lz_package_width),
                    'package_weight': str(product_tmpl.lz_package_weight),
                    'saleProp': {}

                }
                for value in variant.product_template_variant_value_ids:
                    sku_params['saleProp'][value.attribute_id.name] = value.name

                if product_tmpl.lz_package_content:
                    sku_params['package_content'] = product_tmpl.lz_package_content

                if lazada_product_var_image_ids:
                    sku_params['Images'] = {
                        'Image': lazada_product_var_image_ids
                    }
                sku_list.append(sku_params)

            attr_variant = {}
            attr_seq = 1
            for attr in product_tmpl.attribute_line_ids:
                attr_variant[f'variation{attr_seq}'] = {
                    'name': attr.attribute_id.name,
                    'hasImage': False,
                    'customize': True,
                    'options': {
                        'option':[x.name for x in attr.value_ids]
                    }
                }
                attr_seq += 1

                dict_params['Request']['Product']['variation'] = attr_variant 
            
            dict_params = json.dumps(dict_params)

            params = {
                'payload': dict_params
            }

            client = lazop.LazopClient(url, company.lazada_app_key ,company.lazada_app_secret)
            request = lazop.LazopRequest('/product/create')
            request.add_api_param('payload', dict_params)
            response = client.execute(request, access_token)
            body = response.body

            data = body.get('data')
            if data.get('item_id', False):
                lazada_product_obj.create({
                    'product_tmpl_id': product_tmpl.id,
                    'shop_id': shop.id,
                    'item_id': data.get('item_id')
                })
            for var in data.get('sku_list',[]):
                product_id = product_obj.search(['|',('default_code','=',var.get('seller_sku')),('lazada_seller_sku','=',var.get('seller_sku'))], limit=1)
                lazada_product_var_obj.create({
                    'shop_id': shop.id,
                    'variation_id': var.get('sku_id'),
                    'shop_sku': var.get('shop_sku'),
                    'seller_sku': var.get('seller_sku'),
                    'product_id': product_id.id
                })

            if body.get('code', '1') != '0':
                skipped_list += f"{product_tmpl.name}, {body.get('message','create failed.')}\n"
                skipped_count += 1

            if body.get('code', '1') == '0':
                affected_list += f"{product_tmpl.name}, {body.get('message','create success.')}\n"
                updated_count += 1

        history_id = history_obj.create({
            'name': 'Add Product',
            'shop_id': shop.id,
            'total_updated': updated_count,
            'total_skipped': skipped_count,
            'affected_list': affected_list,
            'skipped_list': skipped_list,
            'timestamp': timest,
            'state': 'success',
        }).id

        return {
            'name': 'History API',
            'type': 'ir.actions.act_window',
            'res_model': 'lazada.history.api',
            'res_id': history_id,
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
        }


