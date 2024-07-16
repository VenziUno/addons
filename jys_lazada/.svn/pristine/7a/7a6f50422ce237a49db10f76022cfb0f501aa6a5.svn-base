import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse
import odoo.addons.decimal_precision as dp

class LazadaItem(models.Model):
    _name = "lazada.item"
    _description = 'Lazada Items'
    _order = 'create_date desc'

    name = fields.Char('Name')
    item_id = fields.Char('Item ID')
    shop_id = fields.Many2one('lazada.shop', 'Shop')
    updated_date = fields.Datetime(string='Updated Date', default=fields.Datetime.now)
    
    is_created = fields.Boolean('Created', default=False)
    is_updated = fields.Boolean('Updated', default=False)
    is_variant_updated = fields.Boolean('Variant Updated', default=False)
    is_done = fields.Boolean('Done', default=False)