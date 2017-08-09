# -*- coding: utf-8 -*-
import collections

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import ValidationError
from openerp.osv import expression

import logging
_logger = logging.getLogger(__name__)


class GenericTagModel(models.Model):
    _name = "generic.tag.model"
    _inherits = {'ir.model': 'res_model_id'}

    _description = "Generic Tag Model"

    _access_log = False

    @api.multi
    def _compute_tags_count(self):
        for model in self:
            model.tags_count = self.env['generic.tag'].search_count(
                [('model_id', '=', model.id)])

    res_model_id = fields.Many2one(
        'ir.model', 'Model', required=True, index=True, auto_join=True,
        ondelete='restrict')

    tags_count = fields.Integer(
        string="Tags", compute="_compute_tags_count", store=False,
        readonly=True, help="How many tags related to this model exists")

    @api.multi
    def action_show_tags(self):
        self.ensure_one()
        ctx = dict(self.env.context, default_model_id=self.id)
        return {
            'name': _('Tags related to model %s') % self.name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'generic.tag',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'domain': [('model_id.id', '=', self.id)],
        }


class GenericTagModelMixin(models.AbstractModel):
    _name = "generic.tag.model.mixin"

    @api.model
    def _get_default_model_id(self):
        """ Try to get default model from context and find
            approriate generic.tag.model record
        """
        GenericTagModel = self.env['generic.tag.model']
        default_model = self.env.context.get('default_model', False)

        if default_model:
            return GenericTagModel.search(
                [('model', '=', default_model)], limit=1)

        return GenericTagModel.browse()

    model_id = fields.Many2one(
        "generic.tag.model", "Model", required=True, ondelete='restrict',
        default=_get_default_model_id,
        help="Specify model for which this tag is available")


class GenericTagCategory(models.Model):
    _name = 'generic.tag.category'
    _inherit = ['generic.tag.model.mixin']
    _description = "Generic Tag Category"

    _access_log = False

    @api.multi
    @api.depends('tag_ids')
    def _compute_tags_count(self):
        for line in self:
            line.tags_count = len(line.tag_ids)

        # model_id field will be added by 'generic.tag.model.mixin'
    name = fields.Char(required=True, translate=True, index=True)
    code = fields.Char(
        index=True, help="May be used for special"
                         "tags which have programmed bechavior")

    comment = fields.Text(help="Describe what this tag category is for")

    active = fields.Boolean(index=True, default=True)

    tag_ids = fields.One2many(
        "generic.tag", "category_id", "Tags", readonly=True)

    check_xor = fields.Boolean(
        "Check XOR",
        help="if set to True then only one tag from this category "
             "may be present on a single object. "
             "On attempt to add second tag from this category to object, "
             "error will be raised")
    tags_count = fields.Float(
        string="Tags", compute="_compute_tags_count", store=True,
        readonly=True, track_visibility='always',
        help="How many tags related to this catgory")

    color = fields.Integer()

    _sql_constraints = [
        ('name_uniq', 'unique(model_id, name)',
         'Name of category must be unique'),
        ('code_uniq', 'unique(model_id, code)',
         'Code of category must be unique'),
    ]

    @api.constrains('model_id')
    def _check_model_id(self):
        for category in self:
            tag_model = category.tag_ids.mapped('model_id')
            if tag_model and (len(tag_model) != 1 or
                              tag_model != category.model_id):
                raise ValidationError(_(
                    u"Model must be same as one used in related tags"))

    @api.multi
    def action_show_tags(self):
        self.ensure_one()
        ctx = dict(self.env.context,
                   default_model_id=self.model_id.id,
                   default_category_id=self.id)
        return {
            'name': _('Tags related to category %s') % self.name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'generic.tag',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'domain': [('category_id.id', '=', self.id)],
        }


