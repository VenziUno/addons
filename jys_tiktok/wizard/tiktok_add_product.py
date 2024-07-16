import ast
import json
import requests
import time
import hashlib
import hmac
import math
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime, timedelta
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError

class TiktokAddProduct(models.TransientModel):
	_name = 'tiktok.add.product'
	_description = 'JYS Tiktok Add Product'

	name = fields.Char('Name')
	shop_id = fields.Many2one('tiktok.shop','Shop')

	def add_product(self):
		context = self.env.context
		product_tmpl_obj = self.env['product.template']
		product_obj = self.env['product.product']
		product = product_tmpl_obj.browse(context.get('active_id'))
		tiktok_product_obj = self.env['tiktok.product']
		tiktok_product_var_obj = self.env['tiktok.product.variant']
		company_obj = self.env['res.company']
		company = self.env.company
		shop = self.shop_id
		access_token = shop.tiktok_token
		tiktok_id = shop.shop_id
		chiper = str(shop.tiktok_chiper)
		domain = company.tiktok_api_domain
		app = company.tiktok_client_id
		key = company.tiktok_client_secret
		timest = int(time.time())
		sign = ''
		path = "/product/202309/products"

		headers = {
			'x-tts-access-token': str(access_token), 
			"Content-type": "application/json"
		}

		img_path = '/product/202309/images/upload'
		img_sign = ''
		img_headers = {
			'x-tts-access-token': str(access_token)
		}

		create_params = {}

		if not product.tiktok_description:
			raise UserError(_('Please fill TikTok Description.'))
		if not (len(product.tiktok_description) > 300 and len(product.tiktok_description) < 10000):
			raise UserError(_('Please fill in the description with a minimum of 300 characters and a maximum of 10000 characters.'))

		create_params['description'] = product.tiktok_description

		if not product.tiktok_category_id:
			raise UserError(_('Please fill TikTok Category.'))

		create_params['category_id'] = str(product.tiktok_category_id.tiktok_category_id)

		if product.tiktok_brand_id:
			create_params['brand_id'] = str(product.tiktok_brand_id.brand_id)

		if not product.tiktok_product_image_ids:
			raise UserError(_('Please upload Images.'))
		if not (len(product.tiktok_product_image_ids) >= 1 and len(product.tiktok_product_image_ids) <= 9):
			raise UserError(_('Please upload image minimum 1 image and maximum 9 image.'))

		tiktok_product_image_ids = []
		for img in product.tiktok_product_image_ids:
			if img.uri:
				tiktok_product_image_ids.append({'uri':img.uri})
			else:
				img_format = img.name.split('.')[-1]
				img_type = f"image/{img_format}"
				img_encode = base64.b64decode(img.image)

				image = Image.open(BytesIO(img_encode))
				width, height = image.size
				new_edge_length = min(width, height)
				left = (width - new_edge_length) / 2
				top = (height - new_edge_length) / 2
				right = (width + new_edge_length) / 2
				bottom = (height + new_edge_length) / 2

				cropped_image = image.crop((left, top, right, bottom))
				buffer = BytesIO()
				cropped_image.save(buffer, format="JPEG")
				cropped_image_data = buffer.getvalue()

				files = {
				  'data': (img.name, cropped_image_data, img_type)
				}
				img_url = domain+img_path+f"?app_key={app}&access_token={access_token}&sign={img_sign}&timestamp={timest}"
				img_sign = company_obj.cal_sign(img_url, key, img_headers)
				img_url = domain+img_path+f"?app_key={app}&access_token={access_token}&sign={img_sign}&timestamp={timest}"
				img_res = requests.post(img_url, headers=img_headers, files=files)
				img_values = img_res.json()

				print(img_values,'VALUES===')
				if img_values.get('data'):
					img.write({'uri': img_values.get('data').get('uri')})
					tiktok_product_image_ids.append({'uri': img_values.get('data').get('uri')})

		create_params['main_images'] = tiktok_product_image_ids
		if not (len(product.name) > 25 and len(product.name) < 255):
			raise UserError(_('Please fill in the name Product with a minimum of 25 characters and a maximum of 255 characters.'))
		create_params['title'] = product.name
		if tiktok_product_image_ids:
			create_params['size_chart'] = {
				'image': tiktok_product_image_ids[0]
			}

		if product.pack_dimension_unit and product.tiktok_height and product.tiktok_width and product.tiktok_length:
			create_params['package_dimensions'] = {
				'height': product.tiktok_height,
				'length': product.tiktok_length,
				'unit': product.pack_dimension_unit,
				'width': product.tiktok_width
			}

		if not product.pack_weight_unit:
			raise UserError(_('Please fill Package Weight.'))

		create_params['package_weight'] = {
			'value': product.pack_weight_value,
			'unit': product.pack_weight_unit
		}

		skus_product = []
		for prod in product.product_variant_ids:
			sales_attributes = []
			for val in prod.product_template_variant_value_ids:
				sales_attributes.append({
					'name': val.attribute_id.name,
					'value_name': val.product_attribute_value_id.name,
				})
			skus_product.append({
				'sales_attributes': sales_attributes,
				'inventory': [{"quantity": int(prod.qty_available), "warehouse_id": product.tiktok_warehouse_id.warehouse_id}],
				'price': {
					'amount': str(prod.lst_price),
					'currency': company.currency_id.name
				},
				'seller_sku': prod.tiktok_variation_sku
			})

		create_params['skus'] = skus_product




		url = domain+path+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"
		sign = company_obj.cal_sign(url, key, headers, create_params)
		url = domain+path+f"?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"

		res = requests.post(url, json=create_params, headers=headers)
		values = res.json()

		if not values.get('data'):
			raise UserError(_(f"Info: {values.get('message')}\n."))
		if values.get('data'):
			data = values.get('data')
			tiktok_product_obj.create({
				'shop_id': shop.id,
				'item_id': data.get('product_id'),
				'product_tmpl_id': product.id
			})

			for variant in data.get('skus',[]):
				product_var = product_obj.search([('tiktok_variation_sku','=',variant.get('seller_sku'))], limit=1)
				if product_var:
					tiktok_product_var_obj.create({
						'shop_id': shop.id,
						'variation_id': variant.get('id'),
						'product_id': product_var.id
					})

		# if values.get('message') == 'Success':
		# 	return {
	    #         'warning': {
	    #         	'title': _('Info'),
	    #         	'message': _("Success add product to TikTok.")
	    #         },
	    #     }
