import time
import json
import requests
import hashlib
import hmac
import PyPDF2 # type: ignore
import io
import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.parser import parse # type: ignore

class LazadaShippingLabel(models.TransientModel):
    _name = "lazada.shipping.label"
    _description = "Lazada Shipping Label"

    name = fields.Char('Name')

    def print_label_lz(self):
        context = self.env.context
        company = self.env.company
        sale_obj = self.env['sale.order']
        picking_obj = self.env['stock.picking']
        timest = int(time.time())
        label_url = []
        alr_print = ''
        for pick in picking_obj.browse(context.get('active_ids')):
            url = 'https://api.lazada.co.id/rest'
            method = 'GET'
            sale_id = pick.sale_id
            access_token = sale_id.lazada_shop_id.access_token
            items_request = '/order/items/get'
            items_params = {
                'order_id': pick.sale_id.lazada_ordersn,
            }
            items_response = company.action_call_lazada_api(url=url, request=items_request, params=items_params, method=method, access_token=access_token)
            values = items_response.body
            try:
                package_id = values.get('data')[0].get('package_id')
            except:
                package_id = False
                continue

            if package_id:
                package_request = '/order/package/document/get'
                params_pack = {
                    'doc_type': 'PDF',
                    'print_item_list': True,
                    'packages': [{'package_id':package_id}]
                }
                params_pack = json.dumps(params_pack)
                package_params = {'getDocumentReq': params_pack}
                package_response = company.action_call_lazada_api(url=url, request=package_request, params=package_params, access_token=access_token)
                package_values = package_response.body
                try:
                    url = package_values.get('result').get('data').get('pdf_url')
                    label_url.append(url)
                    pick.write({'is_shipping_printed': True,'date_print_shipped': fields.Datetime.now()})
                except:
                    alr_print += str(package_values)+'\n'
                    continue
            

        pdf_writer = PyPDF2.PdfFileWriter()
        if label_url:
            for url in label_url:
                response = requests.get(url)
                pdf = PyPDF2.PdfFileReader(io.BytesIO(response.content))
                for page_num in range(pdf.getNumPages()):
                    page = pdf.getPage(page_num)
                    pdf_writer.addPage(page)

            pdf_bytes = io.BytesIO()
            pdf_writer.write(pdf_bytes)
            pdf_bytes.seek(0)

            pdf_binary = pdf_bytes.getvalue()
            pdf_base64 = base64.b64encode(pdf_binary).decode('utf-8')
            file_name = 'Lazada-'+(datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H_%M_%S')+'.pdf'
            module_rec = self.env['lazada.shipping.label.pdf'].create(
                {'name': file_name, 'pdf_file': pdf_base64})
            return {'name': _('PDF File'),
                'res_id': module_rec.id,
                "view_mode": 'form',
                'res_model': 'lazada.shipping.label.pdf',
                'type': 'ir.actions.act_window',
                'target': 'new'}
        else:
            raise UserError(alr_print)

class LazadaShippingLabelPDF(models.TransientModel):
    _name = 'lazada.shipping.label.pdf'
    _description = "Lazada Shipping Label PDF"

    name = fields.Char('Name')
    pdf_file = fields.Binary('Click On Download Link To Download \
        PDF', readonly=True)

    def action_back(self):
        return {'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'lazada.shipping.label',
            'target': 'new'}

