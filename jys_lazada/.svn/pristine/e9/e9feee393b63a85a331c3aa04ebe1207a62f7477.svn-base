import time
import json
import requests
import hashlib
import hmac
import PyPDF2 # type: ignore
import io
import base64
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse # type: ignore

class LazadaWarehouse(models.Model):
    _name = 'lazada.warehouse'
    _description = 'Lazada Warehouse'

    name = fields.Char('Name')
    code = fields.Char('code')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
