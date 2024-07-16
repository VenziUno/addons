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
	_name = 'tiktok.update.product'
	_description = 'JYS Tiktok Update Product'

	name = fields.Char('Name')
	shop_id = fields.Many2one('tiktok.shop','Shop')
	shop_ids = fields.Many2many('tiktok.shop', 'update_tiktok_id', 'shop_id', 'tiktok_update_product_rel', string='Shops')
	is_update_price = fields.Boolean('Update Prices')
	is_update_stock = fields.Boolean('Update Stocks')
	is_update_image = fields.Boolean('Update Images')
	is_update_status = fields.Selection([
		('active','Active'),
		('nonactive','Non-Active')
	], string='Update Status')
	is_delete_product = fields.Boolean('Delete Product')
	is_recover_product = fields.Boolean('Recover Deleted Product')

	def update_product(self):
		context = self.env.context
		product_tmpl_obj = self.env['product.template']
		product_obj = self.env['product.product']
		tiktok_product_obj = self.env['tiktok.product']
		tiktok_product_var_obj = self.env['tiktok.product.variant']
		history_obj = self.env['tiktok.history.api']
		company_obj = self.env['res.company']
		view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('jys_tiktok.view_tiktok_history_api_popup')
		view_id = view_ref and view_ref[1] or False

		product_ids = product_tmpl_obj.browse(context.get('active_ids'))
		company = self.env.company
		for shop in self.shop_ids:
			access_token = shop.tiktok_token
			tiktok_id = shop.shop_id
			chiper = str(shop.tiktok_chiper)
			domain = company.tiktok_api_domain
			app = company.tiktok_client_id
			key = company.tiktok_client_secret
			timest = int(time.time())
			sign = ''

			headers = {
				'x-tts-access-token': str(access_token), 
				"Content-type": "application/json"
			}

			updated_count = 0
			affected_count = 0
			skipped_count = 0
			affected_list = ''
			skipped_list = ''

			for product in product_ids:
				tiktok_product_id = tiktok_product_obj.search([('shop_id','=',shop.id),('product_tmpl_id','=',product.id)], limit=1)
				if tiktok_product_id:
					if self.is_recover_product:
						recover_params = {
							'product_ids': [tiktok_product_id.item_id]
						}
						url = domain+f"/product/202309/products/recover?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"
						sign = company_obj.cal_sign(url, key, headers, recover_params)
						url = domain+f"/product/202309/products/recover?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"

						res = requests.post(url, json=recover_params, headers=headers)
						values = res.json()
						if values.get('message') == None:
							skipped_list += f"{product.name}, {values.get('message','recover product failed.')}\n"
							skipped_count += 1

						if values.get('message') == 'Success':
							# product.write({'is_tiktok': False})
							affected_list += f"{product.name}, {values.get('message','recover product success.')} recover product\n"
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
					if self.is_delete_product:
						delete_params = {
							'product_ids': [tiktok_product_id.item_id]
						}
						url = domain+f"/product/202309/products?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"
						sign = company_obj.cal_sign(url, key, headers, delete_params)
						url = domain+f"/product/202309/products?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"

						res = requests.delete(url, json=delete_params, headers=headers)
						values = res.json()
						if values.get('message') == None:
							skipped_list += f"{product.name}, {values.get('message','delete product failed.')}\n"
							skipped_count += 1

						if values.get('message') == 'Success':
							# product.write({'is_tiktok': False})
							affected_list += f"{product.name}, {values.get('message','delete product success.')} delete product\n"
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
						if self.is_update_stock:
							inventory_params = {}
							skus_product = []
							for variant in product.product_variant_ids:
								variation_id = tiktok_product_var_obj.search([('shop_id','=',shop.id),('product_id','=',variant.id)], limit=1)
								if variation_id:
									skus_product.append({
										'id': variation_id.variation_id,
										'inventory': [{"quantity": int(variant.qty_available), "warehouse_id": product.tiktok_warehouse_id.warehouse_id}]
									})

							if not skus_product:
								raise UserError(_('Variant Not Found.'))
							inventory_params['skus'] = skus_product

							url = domain+f"/product/202309/products/{tiktok_product_id.item_id}/inventory/update?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"
							sign = company_obj.cal_sign(url, key, headers, inventory_params)
							url = domain+f"/product/202309/products/{tiktok_product_id.item_id}/inventory/update?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"

							res = requests.post(url, json=inventory_params, headers=headers)
							values = res.json()

							if values.get('message') == None:
								skipped_list += f"{product.name}, {values.get('message','update stock failed.')}\n"
								skipped_count += 1

							if values.get('message') == 'Success':
								affected_list += f"{product.name}, {values.get('message','update stock success.')} update stock\n"
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

						if self.is_update_price:
							price_params = {}
							skus_product = []
							for variant in product.product_variant_ids:
								variation_id = tiktok_product_var_obj.search([('shop_id','=',shop.id),('product_id','=',variant.id)], limit=1)
								if variation_id:
									skus_product.append({
										'id': variation_id.variation_id,
										'price': {
											'amount': str(variant.lst_price),
											'currency': 'IDR' if company.tiktok_state == 'Indonesia' else company.currency_id.name
										}
									})
							if not skus_product:
								raise UserError(_('Variant Not Found.'))
							price_params['skus'] = skus_product

							url = domain+f"/product/202309/products/{tiktok_product_id.item_id}/prices/update?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"
							sign = company_obj.cal_sign(url, key, headers, price_params)
							url = domain+f"/product/202309/products/{tiktok_product_id.item_id}/prices/update?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"

							res = requests.post(url, json=price_params, headers=headers)
							values = res.json()

							# if values.get('data') == None:
							# 	raise UserError(_(f"Info: {values.get('message')}\n."))
							if values.get('message') == None:
								skipped_list += f"{product.name}, {values.get('message','update price failed.')}\n"
								skipped_count += 1

							if values.get('message') == 'Success':
								affected_list += f"{product.name}, {values.get('message','update price success.')} update price\n"
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

						if self.is_update_image:
							img_path = '/product/202309/images/upload'
							img_sign = ''
							img_headers = {
								'x-tts-access-token': str(access_token)
							}
							image_params = {}

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

									if img_values.get('data'):
										img.write({'uri': img_values.get('data').get('uri')})
										tiktok_product_image_ids.append({'uri': img_values.get('data').get('uri')})

							image_params['main_images'] = tiktok_product_image_ids
							
							if tiktok_product_image_ids:
								image_params['size_chart'] = {
									'image': tiktok_product_image_ids[0]
								}

							url = domain+f"/product/202309/products/{tiktok_product_id.item_id}/partial_edit?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"
							sign = company_obj.cal_sign(url, key, headers, image_params)
							url = domain+f"/product/202309/products/{tiktok_product_id.item_id}/partial_edit?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"

							res = requests.post(url, json=image_params, headers=headers)
							values = res.json()

							if values.get('message') == None:
								skipped_list += f"{product.name}, {values.get('message','update image failed.')}\n"
								skipped_count += 1

							if values.get('message') == 'Success':
								affected_list += f"{product.name}, {values.get('message','update image success.')} update image\n"
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

							# if values.get('data') == None:
							# 	raise UserError(_(f"Info: {values.get('message')}\n."))

						if self.is_update_status:
							if self.is_update_status == 'nonactive':
								status_params = {
									'product_ids': [tiktok_product_id.item_id]
								}
								url = domain+f"/product/202309/products/deactivate?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"
								sign = company_obj.cal_sign(url, key, headers, status_params)
								url = domain+f"/product/202309/products/deactivate?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"

								res = requests.post(url, json=status_params, headers=headers)
								values = res.json()

								if values.get('message') == None:
									skipped_list += f"{product.name}, {values.get('message','update status non-active failed.')}\n"
									skipped_count += 1

								if values.get('message') == 'Success':
									# product.write({'is_tiktok': False})
									affected_list += f"{product.name}, {values.get('message','update status non-active success.')} update status non-active\n"
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

							if self.is_update_status == 'active':
								status_params = {
									'product_ids': [tiktok_product_id.item_id]
								}
								url = domain+f"/product/202309/products/activate?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"
								sign = company_obj.cal_sign(url, key, headers, status_params)
								url = domain+f"/product/202309/products/activate?app_key={app}&access_token={access_token}&sign={sign}&timestamp={timest}&shop_cipher={chiper}"

								res = requests.post(url, json=status_params, headers=headers)
								values = res.json()

								if values.get('message') == None:
									skipped_list += f"{product.name}, {values.get('message','update status active failed.')}\n"
									skipped_count += 1

								if values.get('message') == 'Success':
									# product.write({'is_tiktok': False})
									affected_list += f"{product.name}, {values.get('message','update status active success.')} update status active\n"
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
                        'res_model': 'tiktok.history.api',
                        'res_id': history_id,
                        'view_mode': 'form',
                        'view_id': view_id,
                        'target': 'new',
                    }			

				else:
					raise UserError(_(f"TikTok ItemId Not Found for this product [{product.name}]"))