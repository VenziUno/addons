# -*- encoding: utf-8 -*-
import time
from odoo import api, fields, models, tools, _
from datetime import datetime

class LazadaOrder(models.Model):
    _name = 'lazada.order'
    _description = 'Lazada Orders'
    _order = 'updated_date desc, id desc'

    name = fields.Char('Order Number')
    statuses = fields.Char('Statuses')

    created_date = fields.Datetime(string='Created Date', default=fields.Datetime.now)
    updated_date = fields.Datetime(string='Updated Date', default=fields.Datetime.now)
    
    is_updated = fields.Boolean('Updated', default=False)

    shop_id = fields.Many2one('lazada.shop', 'Shop')
    partner_id = fields.Many2one('res.partner', 'Customer')
    partner_invoice_id = fields.Many2one('res.partner', 'Billing')
    partner_shipping_id = fields.Many2one('res.partner', 'Shipping')
    payment_method = fields.Char('Payment Method')
    price = fields.Float('Price')