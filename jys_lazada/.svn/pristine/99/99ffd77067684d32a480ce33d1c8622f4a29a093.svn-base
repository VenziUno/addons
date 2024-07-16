import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse
import odoo.addons.decimal_precision as dp

class LazadaRegion(models.Model):
    _name = "lazada.region"
    _description = 'Lazada Regions'

    name = fields.Char('Region')
    url = fields.Char('API Url')
    
    timezone = fields.Integer('Timezone', default=7)