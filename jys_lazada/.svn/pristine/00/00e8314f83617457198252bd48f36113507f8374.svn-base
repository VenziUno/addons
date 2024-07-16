import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse
import odoo.addons.decimal_precision as dp

class LazadaFinance(models.Model):
    _name = "lazada.finance"
    _description = 'Lazada Finances'
    _order = 'transaction_date desc'

    name = fields.Char('Order No')
    transaction_type = fields.Char('Transaction Type')
    transaction_date = fields.Date('Transaction Date')
    payment_ref = fields.Char('Payment Ref')
    description = fields.Char('Description')
    transaction_number = fields.Char('Transaction Number')

    amount = fields.Float('Amount', digits=dp.get_precision('Product Price'))
    wht_amount = fields.Float('WHT Amount', digits=dp.get_precision('Product Price'))
    vat_amount = fields.Float('VAT Amount', digits=dp.get_precision('Product Price'))
    
    state = fields.Selection([('not paid', 'Not Paid'), ('paid', 'Paid')], 'Paid Status')
    is_updated = fields.Boolean('Updated', default=False)
    shop_id = fields.Many2one('lazada.shop', 'Shop')