import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse
import odoo.addons.decimal_precision as dp

class SaleOrder(models.Model):
    _inherit = "sale.order"

    lazada_shop_id = fields.Many2one('lazada.shop', 'Lazada Shop', copy=False)

    is_lazada_order = fields.Boolean('Lazada Order', default=False, copy=False)
    is_lazada_return = fields.Boolean('Lazada Returned', default=False, copy=False)
    is_lazada_cod = fields.Boolean('Lazada Returned', default=False, copy=False)
    lazada_cod_amount = fields.Float('COD Amount')
    
    lazada_ordersn = fields.Char('Lazada Order Number', copy=False)
    lazada_tracking_no = fields.Char('Lazada Tracking Number', copy=False)

    slowest_delivery_date = fields.Datetime('Slowest Delivery Date')
    lz_shipping_provider_type = fields.Char('Shipping Provider Type')

    _sql_constraints = [
        ('lazada_ordersn_uniq', 'unique(lazada_ordersn)', 'You cannot have more than one order with the same Lazada Serial Number!')
    ]