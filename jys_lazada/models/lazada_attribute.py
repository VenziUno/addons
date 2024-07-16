from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class LazadaAttribute(models.Model):
    _name = 'lazada.attribute'
    _description = 'Lazada Attribute'

    name = fields.Char('Name')
    lazada_name = fields.Char('Lazada Name')
    input_type = fields.Char('Input Type')
    attribute_type = fields.Char('Attribute Type')
    is_sale_prop = fields.Boolean('Sale Prop', default=False)
    is_key_prop = fields.Boolean('Key Prop', default=False)
    is_mandatory = fields.Boolean('Mandatory', default=False)
    value_ids = fields.One2many('lazada.attribute.value', 'attribute_id', 'Values')
    category_id = fields.Many2one('lazada.category', 'Category')

class LazadaAttributeValue(models.Model):
    _name = 'lazada.attribute.value'
    _description = 'Lazada Attribute Value'

    name = fields.Char('Name')
    attribute_id = fields.Many2one('lazada.attribute', 'Attribute')
    
class LazadaAttributeLine(models.Model):
    _name = 'lazada.attribute.line'
    _description = 'Lazada Attribute line'

    name = fields.Char('Name')
    value = fields.Char('Value')
    input_type = fields.Char(related='attribute_id.input_type', string='Input Type', store=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product')
    attribute_id = fields.Many2one('lazada.attribute', 'Attribute')
    value_id = fields.Many2one('lazada.attribute.value', 'Value Selection')
    lazada_category_id = fields.Many2one('lazada.category' ,'Lazada Category', store=True)
    is_mandatory = fields.Boolean(related='attribute_id.is_mandatory', string='Mandatory', store=True)

    