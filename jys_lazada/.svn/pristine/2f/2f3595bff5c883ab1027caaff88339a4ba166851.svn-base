from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class LazadaCategory(models.Model):
    _name = 'lazada.category'
    _description = 'Lazada Category'

    name = fields.Char('Name')
    complete_name = fields.Char(compute='_complete_name', string='Name')
    lazada_category_id = fields.Integer('Lazada Category ID')
    lazada_parent_id = fields.Integer('Lazada Parent ID')
    is_leaf = fields.Boolean('Leaf')
    is_var = fields.Boolean('Var')
    parent_id = fields.Many2one('lazada.category', 'Parent')
    child_ids = fields.One2many('lazada.category', 'parent_id', 'Child')

    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.parent_id:
                name = record.parent_id.name+' / '+name
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

    def _complete_name(self):
        for record in self:
            record.complete_name = record.name_get()[0][1]
    