import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    is_lazada = fields.Boolean('Lazada Logistic', default=False)
    is_cod = fields.Boolean('COD')
    is_default = fields.Boolean('Is Default')
    is_api_integration = fields.Boolean('Is API Integration')
    lazada_logisctic_id = fields.Many2one('lazada.logistic','Lazada Logistic')