class GenericTag(models.Model):
    _name = "generic.tag"
    _inherit = ['generic.tag.model.mixin']
    _description = "Generic Tag"

    _access_log = False

    _rec_name = 'complete_name'
    _order = 'complete_name'

    @api.multi
    def _compute_objects_count(self):
        for tag in self:
            tag.objects_count = self.env[tag.model_id.model].search_count(
                [('tag_ids.id', '=', tag.id)])

    @api.multi
    @api.depends('category_id.name', 'name')
    def _compute_complete_name(self):
        for tag in self:
            if tag.category_id:
                tag.complete_name = "%s / %s" % (tag.category_id.name,
                                                 tag.name)
            else:
                tag.complete_name = tag.name

    @api.constrains('category_id', 'model_id')
    def _check_category_model(self):
        for tag in self:
            if tag.category_id and tag.model_id != tag.category_id.model_id:
                raise ValidationError(_(
                    u"Category must be bound to same model as tag"))

    category_id = fields.Many2one(
        'generic.tag.category', 'Category',
        index=True, ondelete='restrict')
    name = fields.Char(required=True, translate=True, index=True)
    code = fields.Char(
        index=True, help="May be used for special"
                         "tags which have programmed bechavior")
    comment = fields.Text(help="Describe what this tag means")

    active = fields.Boolean(default=True, index=True)

    complete_name = fields.Char(
        string="Name", compute="_compute_complete_name",
        store=True, readonly=True,
        help="Full name of tag (including category name")

    objects_count = fields.Integer(
        string="Tags", compute="_compute_objects_count",
        store=False, readonly=True, track_visibility='always',
        help="How many objects contains this tag")
    group_ids = fields.Many2many('res.groups', string='Groups')
    color = fields.Integer()

    _sql_constraints = [
        ('name_uniq',
         'unique(model_id, category_id, name)',
         'Name of tag must be unique for category'),
        ('code_uniq',
         'unique(model_id, code)',
         'Code of tag must be unique'),
    ]

    @api.multi
    def name_get(self):
        return [(t.id, t.complete_name) for t in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            domain = [
                [('name', operator, name)],
                [('code', operator, name)],
                [('complete_name', operator, name)]
            ]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = expression.AND(domain)
            else:
                domain = expression.OR(domain)

            domain = expression.AND([domain, args])
            tags = self.search(domain, limit=limit)
        else:
            tags = self.search(args, limit=limit)

        return tags.name_get()

    @api.model
    @api.returns('self')
    def get_tags(self, model, code=None, name=None):
        """ Search for tags by model, code, name
        """
        assert bool(code) or bool(name), (
            "code or name must not be None! (code=%s;name=%s)"
            "" % (code, name))
        tag_domain = [('model_id.model', '=', model)]
        if code is not None:
            tag_domain.append(('code', '=', code))
        if name is not None:
            tag_domain.append(('name', '=', name))
        return self.search(tag_domain)

    @api.multi
    def action_show_objects(self):
        self.ensure_one()
        return {
            'name': _('Objects related to tag %s') % self.name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': self.model_id.model,
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'domain': [('tag_ids.id', '=', self.id)],
        }


class GenericTagMixin(models.AbstractModel):
    """ Mixin to be used to add tag support to any model
        by inheriting from it like:
            _inherit=["generic.tag.mixin"]
    """
    _name = "generic.tag.mixin"

    @api.constrains('tag_ids')
    def _check_tags_xor(self):
        for record in self:
            categ_counter = collections.defaultdict(
                self.env['generic.tag'].browse)
            for tag in record.tag_ids:
                if tag.category_id.check_xor:
                    categ_counter[tag.category_id] |= tag

            bad_tags = []
            for category, tags in categ_counter.items():
                if len(tags) > 1:
                    bad_tags.append(
                        (category, tags)
                    )
            if bad_tags:
                msg_detail = ', '.join(
                    ('[%s - %s]' % (cat.name, ', '.join(tags.mapped('name')))
                     for cat, tags in bad_tags)
                )
                raise ValidationError(
                    _("Following (category - tags) pairs, "
                      "break category XOR restriction:\n%s"
                      "") % msg_detail)

    def _search_no_tag_id(self, operator, value):
        with_tags = self.search([('tag_ids', operator, value)])
        return [('id', 'not in', with_tags.mapped('id'))]

    def _compute_no_tag_id(self):
        for res in self:
            res.no_tag_id = False

    tag_ids = fields.Many2many(
        'generic.tag', string="Tags",
        domain=lambda self: [('model_id.model', '=', self._name)])
    no_tag_id = fields.Many2one(
        'generic.tag', string="No Tag", compute="_compute_no_tag_id",
        search='_search_no_tag_id', store=False,
        readonly=True, track_visibility='always',
        domain=lambda self: [('model_id.model', '=', self._name)])

    @api.multi
    def add_tag(self, code=None, name=None, create=False):
        """ Adds tag new tag to object.

            @param code: tag.code field to search for
            @param name: tag.name field to search for
            @param create: if True then create tag if not found
        """
        GenericTag = self.env['generic.tag']
        tags = GenericTag.get_tags(self._name, code=code, name=name)

        if not tags and create:
            model = self.env['generic.tag.model'].search(
                [('model', '=', self._name)])[0]
            tags = GenericTag.create({
                'name': name,
                'code': code,
                'model_id': model.id,
            })

        if tags:
            self.write({'tag_ids': [(4, t.id) for t in tags]})

    @api.multi
    def remove_tag(self, code=None, name=None):
        """ Removes tags specified by code/name

            @param code: tag.code field to search for
            @param name: tag.name field to search for
        """
        GenericTag = self.env['generic.tag']
        tags = GenericTag.get_tags(self._name, code=code, name=name)

        if tags:
            self.write({'tag_ids': [(3, t.id) for t in tags]})

    @api.multi
    def check_tag(self, code=None, name=None):
        """ Check if self have tag with specified code / name
        """
        assert bool(code is not None) or bool(name is not None), (
            "code or name must not be None")
        tag_domain = [('id', 'in', self.ids)]
        if code is not None:
            tag_domain.append(('tag_ids.code', '=', code))
        if name is not None:
            tag_domain.append(('tag_ids.name', '=', name))

        count = self.search_count(tag_domain)
        return bool(count == len(self))

    @api.multi
    def check_tag_category(self, code=None, name=None):
        """ Checks if self have tag with specified
            category code and/or category name
        """
        assert bool(code is not None) or bool(name is not None), (
            "code or name must not be None")
        categ_domain = [('id', 'in', self.ids)]
        if code is not None:
            categ_domain.append(('tag_ids.category_id.code', '=', code))
        if name is not None:
            categ_domain.append(('tag_ids.category_id.name', '=', name))

        count = self.search_count(categ_domain)
        return bool(count == len(self))
