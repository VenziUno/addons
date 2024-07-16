import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse
import odoo.addons.decimal_precision as dp

class ProductTemplate(models.Model):
	_inherit = "product.template"

	is_lazada_auto_stock = fields.Boolean('Auto Stock', default=False, copy=False)
	is_sync_lazada = fields.Boolean('Sync to Lazada', default=False, copy=False)
	is_lazada = fields.Boolean('Lazada Product', default=False, copy=False)
	lazada_seller_sku = fields.Char('Lazada Seller SKU', copy=False)

	is_battery = fields.Boolean('Battery', default=False, copy=False)
	is_flammable = fields.Boolean('Flammable', default=False, copy=False)
	is_liquid = fields.Boolean('Liquid', default=False, copy=False)
	is_none = fields.Boolean('None', default=False, copy=False)

	lazada_brand_id = fields.Many2one('lazada.brand', 'Lazada Brand')
	lazada_category_id = fields.Many2one('lazada.category', 'Lazada Category')
	lazada_desc = fields.Text('Lazada Description')
	lazada_product_ids = fields.One2many('lazada.product', 'product_tmpl_id', 'Lazada Products')
	lazada_attribute_line_ids = fields.One2many('lazada.attribute.line', 'product_tmpl_id', 'Lazada Attributes')
	lazada_product_image_ids = fields.One2many('lazada.product.image', 'product_tmpl_id', 'Lazada Images')
	attachment_id = fields.Many2one('ir.attachment', 'Attachments')
	upload_product_lz_image_ids = fields.Many2many('ir.attachment', 'res_lazada_ir_attachment_relation','res_id', 'attachment_id', string="Upload")

	lz_package_height = fields.Float('Package Height')
	lz_package_width = fields.Float('Package Width')
	lz_package_length = fields.Float('Package Length')
	lz_package_weight = fields.Float('Package Weight')
	lz_package_content = fields.Char('Package Details')

	@api.model
	def create(self, vals):
		context = self.env.context
		result = super(ProductTemplate, self.with_context(context)).create(vals)
		if vals.get('upload_product_lz_image_ids'):
			for x in vals.get('upload_product_lz_image_ids'):
				if x[0] == 4:
					attachment_id = self.env['ir.attachment'].browse(x[1])
					if attachment_id.datas:
						self.env['lazada.product.image'].create({
							'image_id': x[1],
							'image': attachment_id.datas,
							'name': attachment_id.name,
							'product_tmpl_id': result.id
						})
				if x[0] == 3:
					lazada_img_id = self.env['lazada.product.image'].search([('image_id','=',x[1])]).unlink()

		return result

	def write(self, vals):
		context = self.env.context
		result = super(ProductTemplate, self.with_context(context)).write(vals)
		if vals.get('upload_product_lz_image_ids'):
			for x in vals.get('upload_product_lz_image_ids'):
				if x[0] == 4:
					attachment_id = self.env['ir.attachment'].browse(x[1])
					if attachment_id.datas:
						self.env['lazada.product.image'].create({
							'image_id': x[1],
							'image': attachment_id.datas,
							'name': attachment_id.name,
							'product_tmpl_id': self.id
						})
				if x[0] == 3:
					lazada_img_id = self.env['lazada.product.image'].search([('image_id','=',x[1])]).unlink()

		return result

	def action_delete_all_lazada_img(self):
		for dels in self:
			if dels.lazada_product_image_ids:
				dels.lazada_product_image_ids.unlink()

	def unlink(self):
		for dels in self:
			dels.lazada_product_ids.unlink()
			dels.action_delete_all_lazada_img()
		return super(ProductTemplate, self).unlink()

	def action_open_lz_delete_confirmation_wizard(self):
		return {
			'type': 'ir.actions.act_window',
			'name': 'Delete Confirmation',
			'res_model': 'lz.delete.confirmation.wizard',
			'view_mode': 'form',
			'target': 'new',
			'context': {
				'active_id': self.id,
				'default_name': self.name,
			},
		}


class ProductProduct(models.Model):
	_inherit = "product.product"

	lazada_product_variant_ids = fields.One2many('lazada.product.variant', 'product_id', 'Lazada Product Variants')
	lazada_seller_sku = fields.Char('Lazada Seller SKU', copy=False)
	is_sync_lazada = fields.Boolean('Sync to Lazada', copy=False)
	
	adjust_qty = fields.Float('Adjust Quantity')
	lazada_product_var_image_ids = fields.One2many('lazada.product.image.variant', 'product_id', 'lazada Variant Images')

	attachment_id = fields.Many2one('ir.attachment', 'Attachments')
	upload_product_var_lz_image_ids = fields.Many2many('ir.attachment', 'res_lazada_var_ir_attachment_relation','res_id', 'attachment_id', string="Upload")

	@api.model
	def create(self, vals):
		context = self.env.context
		result = super(ProductProduct, self.with_context(context)).create(vals)
		if vals.get('upload_product_var_lz_image_ids'):
			for x in vals.get('upload_product_var_lz_image_ids'):
				if x[0] == 4:
					attachment_id = self.env['ir.attachment'].browse(x[1])
					if attachment_id.datas:
						self.env['lazada.product.image.variant'].create({
							'image_id': x[1],
							'image': attachment_id.datas,
							'name': attachment_id.name,
							'product_id': result.id
						})
				if x[0] == 3:
					lazada_img_id = self.env['lazada.product.image.variant'].search([('image_id','=',x[1])]).unlink()

		return result

	def write(self, vals):
		context = self.env.context
		result = super(ProductProduct, self.with_context(context)).write(vals)
		if vals.get('upload_product_var_lz_image_ids'):
			for x in vals.get('upload_product_var_lz_image_ids'):
				if x[0] == 4:
					attachment_id = self.env['ir.attachment'].browse(x[1])
					if attachment_id.datas:
						self.env['lazada.product.image.variant'].create({
							'image_id': x[1],
							'image': attachment_id.datas,
							'name': attachment_id.name,
							'product_id': self.id
						})
				if x[0] == 3:
					lazada_img_id = self.env['lazada.product.image.variant'].search([('image_id','=',x[1])]).unlink()

		return result

	def action_delete_all_lazada_var_img(self):
		for dels in self:
			if dels.lazada_product_var_image_ids:
				dels.lazada_product_var_image_ids.unlink()

	def unlink(self):
		for dels in self:
			dels.lazada_product_variant_ids.unlink()
			dels.action_delete_all_lazada_var_img()
		return super(ProductProduct, self).unlink()

	def action_open_lz_delete_confirmation_wizard(self):
		return {
			'type': 'ir.actions.act_window',
			'name': 'Delete Confirmation',
			'res_model': 'lz.delete.confirmation.wizard',
			'view_mode': 'form',
			'target': 'new',
			'context': {
				'active_id': self.id,
				'default_name': self.name,
			},
		}

class ProductAttribute(models.Model):
	_inherit = "product.attribute"

	lazada_attribute_id = fields.Many2one('lazada.attribute', 'Lazada Attribute')
	lazada_category_id = fields.Many2one('lazada.category', 'Lazada Category', related='lazada_attribute_id.category_id', store=True)
