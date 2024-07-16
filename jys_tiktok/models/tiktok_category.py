from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class TiktokCategory(models.Model):
    _name = 'tiktok.category'
    _description = 'Tiktok Category'

    name = fields.Char('Name')
    full_name = fields.Char(compute='_full_name', string='Name')    
    tiktok_category_id = fields.Integer('Category ID')
    tiktok_parent_id = fields.Integer('Parent ID')
    is_leaf = fields.Boolean('Leaf Category')
    permission_statuses = fields.Char('Permission')

    rules_ids = fields.One2many('tiktok.category.rules', 'tiktok_category_id', 'Rules')

    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.tiktok_parent_id:
                parent = self.search([('tiktok_parent_id','=',record.tiktok_parent_id)], limit=1, order='id desc')
                #for par in parent:
                name = parent.name+' / '+name
            res.append((record.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        context = dict(self._context or {})
        if name:
            name = name.split(' / ')[-1]
            ids = self.search([('name', operator, name)] + args, limit=limit)
        else:
            ids = self.search(args, limit=limit)
        return ids.name_get()

    def _full_name(self):
        for record in self:
            record.full_name = record.name_get()[0][1]

class TiktokCategoryRules(models.Model):
    _name = 'tiktok.category.rules'
    _description = 'Tiktok Category Rules'

    name = fields.Char('Name')    
    tiktok_category_id = fields.Many2one('tiktok.category','Category ID')
    cod = fields.Boolean('COD Supported')
    epr = fields.Boolean('EPR Required')
    package_dimension = fields.Boolean('Package Dimension Required')
    size_sup = fields.Boolean('Size Chart Supported')
    size_req = fields.Boolean('Size Chart Required')
    certif_id = fields.Char('Certification ID')
    certif_req = fields.Boolean('Certification Required')
    url = fields.Char('Sample Certification')

