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

class LazadaLogistic(models.Model):
    _name = 'lazada.logistic'
    _description = 'Lazada Logistic'

    name = fields.Char('Name')
    is_cod = fields.Boolean('COD')
    is_default = fields.Boolean('Is Default')
    is_api_integration = fields.Boolean('Is API Integration')