import ast
import json
import time
import re
import base64
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from dateutil.parser import parse

class LazadaGetOrder(models.TransientModel):
    _name = "lazada.get.order"
    _description = 'Lazada Get Orders'

    start_date = fields.Datetime('Start Date')
    shop_id = fields.Many2one('lazada.shop', 'Shop')

    is_synced = fields.Boolean('Synced', default=False)
    is_continue = fields.Boolean('Continue Last Sync Date', default=False)

    @api.onchange('shop_id')
    def onchange_shop_id(self):
        self.is_synced = False
        self.is_continue = False
        self.start_date = False
        log_obj = self.env['lazada.history.api']
        last_log_id = log_obj.search([('name', '=', 'Get Orders List'), ('shop_id', '=', self.shop_id.id), ('state', 'in', ['partial', 'success'])], limit=1)
        if last_log_id:
            self.is_synced = True
            self.is_continue = True
            self.start_date = False

    def action_confirm(self):
        date_now = time.strftime('%Y-%m-%d %H:%M:%S')
        context = dict(self._context or {})
        company_obj = self.env['res.company']
        product_obj = self.env['product.product']
        product_tmpl_obj = self.env['product.template']
        partner_obj = self.env['res.partner']
        carrier_obj = self.env['delivery.carrier']
        sale_obj = self.env['sale.order']
        line_obj = self.env['sale.order.line']
        picking_obj = self.env['stock.picking']
        return_obj = self.env['stock.return.picking']
        invoice_obj = self.env['account.move']
        inv_line_obj = self.env['account.move.line']
        payment_obj = self.env['account.payment']
        register_obj = self.env['account.payment.register']
        method_line_obj = self.env['account.payment.method.line']
        order_obj = self.env['lazada.order']
        log_obj = self.env['lazada.history.api']
        # update_obj = self.env['lazada.update.product']
        lazada_product_obj = self.env['lazada.product']
        lazada_variant_obj = self.env['lazada.product.variant']
        data = self
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('jys_lazada.view_lazada_history_api_popup')
        view_id = view_ref and view_ref[1] or False

        if not data.shop_id:
            raise UserError(_('Please select your shop!'))

        shop = data.shop_id
        company = shop.company_id
        company_id = company.id
        timest = int(time.time())

        if not shop.payment_journal_id:
            raise UserError(_('Please fill your shop\'s Payment Journal!'))
        if not shop.payment_method_id:
            raise UserError(_('Please fill your shop\'s Payment Method!'))
        if not company.lazada_commission_product_id:
            raise UserError(_('Please fill your Lazada Commission Product!'))
        if not shop.start_date:
            raise UserError(_('Please fill in the Start Date for get order.'))
        if not company.lazada_logistic_product_id:
            raise UserError(_('Please fill your Lazada Delivery Product!'))

        def cancel_order(sale):
            is_cancel = False

            for inv in sale.invoice_ids:
                if inv.state not in ['cancel'] and inv.pament_state not in ['paid']:
                    inv.button_cancel()

            for picking in sale.picking_ids:
                if picking.picking_type_id.code == 'outgoing':
                    if picking.state == 'done':
                        is_cancel = True
                        if not picking.is_returned:
                            if not picking.is_returned:
                                default_data = return_obj.with_context(active_ids=[picking.id], active_id=picking.id).default_get(['move_dest_exists', 'original_location_id', 'product_return_moves', 'parent_location_id', 'location_id'])
                                return_wiz = return_obj.with_context(active_ids=[picking.id], active_id=picking.id).create(default_data)
                                return_wiz.product_return_moves.write({'to_refund': True}) # Return only 2
                                res = return_wiz.create_returns()
                                return_pick = picking_obj.browse(res['res_id'])
                                
                                if return_pick.show_check_availability == True:
                                    wiz_act = return_pick.with_context(confirm_from_wizard=True).action_assign()
                                    wiz_act = return_pick.with_context(confirm_from_wizard=True).action_done()
                                
                                else:
                                    wiz_act = return_pick.with_context(confirm_from_wizard=True).button_validate()
                                    wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
                                    wiz.with_context(confirm_from_wizard=True).process()

                                picking.write({
                                    'is_returned': True    
                                })
                        else:

                            if picking.state != 'cancel':
                                picking.action_cancel()

            if is_cancel:
                cr.execute("""
                    UPDATE sale_order SET state = 'cancel' WHERE id = %s
                """ % sale.id)

            else:            
                sale.action_cancel()

        def rts_order(sale, order):
            if sale.state in ('draft', 'sent'):
                confirm_context = context.copy()
                confirm_context.update(is_lazada_confirm=True)
                sale.with_context(confirm_context).action_confirm()

                date_order_create = order['created_at']
                if sale.date_order != date_order_create:
                    sale.write({'date_order': date_order_create})

        def lazada_ship(sale, order):
            ship_context = context.copy()
            ship_context.update(is_lazada_ship=True)
            ship_context.update(confirm_from_wizard=True)

            for picking in sale.picking_ids:
                if picking.state not in ('draft', 'cancel', 'done'):
                    if picking.show_check_availability:
                        picking.with_context(ship_context).action_assign()
                    picking.with_context(ship_context).button_validate()

        def create_invoice_order(sale, order):
            if sale.invoice_ids:
                for invoice in sale.invoice_ids:
                    if invoice.state == 'cancel':
                        invoice_id = sale._create_invoices()
                    else:
                        invoice_id = invoice
            else:
                invoice_id = sale._create_invoices()

            invoice = invoice_obj.browse(invoice_id.id)
            invoice.write({
                'invoice_date': sale.date_order,
                'is_lazada': True,
            })

            if invoice.state not in ['posted', 'cancel']:
                invoice.action_post()
            
            return invoice_id

        def fulfill_pack(sale, order_item_ids, order_number):
            if sale:
                try:
                    ship_url = '/order/shipment/providers/get'
                    pack_url = '/order/fulfill/pack'
                    method = 'POST'
                    ship_par = {'orders':[{
                            'order_id': order_number,
                            'order_item_ids': order_item_ids
                        }]
                    }
                    ship_par = json.dumps(ship_par)
                    ship_params = {'getShipmentProvidersReq': ship_par}
                    ship_values = company.lazada_sdk(url=url, request=ship_url, params=ship_params, method=method, access_token=access_token)
                    ships_values = ship_values.body
                    shipping_allocate_type = ''
                    if ships_values.get('result').get('data'):
                        shipping_allocate_type = ships_values.get('result').get('data').get('shipping_allocate_type','')
                    params_pack = {
                        'pack_order_list': [{
                            'order_item_list':order_item_ids,
                            'order_id': order_number
                        }],
                        'delivery_type': 'dropship',
                        'shipping_allocate_type': shipping_allocate_type
                    }
                    params_pack = json.dumps(params_pack)
                    package_params = {'packReq': params_pack}
                    package_values = company.lazada_sdk(url=url, request=pack_url, params=package_params, method=method, access_token=access_token)
                    pack_values = package_values.body
                    if pack_values.get('result'):
                        if pack_values.get('result').get('success'):
                            return True
                        else:
                            return False
                    else:
                        return False
                except:
                    return False

        def complete_order(invoice_id, sale, order):
            if not invoice_id:
                return False
            invoice = invoice_obj.browse(invoice_id.id)
            if invoice.payment_state not in ['in_payment', 'paid']:
                partner_updated = False
                if invoice.partner_id.parent_id:
                    partner_id = invoice.partner_id.parent_id.id
                else:
                    partner_id = invoice.partner_id.id

                if sale.carrier_id and not sale.carrier_id.is_cashless:
                    if invoice.partner_id.parent_id:
                        invoice.write({'partner_id': partner_id,})
                        partner_updated = True
                    if invoice.state != 'posted':
                        invoice.action_post()

                if invoice.partner_id.parent_id and not partner_updated:
                    invoice.button_cancel()
                    invoice.write({'partner_id': partner_id,'state': 'draft'})
                    invoice.action_post()

                move_line_ids = []
                for line in invoice.line_ids:
                    if line.account_id.reconcile:
                        move_line_ids.append(line.id)

                ctx = dict(self._context, uid=self._uid, active_model='account.move', active_ids=[invoice.id], active_id=invoice.id)
                payment_method_line_id = method_line_obj.search([('payment_method_id.payment_type','=','inbound'),('journal_id','=',shop.payment_journal_id.id)], limit=1)
                payment_method_line_id = payment_method_line_id.id
                pay_id = register_obj.with_context(ctx).create({
                    'amount': invoice.amount_residual,
                    'journal_id': shop.payment_journal_id.id,
                    'payment_method_line_id': payment_method_line_id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': partner_id,
                    'payment_date': order['updated_at'].strftime('%Y-%m-%d'),
                })
                payment_data = pay_id.action_create_payments()

        url = shop.region_id.url
        method = 'GET'
        access_token = shop.access_token

        log_id = False
        more = True
        offset = 0
        affected_count = 0
        skipped_count = 0
        affected_list = ''
        skipped_list = ''
        additional_info = ''
        log_line_values = []
        is_continue = False

        # Get Orders List API
        orders_request = '/orders/get'
        orders_params = {
            'offset': offset,
            'limit': 100, # Max Limit: 100
            'sort_direction': 'ASC',
        }

        timezone = str(shop.region_id.timezone or 7)
        current_date = fields.Datetime.now() + timedelta(hours=int(timezone))

        start_order_date = False
        if data.is_continue:
            start_log_id = log_obj.search([('name', '=', 'Get Orders List'), ('shop_id', '=', shop.id), ('state', 'in', ['partial', 'success']), ('is_order_date', '=', True)], limit=1)
            if start_log_id:
                start_log = start_log_id
                start_order_date = start_log.running_date
        else:
            start_order_date = data.start_date
        
        if data.is_continue:
            last_log_id = log_obj.search([('name', '=', 'Get Orders List'), ('shop_id', '=', shop.id), ('state', 'in', ['partial', 'success', 'skipped'])], limit=1)
            if last_log_id:
                date_from = last_log_id.latest_date + timedelta(hours=int(timezone)) - timedelta(minutes=10)
                date_to = date_from + timedelta(days=10)
                update_time_from = date_from

                if date_to > current_date:
                    update_time_to = current_date
                else:
                    update_time_to = date_to

                orders_params['update_after'] = update_time_from.strftime('%Y-%m-%dT%H:%M:%S+0'+timezone+'00')
                orders_params['update_before'] = update_time_to.strftime('%Y-%m-%dT%H:%M:%S+0'+timezone+'00')
                orders_params['sort_by'] = 'updated_at'
                log_latest_date = datetime.now() > update_time_to and update_time_to or datetime.now()
                running_date = update_time_from.strftime('%Y-%m-%d %H:%M:%S')
                is_continue = True

        if not is_continue:
            if not data.start_date:
                raise UserError(_('Please manually run the "Get Orders" first.'))
            date_from = data.start_date + timedelta(hours=int(timezone))
            date_to = date_from + timedelta(days=10)
            create_time_from = date_from

            if date_to > current_date:
                create_time_to = current_date
            else:
                create_time_to = date_to

            orders_params['created_after'] = create_time_from.strftime('%Y-%m-%dT%H:%M:%S+0'+timezone+'00')
            orders_params['created_before'] = create_time_to.strftime('%Y-%m-%dT%H:%M:%S+0'+timezone+'00')
            orders_params['sort_by'] = 'created_at'
            log_latest_date = datetime.now() > create_time_to and create_time_to or datetime.now()
            running_date = data.start_date

        while(more):
            orders_params.update(offset=offset)
            orders_response = company.lazada_sdk(url=url, request=orders_request, params=orders_params, method=method, access_token=access_token)
            orders_body = orders_response.body

            orders_code = orders_body['code']
            if orders_code != '0':
                
                log_id = log_obj.create({
                    'name': 'Get Orders List',
                    'shop_id': shop.id,
                    'running_date': running_date,
                    'latest_date': log_latest_date,
                    'state': 'failed',
                })
                return {
                    'name': 'API Logs',
                    'type': 'ir.actions.act_window',
                    'res_model': 'lazada.history.api',
                    'res_id': log_id.id,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': view_id,
                    'target': 'new'
                }
                
            if not orders_body.get('data') or not orders_body['data'].get('orders'):
                ###Lazada doesn't have "more" response
                more = False

                log_id = log_obj.create({
                    'name': 'Get Orders List',
                    'shop_id': shop.id,
                    'running_date': running_date,
                    'latest_date': log_latest_date,
                    'total_affected': affected_count,
                    'total_skipped': skipped_count,
                    'affected_list': affected_list,
                    'skipped_list': skipped_list,
                    'is_order_date': not is_continue,
                    'additional_info': additional_info,
                    'state': 'success',
                })
                continue

            for order in orders_body['data']['orders']:
                order_number = order['order_number']
                list_statuses = order['statuses']
                if len(list_statuses) > 1:
                    additional_info += '[ %s ]: Order has multiple status\n' % (order_number)

                for statuses in list_statuses:
                    order_exist = order_obj.search([('name', '=', order_number), ('statuses', '=', statuses), ('shop_id', '=', shop.id)])
                    if order_exist:
                        if skipped_count != 0:
                            skipped_list += '\n'
                        skipped_count += 1
                        skipped_list += '[ %s ]: Already created' % (order_number)
                        continue

                    partner_invoice_name = order['address_billing']['first_name']
                    invoice_phone = order['address_billing']['phone']
                    partner_shipping_name = order['address_shipping']['first_name']
                    shipping_phone = order['address_shipping']['phone']

                    partner_invoice = partner_obj.search([('name', '=', partner_invoice_name), ('phone', '=', invoice_phone), ('is_lazada_partner', '=', True)], limit=1)
                    if not partner_invoice:
                        partner_invoice = partner_obj.create({
                            'name': partner_invoice_name,
                            'phone': invoice_phone,
                            'street': order['address_billing']['address1'],
                            'city': order['address_billing']['city'],
                            'zip': order['address_billing']['post_code'],
                            'is_lazada_partner': True,
                            'customer_rank': 1,
                        })
                    if partner_invoice_name != partner_shipping_name:
                        partner_shipping = partner_obj.search([('name', '=', partner_shipping_name), ('phone', '=', shipping_phone), ('parent_id', '=', partner_invoice.id), ('is_lazada_partner', '=', True)], limit=1)
                        if not partner_shipping:
                            partner_shipping = partner_obj.create({
                                'name': partner_shipping_name,
                                'phone': shipping_phone,
                                'street': order['address_billing']['address1'],
                                'city': order['address_billing']['city'],
                                'zip': order['address_billing']['post_code'],
                                'is_lazada_partner': True,
                                'customer_rank': 1,
                                'parent_id': partner_invoice.id,
                                'type': 'delivery',
                            })
                    else:
                        partner_shipping = partner_invoice

                    if order.get('created_at',False):
                        lz_created_at = order['created_at'].replace(' +0700','')
                        lz_created_at = datetime.strptime(lz_created_at, '%Y-%m-%d %H:%M:%S')
                        lz_created_at = lz_created_at - timedelta(hours=7)
                        lz_created_at = lz_created_at.strftime('%Y-%m-%d %H:%M:%S')
                        order['created_at'] = lz_created_at

                    if order.get('updated_at',False):
                        lz_updated_at = order['updated_at'].replace(' +0700','')
                        lz_updated_at = datetime.strptime(lz_updated_at, '%Y-%m-%d %H:%M:%S')
                        lz_updated_at = lz_updated_at - timedelta(hours=7)
                        lz_updated_at = lz_updated_at.strftime('%Y-%m-%d %H:%M:%S')
                        order['updated_at'] = lz_updated_at
                    order_values = {
                        'name': order_number,
                        'shop_id': shop.id,
                        'statuses': statuses,
                        'created_date': order['created_at'],
                        'updated_date': order['updated_at'],
                        'partner_id': partner_invoice.id,
                        'partner_invoice_id': partner_shipping.id,
                        'partner_shipping_id': partner_shipping.id,
                        'payment_method': order['payment_method'],
                        'price': order['price']
                    }
                    lazada_order = order_obj.create(order_values)
                    if affected_count != 0:
                        affected_list += '\n'
                    affected_count += 1
                    affected_list += str(order_number)

            offset += 100

        self.env.cr.execute(""" 
            SELECT name as order_number, shop_id, statuses, created_date as created_at, updated_date as updated_at, partner_id, partner_invoice_id, partner_shipping_id, payment_method, price
            FROM (
                SELECT DISTINCT ON (name) name, shop_id, statuses, created_date, updated_date, partner_id, partner_invoice_id, partner_shipping_id, payment_method, price
                FROM lazada_order
                WHERE shop_id = %s AND (is_updated IS NULL OR is_updated = false)
                ORDER BY name, updated_date ASC
            ) sub ORDER BY updated_date ASC LIMIT 50
        """, (shop.id,))
        order_ids = self.env.cr.dictfetchall()
        sale_updated_count = 0
        sale_skipped_count = 0
        sale_affected_count = 0
        sale_inserted_count = 0
        sale_affected_list = ''
        sale_skipped_list = ''
        sale_ids = []
        dropship = False

        for order in order_ids:
            statuses = order['statuses']
            statuses = 'confirmed'
            payment_method = order['payment_method']
            price = order['price']
            permission = False
            order_create_date = order['created_at']
            order_number = order['order_number']
            if start_order_date:
                if order_create_date >= start_order_date:
                    permission = True
            else:
                permission = True
            if permission:
                sale_id = sale_obj.search([('lazada_ordersn', '=', order_number), ('lazada_shop_id', '=', shop.id)], limit=1)
                if sale_id:
                    sale = sale_id
                    if payment_method == 'COD':
                        sale.write({
                            'is_lazada_cod': True,
                            'lazada_cod_amount': price
                        })
                    if sale.date_order != order_create_date:
                        sale.write({'date_order': order_create_date})

                    if statuses in ('ready_to_ship', 'packed'):
                        rts_order(sale, order)
                        invoice_id = create_invoice_order(sale, order)
                    elif statuses in ('shipped', 'delivered'):
                        rts_order(sale, order)
                        lazada_ship(sale, order)
                        create_invoice_order(sale, order)
                    elif statuses in ('canceled', 'returned', 'failed', 'failed_delivery'):
                        sale_ids.append(sale.id)
                        cancel_order(sale, order)
                    elif statuses == "confirmed":
                        rts_order(sale, order)
                        lazada_ship(sale, order)
                        invoice_id = create_invoice_order(sale, order)
                        complete_order(invoice_id, sale, order)

                    # if not sale.tracking_no:
                    ###Get Tracking Number

                    items_request = '/order/items/get'
                    items_params = {
                        'order_id': order_number,
                    }
                    items_response = company.lazada_sdk(url=url, request=items_request, params=items_params, method=method, access_token=access_token)
                    values = items_response.body

                    order_item_ids = []
                    for item in values['data']:
                        if item.get('order_item_id',False):
                            order_item_ids.append(item.get('order_item_id'))

                    if statuses in ('pending','packed'):
                        dropship = fulfill_pack(sale, order_item_ids, order_number)

                    items_code = values['code']
                    if items_code == '0':
                        tracking_no = values.get('data')[0].get('tracking_code',False)
                        if tracking_no:
                            sale.write({'tracking_no': tracking_no,'lazada_tracking_no': tracking_no})
                            if sale.picking_ids:
                                sale.picking_ids.write({'carrier_tracking_ref': tracking_no})

                        slowes_date = values.get('data')[0].get('fulfillment_sla',False)
                        if slowes_date:
                            pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
                            matches = re.findall(pattern, slowes_date)
                            if matches:
                                slow_date = matches[0]
                                if slow_date:
                                    slow_date = datetime.strptime(slow_date, '%Y-%m-%d %H:%M:%S')
                                    slow_date = slow_date - timedelta(hours=7)
                                    slow_date = slow_date.strftime('%Y-%m-%d %H:%M:%S')
                                    sale.write({'slowest_delivery_date': slow_date})

                        package_request = '/order/package/document/get'
                        params_pack = {
                            'doc_type': 'HTML',
                            'packages': [{'package_id':values.get('data')[0].get('package_id')}]
                        }
                        params_pack = json.dumps(params_pack)
                        package_params = {'getDocumentReq': params_pack}
                        package_response = company.lazada_sdk(url=url, request=package_request, params=package_params, access_token=access_token)
                        package_values = package_response.body
                        file_html = package_values.get('result').get('data').get('file')
                        if file_html:
                            file_html = base64.b64decode(file_html)
                            file_html = file_html.decode('utf-8')
                            soup = BeautifulSoup(file_html, 'html.parser')
                            prioritas_value = soup.find('div', {'class': 'tdchild-div'}).text.strip()
                            if prioritas_value:
                                sale.write({'lz_shipping_provider_type': prioritas_value})

                        date_order_create = values.get('data')[0].get('created_at',False)
                        if date_order_create:
                            date_order_create = date_order_create.replace(' +0700','')
                            if sale.date_order != date_order_create:
                                date_order_create = datetime.strptime(date_order_create, '%Y-%m-%d %H:%M:%S')
                                date_order_create = date_order_create - timedelta(hours=7)
                                date_order_create = date_order_create.strftime('%Y-%m-%d %H:%M:%S')
                                sale.write({'date_order': date_order_create})

                        name_shipping = False
                        if item.get('shipment_provider'):
                            name_shipping = list(item['shipment_provider'].split(":"))
                            name_shipping = len(name_shipping) == 3 and name_shipping[2].strip() or False

                        if name_shipping:
                            carrier = carrier_obj.search([('name', '=', name_shipping)], limit=1)
                            if carrier:
                                sale.write({'carrier_id': carrier.id})
                                sale.picking_ids.write({'carrier_id': carrier.id})

                    sale_updated_count += 1

                    if sale_affected_count != 0:
                        sale_affected_list += '\n'
                    sale_affected_count += 1
                    sale_affected_list += str(order_number)

                    self.env.cr.execute("""
                        UPDATE lazada_order set is_updated = True where name = %s and shop_id = %s and updated_date <= %s
                    """, (str(order_number), shop.id, order['updated_at']))

                    if not dropship and statuses in ('pending','packed'):
                        self.env.cr.execute("""
                            UPDATE lazada_order set is_updated = False where name = %s and shop_id = %s and updated_date <= %s
                        """, (str(order_number), shop.id, order['updated_at']))

                else:
                    sale_exist = sale_obj.search(['|', ('client_order_ref', '=', order_number), ('lazada_ordersn', '=', order_number)], limit=1)
                    if sale_exist:
                        self.env.cr.execute("""
                            UPDATE lazada_order set is_updated = True where name = %s and shop_id = %s and updated_date <= %s
                        """, (str(order_number), shop.id, order['updated_at']))

                        if sale_skipped_count != 0:
                            sale_skipped_list += '\n'
                        sale_skipped_count += 1
                        sale_skipped_list += '%s: Order already exist, skip order' % (order_number)
                        continue

                    sale_values = {
                        'date_order': order_create_date,
                        'partner_id': order['partner_id'],
                        'partner_invoice_id': order['partner_invoice_id'],
                        'partner_shipping_id': order['partner_shipping_id'],
                        'client_order_ref': order_number,

                        'lazada_shop_id': shop.id,
                        'is_lazada_order': True,
                        'lazada_ordersn': order_number,
                        'warehouse_id': shop.warehouse_id.id,
                        'lazada_cod_amount': price
                    }
                    if payment_method == 'COD':
                        sale_values['is_lazada_cod'] = True

                    ###Get Orders API
                    items_request = '/order/items/get'
                    items_params = {
                        'order_id': order_number,
                    }
                    items_response = company.lazada_sdk(url=url, request=items_request, params=items_params, method=method, access_token=access_token)
                    items_body = items_response.body
                    items_code = items_body['code']
                    if items_code != '0':

                        if sale_skipped_count != 0:
                            sale_skipped_list += '\n'
                        sale_skipped_count += 1
                        sale_skipped_list += '%s: Order has error when get the Item Details' % (order_number)
                        continue
                    
                    product_error = False
                    order_line = []
                    order_lines = []
                    shipping_fee = 0
                    tracking_code = False
                    name_shipping = False
                    total_so = 0
                    order_item_ids = []
                    for item in items_body['data']:
                        # if 'shipping_provider_type' in str(item):
                        #     sale_values['lz_shipping_provider_type'] = item['shipping_provider_type']
                        if item.get('order_item_id',False):
                            order_item_ids.append(item.get('order_item_id'))
                        variation_sku = item['sku'].strip().replace('\n', '')
                        lazada_variant = lazada_variant_obj.search([('shop_id', '=', shop.id), ('shop_sku', '=', item['shop_sku']), ('product_id.active', '=', True)], limit=1)
                        if lazada_variant:
                            product = lazada_variant.product_id
                        else:
                            product = product_obj.search(['|',('default_code', '=', variation_sku),('lazada_seller_sku','=',variation_sku)], limit=1)
                        if not product:
                            sale_skipped_list += '[ %s ]: SKU not found [ %s ]\n' % (order_number, variation_sku)
                            product_error = True
                            continue

                        shipping_fee += item['shipping_amount']
                        calculate_price = item['paid_price']
                        order_lines.append((0, 0, {
                            'product_id': product.id,
                            'product_uom_qty': 1,
                            'price_unit': calculate_price,
                        }))
                        total_so += calculate_price

                        tracking_code = item.get('tracking_code')
                        if item.get('shipment_provider'):
                            name_shipping = list(item['shipment_provider'].split(":"))
                            name_shipping = len(name_shipping) == 3 and name_shipping[2].strip() or False

                    # Membuat kamus kosong untuk menyimpan hasil penjumlahan
                    gabungan_produk = {}

                    # Iterasi melalui data dan menggabungkan product_uom_qty untuk setiap product_id
                    for _, _, record in order_lines:
                        product_id = record['product_id']
                        uom_qty = record['product_uom_qty']
                        
                        if product_id in gabungan_produk:
                            gabungan_produk[product_id]['product_uom_qty'] += uom_qty
                        else:
                            gabungan_produk[product_id] = record

                    # Mengubah hasil penggabungan menjadi daftar
                    hasil_gabungan = list(gabungan_produk.values())

                    # Menampilkan hasil penggabungan
                    for item in hasil_gabungan:
                        order_line.append((0, 0, item))
                    # if shipping_fee:
                    #     order_line.append((0, 0, {
                    #         'product_id': company.lazada_logistic_product_id.id,
                    #         'product_uom_qty': 1,
                    #         'price_unit': shipping_fee,
                    #         'is_delivery': True,
                    #     }))
                    order_line.append((0,0, {
                        'product_id': company.lazada_commission_product_id.id,
                        'product_uom_qty': 1,
                        'price_unit': -round(total_so*(float(shop.lazada_commission)/100),2)
                    }))
                    if name_shipping:
                        carrier = carrier_obj.search([('name', '=', name_shipping)], limit=1)
                        if not carrier:
                            if sale_skipped_count != 0:
                                sale_skipped_list += '\n'
                            sale_skipped_count += 1
                            sale_skipped_list += '%s: shipping carrier (%s) not found' % (order_number, name_shipping)
                            continue

                        sale_values['carrier_id'] = carrier.id

                    if product_error:
                        sale_skipped_count += 1
                        continue
                    else:
                        sale_values['tracking_no'] = tracking_code
                        sale_values['order_line'] = order_line
                        sale = sale_obj.create(sale_values)

                        if sale.date_order != order_create_date:
                            sale.write({'date_order': order_create_date})


                        sale_ids.append(sale.id)

                        if statuses in ('pending','packed'):
                            dropship = fulfill_pack(sale, order_item_ids, order_number)

                        if statuses in ('ready_to_ship','packed'):
                            rts_order(sale, order)
                            invoice_id = create_invoice_order(sale, order)
                        elif statuses in ('shipped', 'delivered'):
                            rts_order(sale, order)
                            lazada_ship(sale, order)
                            create_invoice_order(sale, order)
                        elif statuses in ('canceled', 'returned', 'failed', 'failed_delivery'):
                            cancel_order(sale, order)
                        elif statuses == 'confirmed': 
                            rts_order(sale, order)
                            lazada_ship(sale, order)
                            invoice_id = create_invoice_order(sale, order)
                            complete_order(invoice_id, sale, order)

                        if sale.picking_ids:
                            sale.picking_ids.write({'carrier_tracking_ref': tracking_code})

                        slowes_date = items_body.get('data')[0].get('fulfillment_sla',False)
                        if slowes_date:
                            pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
                            matches = re.findall(pattern, slowes_date)
                            if matches:
                                slow_date = matches[0]
                                if slow_date:
                                    slow_date = datetime.strptime(slow_date, '%Y-%m-%d %H:%M:%S')
                                    slow_date = slow_date - timedelta(hours=7)
                                    slow_date = slow_date.strftime('%Y-%m-%d %H:%M:%S')
                                    sale.write({'slowest_delivery_date': slow_date})

                        package_request = '/order/package/document/get'
                        params_pack = {
                            'doc_type': 'HTML',
                            'packages': [{'package_id':items_body.get('data')[0].get('package_id')}]
                        }
                        params_pack = json.dumps(params_pack)
                        package_params = {'getDocumentReq': params_pack}
                        package_response = company.lazada_sdk(url=url, request=package_request, params=package_params, access_token=access_token)
                        package_values = package_response.body
                        file_html = package_values.get('result').get('data').get('file')
                        if file_html:
                            file_html = base64.b64decode(file_html)
                            file_html = file_html.decode('utf-8')
                            soup = BeautifulSoup(file_html, 'html.parser')
                            prioritas_value = soup.find('div', {'class': 'tdchild-div'}).text.strip()
                            if prioritas_value:
                                sale.write({'lz_shipping_provider_type': prioritas_value})                            

                        date_order_create = items_body.get('data')[0].get('created_at',False)
                        if date_order_create:
                            date_order_create = date_order_create.replace(' +0700','')
                            if sale.date_order != date_order_create:
                                date_order_create = datetime.strptime(date_order_create, '%Y-%m-%d %H:%M:%S')
                                date_order_create = date_order_create - timedelta(hours=7)
                                date_order_create = date_order_create.strftime('%Y-%m-%d %H:%M:%S')
                                sale.write({'date_order': date_order_create})
                        sale_inserted_count += 1

                        if sale_affected_count != 0:
                            sale_affected_list += '\n'
                        sale_affected_count += 1
                        sale_affected_list += str(order_number)

                        self.env.cr.execute("""
                            UPDATE lazada_order set is_updated = True where name = %s and shop_id = %s and updated_date <= %s
                        """, (str(order_number), shop.id, order['updated_at']))

                        if not dropship and statuses in ('pending','packed'):
                            self.env.cr.execute("""
                                UPDATE lazada_order set is_updated = False where name = %s and shop_id = %s and updated_date <= %s
                            """, (str(order_number), shop.id, order['updated_at']))
            else:
                if sale_skipped_count != 0:
                    sale_skipped_list += '\n'
                sale_skipped_count += 1
                sale_skipped_list += '[ %s ]: The order date is below start date\n' % (order_number)

                self.env.cr.execute("""
                    UPDATE lazada_order set is_updated = True where name = %s and shop_id = %s and updated_date <= %s
                """, (str(order_number), shop.id, order['updated_at']))

            self.env.cr.commit()

        self.env.cr.execute(""" 
            SELECT COUNT(id) FROM lazada_order 
                WHERE shop_id = %s AND (is_updated IS NULL OR is_updated = false) 
            """ % (shop.id))
        is_more = self.env.cr.fetchone()[0]
        additional_info = ''
        if is_more:
            context['is_more'] = True
            additional_info = 'There are still orders that need to be processed.'

        # if len(sale_ids) > 1:
        #     self.env.cr.execute("""
        #         SELECT array_to_string(ARRAY(
        #         SELECT DISTINCT ON (pt.id) pt.id FROM sale_order so
        #             LEFT JOIN sale_order_line sol ON sol.order_id = so.id
        #             LEFT JOIN product_product pp ON sol.product_id = pp.id
        #             LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
        #         WHERE so.id IN %s AND pt.is_lazada_auto_stock = True
        #         ), ',')
        #     """ % (tuple(sale_ids),))
        # elif len(sale_ids) == 1:
        #     self.env.cr.execute("""
        #         SELECT array_to_string(ARRAY(
        #         SELECT DISTINCT ON (pt.id) pt.id FROM sale_order so
        #             LEFT JOIN sale_order_line sol ON sol.order_id = so.id
        #             LEFT JOIN product_product pp ON sol.product_id = pp.id
        #             LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
        #         WHERE so.id = %s AND pt.is_lazada_auto_stock = True
        #         ), ',')
        #     """ % (sale_ids[0]))

        # if sale_ids:
        #     product_tmpl_ids = self.env.cr.fetchone()
        #     if product_tmpl_ids and product_tmpl_ids[0]:
        #         product_tmpl_ids = map(int, product_tmpl_ids[0].split(','))
        #         if company.lazada_shop_ids:
        #             update_context = context.copy()
        #             update_context.update(active_ids=product_tmpl_ids)
        #             update_id = update_obj.create({
        #                 'shop_ids': [(6, 0, company.lazada_shop_ids.ids)],
        #                 'is_update_stock': True
        #             })
        #             update_id.with_context(update_context).action_confirm()

        log_id = log_obj.create({
            'name': 'Get Order',
            'shop_id': shop.id,
            'additional_info': additional_info,
            'total_inserted': sale_inserted_count,
            'total_updated': sale_updated_count,
            'total_affected': sale_affected_count,
            'total_skipped': sale_skipped_count,
            'affected_list': sale_affected_list,
            'skipped_list': sale_skipped_list,
            'timestamp': timest,
            'state': 'success',
        }).id

        return {
            'name': 'History API',
            'type': 'ir.actions.act_window',
            'res_model': 'lazada.history.api',
            'res_id': log_id,
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context
        }


