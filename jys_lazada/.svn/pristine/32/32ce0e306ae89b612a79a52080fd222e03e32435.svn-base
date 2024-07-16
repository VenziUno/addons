import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class ResPartner(models.Model):
    _inherit = "res.partner"

    is_lazada_partner = fields.Boolean('Lazada Partner', default=False, copy=False)