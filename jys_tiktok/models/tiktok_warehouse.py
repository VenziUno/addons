from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class TiktokWarehouse(models.Model):
    _name = 'tiktok.warehouse'
    _description = 'Tiktok Warehouse'

    name = fields.Char('Name')
    warehouse_id = fields.Char('Warehouse ID')
    address = fields.Char('Address')