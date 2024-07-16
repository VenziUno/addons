import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse
import odoo.addons.decimal_precision as dp
import base64
from PIL import Image
import io

class LazadaProduct(models.Model):
    _name = "lazada.product"
    _description = 'Lazada Products'

    name = fields.Char('Name')
    product_tmpl_id = fields.Many2one('product.template', 'Product')
    shop_id = fields.Many2one('lazada.shop', 'Shop')
    item_id = fields.Char('Item ID')

class LazadProductVariant(models.Model):
    _name = "lazada.product.variant"
    _description = 'Lazada Product Variants'

    name = fields.Char('Name')
    shop_sku = fields.Char('Shop SKU')
    seller_sku = fields.Char('Seller SKU')
    product_id = fields.Many2one('product.product', 'Product')
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id', store=True)
    shop_id = fields.Many2one('lazada.shop', 'Shop')
    variation_id = fields.Char('Variation ID')
    price = fields.Float('Price')

class LazadaProductImage(models.Model):
    _name = 'lazada.product.image'
    _description = 'Lazada Product Image'

    name = fields.Char('Name')
    product_tmpl_id = fields.Many2one('product.template', 'Product')
    product_id = fields.Many2one('product.product', 'Product Variant')
    shop_id = fields.Many2one('lazada.shop', 'Shop')
    attachment_id = fields.Many2one('ir.attachment', 'Attachment')
    image = fields.Binary(string='Image')
    image_id = fields.Integer('Image ID')
    uri = fields.Char('URI')
    image_ids = fields.One2many('lazada.product.image.variant','product_image_id','Variant Images')

    def is_valid_image(self, vals):
        supported_formats = ['jpeg','jpg','png','JPEG', 'JPG', 'PNG']
        
        min_pixels = 300
        max_pixels = 20000
        
        max_file_size = 5 * 1024 * 1024 #5MB
        
        try:
            image_data = base64.b64decode(vals['image'])
            image_size = len(image_data)
            
            if image_size > max_file_size:
                return False, "File size exceeds 5MB."
            
            image = Image.open(io.BytesIO(image_data))

            if image.format not in supported_formats:
                return False, "Unsupported image format. Must be JPG, JPEG, or PNG."
            
            width, height = image.size
            if not (min_pixels <= width <= max_pixels and min_pixels <= height <= max_pixels):
                return False, "Image dimensions out of range. Must be between 300x300 and 20000x20000 pixels."
            
            return True, "Image is valid."
        
        except Exception as e:
            return False, f"An error occurred: {str(e)}" 

    @api.model
    def create(self, vals):
        context = self.env.context
        if context.get('lazada_get_product'):
            return super(LazadaProductImage, self.with_context(context)).create(vals)
        if vals.get('name'):
            image = vals.get('name')
            image_format = image.split('.')
            if image_format[-1] not in ['jpeg','jpg','png','JPEG', 'JPG', 'PNG']:
                raise UserError(_('[%s], Unsupported image format. Must be JPG, JPEG, or PNG.')%(vals.get('name')))

            check = self.is_valid_image(vals)
            if not check[0]:
                raise UserError(_('[%s], %s')%(vals.get('name'), check[1]))
        return super(LazadaProductImage, self.with_context(context)).create(vals)

    def unlink(self):
        for dels in self:
            attachment_id = self.env['ir.attachment'].browse(dels.image_id)
            if attachment_id.datas:
                attachment_id.unlink()
        return super(LazadaProductImage, self).unlink()


class LazadaProductImageVariant(models.Model):
    _name = 'lazada.product.image.variant'
    _description = 'Lazada Product Image Variant'

    name = fields.Char(string="Description")
    image = fields.Binary(string="Image", attachment=True)
    product_image_id = fields.Many2one('lazada.product.image','Product Image')
    product_id = fields.Many2one('product.product', string="Product Variant")
    image_id = fields.Integer('Image ID')
    uri = fields.Char('URI')

    def is_valid_image(self, vals):
        supported_formats = ['jpeg','jpg','png','JPEG', 'JPG', 'PNG']
        
        min_pixels = 300
        max_pixels = 20000
        
        max_file_size = 5 * 1024 * 1024 #5MB
        
        try:
            image_data = base64.b64decode(vals['image'])
            image_size = len(image_data)
            
            if image_size > max_file_size:
                return False, "File size exceeds 5MB."
            
            image = Image.open(io.BytesIO(image_data))
            
            if image.format not in supported_formats:
                return False, "Unsupported image format. Must be JPG, JPEG, or PNG."
            
            width, height = image.size
            if not (min_pixels <= width <= max_pixels and min_pixels <= height <= max_pixels):
                return False, "Image dimensions out of range. Must be between 300x300 and 20000x20000 pixels."
            
            return True, "Image is valid."
        
        except Exception as e:
            return False, f"An error occurred: {str(e)}" 

    @api.model
    def create(self, vals):
        context = self.env.context
        if context.get('lazada_get_product'):
            return super(LazadaProductImageVariant, self.with_context(context)).create(vals)
        if vals.get('name'):
            image = vals.get('name')
            image_format = image.split('.')
            if image_format[-1] not in ['jpeg','jpg','png','JPEG', 'JPG', 'PNG']:
                raise UserError(_('[%s], Unsupported image format. Must be JPG, JPEG, or PNG.')%(vals.get('name')))

            check = self.is_valid_image(vals)
            if not check[0]:
                raise UserError(_('[%s], %s')%(vals.get('name'), check[1]))
        return super(LazadaProductImageVariant, self.with_context(context)).create(vals)

    def unlink(self):
        for dels in self:
            attachment_id = self.env['ir.attachment'].browse(dels.image_id)
            if attachment_id.datas:
                attachment_id.unlink()
        return super(LazadaProductImageVariant, self).unlink()
