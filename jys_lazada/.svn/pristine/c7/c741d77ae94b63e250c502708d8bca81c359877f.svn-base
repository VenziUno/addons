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

class LazadaUpdateProduct(models.TransientModel):
    _name = 'lazada.update.product'
    _description = 'Lazada Update Product'

    shop_ids = fields.Many2many('lazada.shop', 'lazada_update_product_shop_rel', 'update_wizard_id', 'shop_id', string='Shops')
    shop_id = fields.Many2one('lazada.shop','Shop')
    is_remove = fields.Boolean('Remove Product')
    is_price = fields.Boolean('Update Price')
    is_stock = fields.Boolean('Update Stock')
    is_image = fields.Boolean('Update Image')
    is_non_active = fields.Boolean('Non-Active Product')

    def update_product(self):
        context = self.env.context
        product_tmpl_obj = self.env['product.template']
        product_obj = self.env['product.product']
        history_obj = self.env['lazada.history.api']
        product_tmpl_ids = product_tmpl_obj.browse(context.get('active_ids'))
        lazada_product_obj = self.env['lazada.product']
        lazada_product_var_obj = self.env['lazada.product.variant']
        company_obj = self.env['res.company']
        company = self.env.company
        appkey = company.lazada_app_key
        appSecret = company.lazada_app_secret
        shop = self.shop_ids
        url = shop.region_id.url
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        method = 'POST'
        access_token = shop.access_token
        remove_path = '/product/remove'
        price_qty_path = '/product/price_quantity/update'
        img_path = '/images/set'
        nonactive_path = '/product/deactivate'

        updated_count = 0
        affected_count = 0
        skipped_count = 0
        affected_list = ''
        skipped_list = ''
        timest = int(time.time())
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('jys_lazada.view_lazada_history_api_popup')
        view_id = view_ref and view_ref[1] or False

        if not self.shop_ids:
            raise UserError(_('Please select the Shop.'))

        for shop in self.shop_ids:
            url = shop.region_id.url
            for product in product_tmpl_ids:
                lazada_product_id = lazada_product_obj.search([('shop_id','=',shop.id),('product_tmpl_id','=',product.id)], limit=1)
                if lazada_product_id:
                    if self.is_remove:
                        sku_id_list = []
                        for var in product.product_variant_ids:
                            lazada_product_var_id = lazada_product_var_obj.search([('shop_id','=',shop.id),('product_id','=',var.id)], limit=1)
                            sku_id_list.append(f"SkuId_{lazada_product_id.item_id}_{lazada_product_var_id.variation_id}")
                            lazada_product_var_id.unlink()
                        lazada_product_id.unlink()
                        sku_id_list = json.dumps(sku_id_list)
                        params = {
                            'sku_id_list': sku_id_list
                        }

                        remove = company.lazada_sdk(url=url, request=remove_path, params=params, method=method, access_token=access_token)
                        body = remove.body

                        if body.get('code', '1') != '0':
                            skipped_list += f"{product.name}, {body.get('message','remove product failed.')}\n"
                            skipped_count += 1

                        if body.get('code', '1') == '0':
                            affected_list += f"{product.name}, {body.get('message','remove product success.')}\n"
                            updated_count += 1

                        history_id = history_obj.create({
                            'name': 'Update Product',
                            'shop_id': shop.id,
                            'total_updated': updated_count,
                            'total_skipped': skipped_count,
                            'affected_list': affected_list,
                            'skipped_list': skipped_list,
                            'timestamp': timest,
                            'state': 'success' if updated_count > 0 else 'failed'
                        }).id
                    else:
                        if self.is_non_active:
                            product_xml = f"<Request><Product><ItemId>{lazada_product_id.item_id}</ItemId></Product></Request>"
                            params = {
                                'apiRequestBody': product_xml
                            }
                            stock = company.lazada_sdk(url=url, request=nonactive_path, params=params, method=method, access_token=access_token)
                            body = stock.body

                            if body.get('code', '1') != '0':
                                skipped_list += f"{product.name}, {body.get('message','update stock failed.')}\n"
                                skipped_count += 1

                            if body.get('code', '1') == '0':
                                affected_list += f"{product.name}, {body.get('message','update stock success.')}\n"
                                updated_count += 1

                            history_id = history_obj.create({
                                'name': 'Update Product',
                                'shop_id': shop.id,
                                'total_updated': updated_count,
                                'total_skipped': skipped_count,
                                'affected_list': affected_list,
                                'skipped_list': skipped_list,
                                'timestamp': timest,
                                'state': 'success' if updated_count > 0 else 'failed'
                            }).id
                        if self.is_stock:
                            sku_list = ""
                            for var in product.product_variant_ids:
                                lazada_product_var_id = lazada_product_var_obj.search([('shop_id','=',shop.id),('product_id','=',var.id)], limit=1)
                                sku_list += f"<Sku><ItemId>{lazada_product_id.item_id}</ItemId><SkuId>{lazada_product_var_id.variation_id}</SkuId><Quantity>{int(var.qty_available)}</Quantity></Sku>"
                            product_xml = f"<Request><Product><Skus>{sku_list}</Skus></Product></Request>"
                            params = {
                                'payload': product_xml
                            }
                            stock = company.lazada_sdk(url=url, request=price_qty_path, params=params, method=method, access_token=access_token)
                            body = stock.body

                            if body.get('code', '1') != '0':
                                skipped_list += f"{product.name}, {body.get('message','update stock failed.')}\n"
                                skipped_count += 1

                            if body.get('code', '1') == '0':
                                affected_list += f"{product.name}, {body.get('message','update stock success.')}\n"
                                updated_count += 1

                            history_id = history_obj.create({
                                'name': 'Update Product',
                                'shop_id': shop.id,
                                'total_updated': updated_count,
                                'total_skipped': skipped_count,
                                'affected_list': affected_list,
                                'skipped_list': skipped_list,
                                'timestamp': timest,
                                'state': 'success' if updated_count > 0 else 'failed'
                            }).id

                        if self.is_price:
                            sku_list = ""
                            for var in product.product_variant_ids:
                                lazada_product_var_id = lazada_product_var_obj.search([('shop_id','=',shop.id),('product_id','=',var.id)], limit=1)
                                sku_list += f"<Sku><ItemId>{lazada_product_id.item_id}</ItemId><SkuId>{lazada_product_var_id.variation_id}</SkuId><Price>{int(var.lst_price)}</Price></Sku>"
                            product_xml = f"<Request><Product><Skus>{sku_list}</Skus></Product></Request>"
                            params = {
                                'payload': product_xml
                            }
                            price = company.lazada_sdk(url=url, request=price_qty_path, params=params, method=method, access_token=access_token)
                            body = price.body

                            if body.get('code', '1') != '0':
                                skipped_list += f"{product.name}, {body.get('message','update price failed.')}\n"
                                skipped_count += 1

                            if body.get('code', '1') == '0':
                                affected_list += f"{product.name}, {body.get('message','update price success.')}\n"
                                updated_count += 1

                            history_id = history_obj.create({
                                'name': 'Update Product',
                                'shop_id': shop.id,
                                'total_updated': updated_count,
                                'total_skipped': skipped_count,
                                'affected_list': affected_list,
                                'skipped_list': skipped_list,
                                'timestamp': timest,
                                'state': 'success' if updated_count > 0 else 'failed'
                            }).id

                        if self.is_image:
                            sku_list = ""
                            for variant in product.product_variant_ids:
                                lazada_product_var_id = lazada_product_var_obj.search([('shop_id','=',shop.id),('product_id','=',variant.id)], limit=1)
                                product_tmpl_var_images = ""
                                lazada_product_var_image_ids = []
                                if not (variant.default_code or variant.lazada_seller_sku):
                                    raise UserError(_('Internal Reference atau Lazada Seller SKU per variant mohon di isi.'))
                                if not variant.lazada_product_var_image_ids:
                                    raise UserError(_(f'Gambar tidak ditemukan pada SKU: {variant.default_code or variant.lazada_seller_sku}.'))
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
                                        product_tmpl_var_images += f"<Image>{image}</Image>"
                                if product_tmpl_var_images:
                                    product_tmpl_var_images = f"<Images>{product_tmpl_var_images}</Images>"
                                sku_list += f"<Sku><SkuId>{lazada_product_var_id.variation_id}</SkuId>{product_tmpl_var_images}</Sku>"

                            product_xml = f"<?xml version='1.0' encoding='UTF-8' ?><Request><Product><Skus>{sku_list}</Skus></Product></Request>"
                            params = {
                                'payload': product_xml
                            }
                            price = company.lazada_sdk(url=url, request=img_path, params=params, method=method, access_token=access_token)
                            body = price.body

                            if body.get('code', '1') != '0':
                                skipped_list += f"{product.name}, {body.get('message','set images failed.')}\n"
                                skipped_count += 1

                            if body.get('code', '1') == '0':
                                affected_list += f"{product.name}, {body.get('message','set images success.')}\n"
                                updated_count += 1

                            history_id = history_obj.create({
                                'name': 'Update Product',
                                'shop_id': shop.id,
                                'total_updated': updated_count,
                                'total_skipped': skipped_count,
                                'affected_list': affected_list,
                                'skipped_list': skipped_list,
                                'timestamp': timest,
                                'state': 'success' if updated_count > 0 else 'failed'
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

