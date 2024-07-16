import time
import json
import requests
import hashlib, hmac
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.parser import parse

import lazop
from requests.models import PreparedRequest
req = PreparedRequest()

class LazadaShop(models.Model):
    _name = "lazada.shop"
    _description = 'Lazada Shops'


    name = fields.Char('Name')
    oauth_code = fields.Char('Shop Auth Code')
    access_token = fields.Char('Shop Access Token')
    refresh_token = fields.Char('Shop Refresh Token')
    
    last_token_datetime = fields.Datetime('Last Updated Token')
    start_date = fields.Datetime('Start Date')
    lazada_commission = fields.Float('Commission')
    warehouse_id = fields.Many2one('stock.warehouse','Warehouse')

    @api.model
    def _default_company(self):
        context = dict(self._context or {})
        if context.get('active_id') and context.get('active_model') == 'res.company':
            company = self.env['res.company'].browse(context['active_id'])
        else:
            company = self.env.user.company_id
        return company.id
        
    region_id = fields.Many2one('lazada.region', 'Shop Region', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=_default_company)
    payment_journal_id = fields.Many2one('account.journal', 'Payment Journal')
    payment_method_id = fields.Many2one('account.payment.method', 'Payment Method')
    service_account_id = fields.Many2one('account.account', 'Service Account')

    _sql_constraints = [
        ('shop_uniq', 'unique(name,region_id)', 'The same Shop already exist!')
    ]


    @api.onchange('oauth_code')
    def _onchange_oauth_code(self):
        self.access_token = False
        self.refresh_token = False
        self.last_token_datetime = False

    def auth_shop_lazada(self):
        companys = self.env.company
        for company in companys:
            if not company.lazada_redirect_url:
                raise UserError(_('Please set your Redirect URL to authorize shop!'))
            if not company.lazada_app_key:
                raise UserError(_('Please set your App Key to authorize shop!'))
            if not company.lazada_app_secret:
                raise UserError(_('Please set your App Secret to authorize shop!'))

            url = 'https://auth.lazada.com/oauth/authorize'
            params = {
                'response_type': 'code',
                'force_auth': True,
                'redirect_uri': company.lazada_redirect_url,
                'client_id': company.lazada_app_key,
            }
            req.prepare_url(url, params)
            return {
                'type': 'ir.actions.act_url', 
                'url': req.url, 
                'target': 'new'
            }

    def generate_new_token(self):
        log_obj = self.env['lazada.history.api']
        for shop in self:
            company = shop.company_id
            url = 'https://auth.lazada.com/rest'
            if not shop.access_token or not shop.refresh_token:
                request = '/auth/token/create'
                params = {
                    'code': shop.oauth_code,
                }
            else:
                request = '/auth/token/refresh'
                params = {
                    'refresh_token': shop.refresh_token,
                }

            affected_count = 0
            skipped_count = 0
            affected_list = ''
            skipped_list = ''

            response = company.lazada_sdk(url=url, request=request, params=params)
            body = response.body
            
            if body.get('access_token') and body.get('refresh_token'):
                shop.write({
                    'access_token': body['access_token'],
                    'refresh_token': body['refresh_token'],
                    'last_token_datetime': datetime.now(),
                })
                
                affected_count = 1
                affected_list = body['access_token']

            else:
                skipped_count = 1
                skipped_list = shop.refresh_token or shop.oauth_code

            log_obj.create({
                'name': 'Get Token Access',
                'shop_id': shop.id,
                'total_affected': affected_count,
                'total_skipped': skipped_count,
                'affected_list': affected_list,
                'skipped_list': skipped_list,
            })

        return True

    def run_scheduler_lazada_update_token(self):
        shop_obj = self.env['lazada.shop']
        shops = shop_obj.search([])
        shops.generate_new_token()