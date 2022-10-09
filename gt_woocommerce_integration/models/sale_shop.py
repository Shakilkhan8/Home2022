# -*- coding: utf-8 -*-
#############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
# import urllib
# import re
# from urllib.request import Request, urlopen
# import urllib.request as ur

# from requests import request
from odoo import api, fields, models, _
from odoo.addons.gt_woocommerce_integration.api import API
from odoo.addons.gt_woocommerce_integration.api import woocom_api
import logging
from datetime import timedelta, datetime, date, time
import time
import requests, base64, sys
from io import BytesIO

logger = logging.getLogger('__name__')
import urllib
import json
from odoo.exceptions import UserError
from googletrans import Translator

from datetime import datetime, timedelta, date

# from json import dumps as jsonencode
translator = Translator()
from importlib import reload
import sys

reload(sys)


class SaleShop(models.Model):
    _inherit = "sale.shop"

    @api.model
    def _get_shipment_fee_product(self):
        product = self.env.ref('gt_woocommerce_integration.product_product_shipping')
        return product and product.id or False

    @api.model
    def _get_shipment_gift_product(self):
        product = self.env.ref('gt_woocommerce_integration.product_product_gift_wrapp')
        return product and product.id or False

    code = fields.Char(srting='Code')
    name = fields.Char('Name')

    woocommerce_shop = fields.Boolean(srting='Woocommerce Shop')
    woocommerce_instance_id = fields.Many2one('woocommerce.instance', srting='Woocommerce Instance', readonly=True)
    #     woocommerce_id = fields.Char(string='shop Id')

    # ## Product Configuration
    product_import_condition = fields.Boolean(string="Create New Product if Product not in System while import order",
                                              default=True)
    #     route_ids = fields.Many2many('stock.location.route', 'shop_route_rel', 'shop_id', 'route_id', string='Routes')

    # Order Information
    company_id = fields.Many2one('res.company', srting='Company', required=False,
                                 default=lambda s: s.env['res.company']._company_default_get('stock.warehouse'))
    prefix = fields.Char(string='Prefix')
    suffix = fields.Char(string='Suffix')
    shipment_fee_product_id = fields.Many2one('product.product', string="Shipment Fee",
                                              domain="[('type', '=', 'service')]")
    gift_wrapper_fee_product_id = fields.Many2one('product.product', string="Gift Wrapper Fee",
                                                  domain="[('type', '=', 'service')]")
    sale_journal = fields.Many2one('account.journal')
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist')
    partner_id = fields.Many2one('res.partner', string='Customer')
    workflow_id = fields.Many2one('import.order.workflow', string="Order Workflow")
    on_fly_update_order_status = fields.Boolean(string="Update on Shop at time of Odoo Order Status Change",
                                                default=True)
    # stock Configuration
    on_fly_update_stock = fields.Boolean(string="Update on Shop at time of Odoo Inventory Change", default=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    # Schedular Configuration
    auto_import_order = fields.Boolean(string="Auto Import Order", default=True)
    auto_import_products = fields.Boolean(string="Auto Import Products", default=True)
    auto_update_inventory = fields.Boolean(string="Auto Update Inventory", default=True)
    auto_update_order_status = fields.Boolean(string="Auto Update Order Status", default=True)
    auto_update_product_data = fields.Boolean(string="Auto Update Product data", default=True)
    auto_update_price = fields.Boolean(string="Auto Update Price", default=True)

    # Import last date
    last_woocommerce_inventory_import_date = fields.Datetime(srting='Last Inventory Import Time')
    last_woocommerce_product_import_date = fields.Datetime(srting='Last Product Import Time')
    last_woocommerce_product_attrs_import_date = fields.Datetime(srting='Last Product Attributes Import Time')
    last_woocommerce_order_import_date = fields.Date(srting='Last Order Import Time')

    last_woocommerce_refund_order_import_date = fields.Date(srting='Last Refund Order Import Time')

    last_woocommerce_msg_import_date = fields.Datetime(srting='Last Message Import Time')

    # Update last date
    woocommerce_last_update_category_date = fields.Datetime(srting='Woocom last update category date')
    woocommerce_last_update_inventory_date = fields.Datetime(srting='Woocom last update inventory date')
    woocommerce_last_update_catalog_rule_date = fields.Datetime(srting='Woocom last update catalog rule date')
    woocommerce_last_update_product_data_date = fields.Datetime(srting='Woocom last update product data rule date')
    woocommerce_last_update_order_status_date = fields.Datetime(srting='Woocom last update order status date')

    woocommerce_last_update_product_tag_date = fields.Datetime(srting='Woocom last update product tag date')
    woocommerce_last_update_coupon_date = fields.Datetime(srting='Woocom last update coupon date')

    # Export last date
    prestashop_last_export_product_data_date = fields.Datetime(string='Last Product Export Time')
    product_import_last_id = fields.Integer('Product Last Import Id')


    # @api.one
    def create_woo_attr(self, attr_val, wcapi):
        logger.info('create_woo_attrrrrrrrrrrrrrrrrr===> %s', attr_val)
        prod_att_obj = self.env['product.attribute']
        prod_attr_vals_obj = self.env['product.attribute.value']
        attribute_list = []
        attribute_val = {
            'name': attr_val.get('name'),
            'woocom_id': attr_val.get('id'),
            'company_id': self.env.company.id,
        }
        logger.info('attrs_valssssssssssss111111111===> %s', attribute_val)
        attrs_ids = prod_att_obj.search([('woocom_id', '=', attr_val.get('id'))])

        if not attrs_ids:
            att_id = prod_att_obj.create(attribute_val)
        else:
            attrs_ids[0].write(attribute_val)
            att_id = attrs_ids[0]

        # logger.info('Value ===> %s', att_id.name)
        attribute_value_rul = "products/attributes/" + str(attr_val.get('id')) + "/terms"
        attr_value_list = wcapi.get(attribute_value_rul)
        attr_value_list = attr_value_list.json()

        if attr_value_list.get('product_attribute_terms'):
            for attr_val in attr_value_list.get('product_attribute_terms'):

                attrs_op_val = {
                    'attribute_id': att_id.id,
                    'woocom_id': attr_val.get('id'),
                    'name': attr_val.get('slug'),
                    'company_id': self.env.company.id,
                }
                logger.info('attrs_valssssssssssss===> %s', attrs_op_val)
                attrs_ids = prod_attr_vals_obj.search(
                    [('woocom_id', '=', attr_val.get('id')), ('attribute_id', '=', att_id.id)])
                if attrs_ids:
                    attrs_ids[0].write(attrs_op_val)
                    # attribute_list.append(attrs_ids[0].id)
                else:
                    prod_attr_vals_obj.create(attrs_op_val)
                    # attribute_list.append(v_id.id)
            return attribute_list

    # @api.multi
    def importWoocomAttribute(self):
        # print ("IMPORT_ATRRRRRRRRRRRRRRr")
        # logger.info('importWoocomAttribute===>')
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=False, version='v3')
            #             try:
            r = wcapi.get("products/attributes")
            # logger.error('rrrrrrrrrr ===> %s', r.text)
            if not r.status_code:
                raise UserError(_("Enter Valid url"))
            attribute_list = r.json()
            logger.error('attribute_listattribute_list ===> %s', attribute_list)
            if attribute_list.get('product_attributes'):
                #                     try:
                for attribute in attribute_list.get('product_attributes'):
                    logger.info('attributeeeeeeeeeeeeeee===> %s', attribute)
                    shop.create_woo_attr(attribute, wcapi)
        #                     except Exception as e:
        #                         if self.env.context.get('log_id'):
        #                             log_id = self.env.context.get('log_id')
        #                             self.env['log.error'].create({'log_description': str(e) + " While Getting Atribute info of %s" % (attribute_list.get('product_attributes')), 'log_id': log_id})
        #                         else:
        #                             log_id = self.env['woocommerce.log'].create({'all_operations':'import_attribute', 'error_lines': [(0, 0, {'log_description': str(e) + " While Getting Atribute info of %s" % (attribute_list.get('product_attributes'))})]})
        #                             self = self.with_context(log_id=log_id.id)
        #             except Exception as e:
        #                 if self.env.context.get('log_id'):
        #                     log_id = self.env.context.get('log_id')
        #                     self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
        #                 else:
        #                     log_id = self.env['woocommerce.log'].create({'all_operations':'import_attributes', 'error_lines': [(0, 0, {'log_description': str(e)})]})
        #                     self = self.with_context(log_id=log_id.id)
        return True

    # @api.multi
    # def importWoocomAttribute(self):
    #     for shop in self:
    #             wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=False, version='v3')
    #         # try:
    #             count = 1
    #             r = wcapi.get("products/attributes")
    #             logger.error('rrrrrrrrrr ===> %s', r.text)
    #             if not r.status_code:
    #                 raise UserError(_("Enter Valid url"))
    #             attribute_list = r.json()
    #             while len(attribute_list) > 0:
    #                 if attribute_list.get('product_attributes'):
    #                     for attribute in attribute_list.get('product_attributes'):
    #                         shop.create_woo_attr(attribute, wcapi)
    #                         count+=1
    #                         attribute_list = wcapi.get("products/attributes?page="+ str(count))
    #                         attribute_list = attribute_list.json()
    #         # except Exception as e:
    #         #     print ("Error.............%s",e)
    #         #     pass
    #     return True

    # # @api.one
    # def get_categ_parent(self, category, wcapi):
    #     # print("==category==>",category)
    #     # logger.info('get_categ_parent===> %s', category)
    #     prod_category_obj = self.env['woocom.category']
    #     vals = {
    #         'woocom_id': str(category.get('id')),
    #         'name': category.get('name'),
    #     }
    #     category_check = prod_category_obj.search([('woocom_id', '=', category.get('parent'))])
    #     # logger.info('category_checkt===> %s', category_check)
    #     if not category_check:
    #         if int(category.get('parent')) == 0:
    #             vals.update({'parent_id': False})
    #         else:
    #             cat_url = 'products/categories/' + str(category.get('parent'))
    #             valsss = wcapi.get(cat_url)
    #             valsss = valsss.json()
    #             parent_id = self.get_categ_parent(valsss, wcapi)[0]
    #             vals.update({'parent_id': parent_id[0].id})
    #         parent_id = prod_category_obj.create(vals)
    #         # logger.info('Created Category ===> %s' % (parent_id.id))
    #         if parent_id:
    #             self.env.cr.execute(
    #                 "select categ_id from woocom_category_shop_rel where categ_id = %s and shop_id = %s" % (
    #                     parent_id.id, self.id))
    #             categ_data = self.env.cr.fetchone()
    #             if categ_data == None:
    #                 self.env.cr.execute("insert into woocom_category_shop_rel values(%s,%s)" % (parent_id.id, self.id))
    #         return parent_id
    #     else:
    #         parent_id = prod_category_obj.create(vals)
    #         if parent_id:
    #             self.env.cr.execute(
    #                 "select categ_id from woocom_category_shop_rel where categ_id = %s and shop_id = %s" % (
    #                     parent_id.id, self.id))
    #             categ_data = self.env.cr.fetchone()
    #             if categ_data == None:
    #                 self.env.cr.execute("insert into woocom_category_shop_rel values(%s,%s)" % (parent_id.id, self.id))
    #         return parent_id
    #
    # # @api.one
    # def create_woo_category(self, category, wcapi):
    #     # logger.info('create_woo_category===> %s', category)
    #
    #     prod_category_obj = self.env['woocom.category']
    #     category_check = prod_category_obj.search([('woocom_id', '=', category.get('id'))])
    #     if not category_check:
    #         vals = {
    #             'woocom_id': str(category.get('id')),
    #             'name': category.get('name'),
    #         }
    #         parent_category_check = prod_category_obj.search([('woocom_id', '=', category.get('parent'))])
    #         if not parent_category_check:
    #             # logger.info('==category.get(parent)fff==> %s', category.get('parent'))
    #             print("==category.get('parent')fff==>", category.get('parent'))
    #             if int(category.get('parent')) != 0:
    #                 cat_url = 'products/categories/' + str(category.get('parent'))
    #                 # logger.info('cat_url=========> %s', cat_url)
    #                 # print ("cat_url=========>",cat_url)
    #                 valsss = wcapi.get(cat_url)
    #                 valsss = valsss.json()
    #                 # print("==valsss==>",valsss)
    #                 # logger.info('==valsss==> %s', cat_url)
    #                 parent_id = self.get_categ_parent(valsss, wcapi)[0].id
    #             else:
    #                 parent_id = False
    #             vals.update({'parent_id': parent_id})
    #         else:
    #             vals.update({'parent_id': parent_category_check[0].id})
    #         # logger.info('Created vals ===> %s' % vals)
    #         cat_id = prod_category_obj.create(vals)
    #         # logger.info('Created Category ===> %s' % (cat_id.id))
    #         return cat_id
    #     else:
    #         vals = {
    #             'woocom_id': str(category.get('id')),
    #             'name': category.get('name'),
    #         }
    #         parent_category_check = prod_category_obj.search([('woocom_id', '=', category.get('parent'))])
    #         if not parent_category_check:
    #             if int(category.get('parent')) != int('0'):
    #                 cat_url = 'products/categories/' + str(category.get('parent'))
    #                 valsss = wcapi.get(cat_url)
    #                 valsss = valsss.json()
    #                 parent_id = self.get_categ_parent(valsss, wcapi)[0].id
    #             else:
    #                 parent_id = False
    #             vals.update({'parent_id': parent_id})
    #         else:
    #             vals.update({'parent_id': parent_category_check[0].id})
    #         category_check[0].write(vals)
    #         return category_check[0]
    #
    # # @api.multi
    # def importWooCategory(self):
    #     for shop in self:
    #             wcapi = API(url=shop.woocommerce_instance_id.location,
    #                     consumer_key=shop.woocommerce_instance_id.consumer_key,
    #                     consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
    #         # try:
    #             count = 1
    #             categ = wcapi.get("products/categories?page=" + str(count))
    #             if not categ.status_code:
    #                 raise UserError(_("Enter Valid url"))
    #             category_list = categ.json()
    #             # try:
    #             for category in category_list:
    #                 shop.create_woo_category(category, wcapi)
    #             while len(category_list) > 0:
    #                 count += 1
    #                 categ = wcapi.get("products/categories?page=" + str(count))
    #                 category_list = categ.json()
    #                 for category in category_list:
    #                     shop.create_woo_category(category, wcapi)
    #             # except Exception as e:
    #             #     if self.env.context.get('log_id'):
    #             #         log_id = self.env.context.get('log_id')
    #             #         self.env['log.error'].create({'log_description': str(
    #             #             e) + " While Getting product categories info of %s" % (
    #             #                                                              category_list.get('product_categories')),
    #             #                                       'log_id': log_id})
    #             #     else:
    #             #         log_id = self.env['woocommerce.log'].create({'all_operations': 'import_categories',
    #             #                                                      'error_lines': [(0, 0, {'log_description': str(
    #             #                                                          e) + " While Getting product categories info of %s" % (
    #             #                                                                                                     category_list.get(
    #             #                                                                                                         'product_categories'))})]})
    #         #             self = self.with_context(log_id=log_id.id)
    #         # except Exception as e:
    #         #     if self.env.context.get('log_id'):
    #         #         log_id = self.env.context.get('log_id')
    #         #         self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
    #         #     else:
    #         #         log_id = self.env['woocommerce.log'].create(
    #         #             {'all_operations': 'import_categories', 'error_lines': [(0, 0, {'log_description': str(e)})]})
    #         #         self = self.with_context(log_id=log_id.id)
    #     return True

    # @api.one
    def get_categ_parent(self, category, wcapi):
        #        print("==category==>",category)
        # logger.info('get_categ_parent===> %s', category)
        prod_category_obj = self.env['woocom.category']
        vals = {
            'woocom_id': str(category.get('id')),
            'name': category.get('name'),
        }
        # print ("valsssssssssssss",vals)
        category_check = prod_category_obj.search([('woocom_id', '=', category.get('parent'))])
        # logger.info('category_checkt===> %s', category_check)
        # print ("category_checkkkkkkkkkkkkkkkkk",category_check)

        if not category_check:
            if int(category.get('parent')) == 0:
                vals.update({'parent_id': False})
                # print ("IIIIFFFFFFFFF")
            else:
                # print ("ELSEEEEEEEEEEEEE***1",category.get('parent'))
                cat_url = 'products/categories/' + str(category.get('parent'))
                valsss = wcapi.get(cat_url)
                valsss = valsss.json()
                parent_id = self.get_categ_parent(valsss, wcapi)[0]
                vals.update({'parent_id': parent_id[0].id})
            parent_id = prod_category_obj.create(vals)
            # logger.info('Created Category ===> %s' % (parent_id.id))
            if parent_id:
                self.env.cr.execute(
                    "select categ_id from woocom_category_shop_rel where categ_id = %s and shop_id = %s" % (
                        parent_id.id, self.id))
                categ_data = self.env.cr.fetchone()
                if categ_data == None:
                    self.env.cr.execute("insert into woocom_category_shop_rel values(%s,%s)" % (parent_id.id, self.id))
            return parent_id
        else:
            parent_id = prod_category_obj.create(vals)
            if parent_id:
                self.env.cr.execute(
                    "select categ_id from woocom_category_shop_rel where categ_id = %s and shop_id = %s" % (
                        parent_id.id, self.id))
                categ_data = self.env.cr.fetchone()
                if categ_data == None:
                    self.env.cr.execute("insert into woocom_category_shop_rel values(%s,%s)" % (parent_id.id, self.id))
            return parent_id

    # @api.one
    def create_woo_category(self, category, wcapi):
        # logger.info('create_woo_category===> %s', category)

        prod_category_obj = self.env['woocom.category']
        category_check = prod_category_obj.search([('woocom_id', '=', category.get('id'))])
        if not category_check:
            vals = {
                'woocom_id': str(category.get('id')),
                'name': category.get('name'),
                'company_id': self.env.company.id,
            }
            parent_category_check = prod_category_obj.search([('woocom_id', '=', category.get('parent'))])
            if not parent_category_check:
                # logger.info('==category.get(parent)fff==> %s', category.get('parent'))
                #                print("==not parent_category_check==>",category.get('parent'))
                if int(category.get('parent')) != 0:
                    cat_url = 'products/categories/' + str(category.get('parent'))
                    # logger.info('cat_url=========> %s', cat_url)
                    # print ("cat_url=========>",cat_url)
                    valsss = wcapi.get(cat_url)
                    valsss = valsss.json()
                    #                    print("==valsss==>",valsss)
                    # logger.info('==valsss==> %s', cat_url)
                    parent_id = self.get_categ_parent(valsss, wcapi)[0].id
                else:
                    parent_id = False
                vals.update({'parent_id': parent_id})
            else:
                vals.update({'parent_id': parent_category_check[0].id})
            # logger.info('Created vals ===> %s' % vals)
            cat_id = prod_category_obj.create(vals)
            # logger.info('Created Category ===> %s' % (cat_id.id))
            return cat_id
        else:
            vals = {
                'woocom_id': str(category.get('id')),
                'name': category.get('name'),
            }
            parent_category_check = prod_category_obj.search([('woocom_id', '=', category.get('parent'))])
            if not parent_category_check:
                if int(category.get('parent')) != int('0'):
                    cat_url = 'products/categories/' + str(category.get('parent'))
                    valsss = wcapi.get(cat_url)
                    valsss = valsss.json()
                    parent_id = self.get_categ_parent(valsss, wcapi)[0].id
                else:
                    parent_id = False
                vals.update({'parent_id': parent_id})
            else:
                vals.update({'parent_id': parent_category_check[0].id})
            category_check[0].write(vals)
            return category_check[0]

    # @api.multi
    def importWooCategory(self):
        #        print ("importWooCategoryrrrrrrrrrrrrrrrrrr........")
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            # try:
            count = 1
            categ = wcapi.get("products/categories")  # ?page=" + str(count))
            print("categ.status_code", type(categ), categ.status_code)
            if not categ.status_code:
                raise UserError(_("Enter Valid url"))
            category_list = categ.json()
            # print("category_list", category_list)

            # try:
            for category in category_list:
                shop.create_woo_category(category, wcapi)
            while len(category_list) > 0:
                count += 1
                categ = wcapi.get("products/categories?page=" + str(count))
                category_list = categ.json()
                for category in category_list:
                    shop.create_woo_category(category, wcapi)
        #     except Exception as e:
        #         if self.env.context.get('log_id'):
        #             log_id = self.env.context.get('log_id')
        #             self.env['log.error'].create({'log_description': str(
        #                 e) + " While Getting product categories info of %s" % (
        #                                                                  category_list.get('product_categories')),
        #                                           'log_id': log_id})
        #         else:
        #             log_id = self.env['woocommerce.log'].create({'all_operations': 'import_categories',
        #                                                          'error_lines': [(0, 0, {'log_description': str(
        #                                                              e) + " While Getting product categories info of %s" % (
        #                                                                                                         category_list.get(
        #                                                                                                             'product_categories'))})]})
        #             self = self.with_context(log_id=log_id.id)
        # except Exception as e:
        #     if self.env.context.get('log_id'):
        #         log_id = self.env.context.get('log_id')
        #         self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
        #     else:category_list
        #         log_id = self.env['woocommerce.log'].create(
        #             {'all_operations': 'import_categories', 'error_lines': [(0, 0, {'log_description': str(e)})]})
        #         self = self.with_context(log_id=log_id.id)
        return True

    # @api.one
    def create_woocom_product(self, product, wcapi):
        print("CEATE PRODUCTTTTTTTTTTTT", product)
        logger.info('CEATE PRODUCTTTTTTTTTTTT===> %s', product)
        prod_temp_obj = self.env['product.template']
        product_obj = self.env['product.product']
        att_val_obj = self.env['product.attribute.value']
        att_obj = self.env['product.attribute']
        category_obj = self.env['woocom.category']
        tag_obj = self.env['product.tags']
        brand_obj = self.env['product.brands']
        product_att_line_obj = self.env['product.template.attribute.line']
        product_image_obj = self.env['product.images']

        print('product+++++++++++++++++', product)
        # print('expiry+++++++++++++++++', product.get('date_on_sale_to'))

        # print ("product.get('nameeeeeeeeeeeeeeeeeeeee')",product.get('name'))
        if product:
            prd_tmp_vals = {
                # 'name': product.get('name'),
                'type': 'product',
                # 'list_price': product.get('sale_price') and float(product.get('sale_price')) or 0.00,
                'list_price': product.get('price') and float(product.get('price')) or 0.00,
                'default_code': product.get('sku'),
                'description': product.get('short_description'),
                'woocom_regular_price': product.get('regular_price') and float(product.get('regular_price')) or 0.00,
                'woocom_id': product.get('id'),
                'woocom_price': product.get('price') and float(product.get('price')) or 0.00,
                'product_lngth': product.get('dimensions') and product.get('dimensions').get('length') or False,
                'product_width': product.get('dimensions') and product.get('dimensions').get('width') or False,
                'product_hght': product.get('dimensions') and product.get('dimensions').get('height') or False,
                'product_wght': product.get('weight') or False,
                'product_expiry': product.get('date_on_sale_to') or False,
                'company_id': self.env.company.id,
                'available_in_pos' : True,

            }
            print("prd_tmp_valsssssssssssssssssssss", prd_tmp_vals)

            if not product.get('name'):
                log_id = self.env['woocommerce.log'].create({'all_operations': 'import_products', 'error_lines': [
                    (0, 0, {'log_description': "The product having id = {} has no name.".format(product.get('id'))})]})
                # break
                return False
            else:
                prd_tmp_vals.update({'name': product.get('name')})

###################### NEW CUSTOMISATION FOR PRODUCT BRANDS########################
            brands = []
            print("<><><><><><><>product.get('brands')>>>>>>>>>>>>>", product.get('brands'))
            if product.get('brands'):
                for brand in product.get('brands'):
                    brand_ids = brand_obj.search([('woo_brand_id', '=', brand.get('id'))])
                    if brand_ids:
                        brands.append(brand_ids.id)
                    else:
                        brand_vals = {
                            'name': brand.get('name'),
                            'slug': brand.get('slug'),
                            'woo_brand_id': brand.get('id'),
                        }
                        brand_record = brand_obj.create(brand_vals)

                        if brand_record:
                            brands.append(brand_record.id)

                if brands:
                    prd_tmp_vals.update({'brand_ids': [(6, 0, brands)]})
            # print("<><><><><><><>brands>>>>>>>>>>>>>", brands)
            tags = []
            if product.get('tags'):
                for tag in product.get('tags'):
                    tag_ids = tag_obj.search([('tag_id', '=', tag.get('id'))])
                    if tag_ids:
                        tags.append(tag_ids[0].id)
                    else:
                        tag_vals = {
                            'name': tag.get('name'),
                            'slud_code': tag.get('slug'),
                            'description': tag.get('description'),
                            'tag_id': tag.get('id'),
                        }
                        tag_record = tag_obj.create(tag_vals)

                        if tag_record:
                            tags.append(tag_record.id)

                if tags:
                    prd_tmp_vals.update({'tag_ids': [(6, 0, tags)]})

            if product.get('categories'):
                categ = product.get('categories')
                if isinstance(product.get('categories'), dict):
                    categ = [categ]
                cat = product.get('categories')
                categ_ids = []
                for cat_id in cat:
                    print("<><><><>cat<><><>", cat_id)
                    cat_ids = category_obj.search([('woocom_id', '=', cat_id.get('id'))])
                    print("<><><><>cat_ids<><><>", cat_ids)
                    if cat_ids:
                        categ_id = cat_ids[0]
                        categ_ids.append(categ_id.id)
                        print("<><><><>categ_ids<><><>", categ_ids)
                        logger.info('product categ id ===> %s', categ_id.name)
                        prd_tmp_vals.update({'woo_categ': categ_id.id})
                        prd_tmp_vals.update({'woo_categories': [(6, 0, categ_ids)]})
                    else:
                        self.importWooCategory()
                        cat_ids = category_obj.search([('woocom_id', '=', cat.get('id'))])
                        if cat_ids:
                            prd_tmp_vals.update({'woo_categ': categ_id[0].id})
                            prd_tmp_vals.update({'woo_categories': [(6, 0, categ_ids)]})
            img_ids = []
            images_list = product.get('images')
            count = 1
            if images_list:
                for imgs in images_list:
                    loc = imgs.get('src').split('/')
                    image_name = loc[len(loc) - 1]
                    img_vals = {
                        'name': image_name,
                        'link': True,
                        'url': imgs.get('src'),
                        'woocom_img_id': imgs.get('id')
                    }

                if count == 1:
                    #     file_contain = urllib.request.urlopen(Request(imgs.get('src'),headers={'User-Agent': 'Mozilla/5.0'})).read()
                    #     image_data = base64.encodestring(file_contain)
                    #     prd_tmp_vals.update({'image_medium': image_data})
                    # img_ids.append((0, 0, img_vals))
                    # prd_tmp_vals.update({'woocom_product_img_ids':img_ids})
                    try:

                        # (filename, header) = urllib.request.urlretrieve(new_image2)
                        # s = ur.urlopen(new_img)
                        # f = s.read()
                        (filename, header) = urllib.request.urlretrieve(imgs.get('src'))
                        f = open(filename, 'rb')
                        img = base64.encodestring(f.read())
                        prd_tmp_vals.update({'image_1920': img})
                        f.close()
                    except:
                        pass
                img_ids.append((0, 0, img_vals))
            prd_tmp_vals.update({'woocom_product_img_ids': img_ids})

            # break
            #    attributes line
            at_lines = []

            for attrdict in product.get('attributes'):
                # logger.info('ATTRIBUTEEEEEEEEEEEEEEE===> %s', attrdict)
                attrs_ids = att_obj.search([('name', '=', attrdict.get('name'))])
                att_id = False
                if attrs_ids:
                    att_id = attrs_ids[0]
                    # logger.info('product attribute id ===> %s', att_id.name)
                else:
                    self.importWoocomAttribute()
                    attrs_ids = att_obj.search([('name', '=', attrdict.get('name'))])
                    if attrs_ids:
                        att_id = attrs_ids[0]
                if att_id:
                    value_ids = []
                    option = []
                    if attrdict.get('options'):
                        option = attrdict.get('options')
                    elif attrdict.get('option'):
                        option = attrdict.get('option')
                    if isinstance(option, dict):
                        option = [option]
                    for value in option:
                        # logger.info('forrrrrrrvalllllllllllOPTIONNNNNN===> %s', value)
                        v_ids = att_val_obj.search([('attribute_id', '=', att_id.id), ('name', '=', value.lower())])
                        if v_ids:
                            value_ids.append(v_ids[0].id)
                    if value_ids:
                        at_lines.append((0, 0, {
                            'attribute_id': att_id.id,
                            'value_ids': [(6, 0, value_ids)],
                        }))
            if at_lines:
                prd_tmp_vals.update({'attribute_line_ids': at_lines})
            temp_ids = prod_temp_obj.search([('woocom_id', '=', product.get('id'))])
            if temp_ids:
                temp_id = temp_ids[0]
                logger.info('product template id ===> %s', temp_id.name)
                new_lines = []
                if at_lines:
                    for variant_data in at_lines:
                        p_at_ids = product_att_line_obj.search(
                            [('attribute_id', '=', variant_data[2].get('attribute_id')),
                             ('product_tmpl_id', '=', temp_id.id)])
                        if p_at_ids:
                            v_data = [v.id for v in p_at_ids[0].value_ids]
                            new_vals = []
                            for vd in variant_data[2].get('value_ids')[0][2]:
                                if vd not in v_data:
                                    new_vals.append(vd)
                            if new_vals:
                                new_lines.append(
                                    (1, p_at_ids[0].id, {'attribute_id': variant_data[2].get('attribute_id'),
                                                         'value_ids': [(4, new_vals)]}))
                        else:
                            variant_data[2].update({'product_tmpl_id': temp_id.id})
                            product_att_line_obj.create(variant_data[2])
                            new_lines.append((0, 0, {'attribute_id': variant_data[2].get('attribute_id'),
                                                     'value_ids': variant_data[2].get('value_ids')[0][2]}))
                #                 prd_tmp_vals.pop('attribute_line_ids')
                F = prd_tmp_vals.copy()
                #             F.pop('image_medium')
                prd_tmp_vals.update({'attribute_line_ids': new_lines})
                # print ("VALSSSSSSSSPRODDD4444444444444444444DDDd",prd_tmp_vals)

                if prd_tmp_vals.get('woocom_product_img_ids'):
                    images_ids = []
                    for img in prd_tmp_vals.get('woocom_product_img_ids'):
                        img_ids = product_image_obj.search(
                            [('woocom_img_id', '=', img[2].get('woocom_img_id')), ('product_t_id', '=', temp_id[0].id)])
                        if not img_ids:
                            images_ids.append(img)
                    prd_tmp_vals.update({'woocom_product_img_ids': images_ids})

                temp_id.write(prd_tmp_vals)
                self.env.cr.commit()
            else:
                # try:
                # print ("VALSSSSSSSSPRODDDDDDd",prd_tmp_vals)
                # logger.info('VALSSSSSSSSPRODDDDDDd===> %s', prd_tmp_vals)
                temp_ids = prod_temp_obj.create(prd_tmp_vals)
                self._cr.commit()
                # except:
                #     log_id = self.env['woocommerce.log'].create({'all_operations': 'import_products', 'error_lines': [(0, 0,
                #                                                                                                        {
                #                                                                                                            'log_description': "The product having id = {} has less imaze size.".format(
                #                                                                                                                product.get(
                #                                                                                                                    'id'))})]})

            if product.get('variations'):
                for variation in product.get('variations'):
                    # logger.info('variationnnnnnnnnnnnnnnnnnn===> %s', variation)
                    # try:
                    url = "products/" + str(product.get('id')) + "/variations/" + str(variation)
                    vari = wcapi.get(url)
                    if not vari.status_code:
                        raise UserError(_("Enter Valid url"))
                    vari_data = vari.json()
                    op_ids = []
                    for var in vari_data.get('attributes'):
                        v_ids = att_val_obj.search([('name', '=', var.get('option').lower())])
                        if v_ids:
                            op_ids.append(v_ids[0].id)
                    if op_ids:
                        product_ids = product_obj.search(
                            [('product_tmpl_id.woocom_id', '=', product.get('id'))])
                        prod_id_var = False
                        if product_ids:
                            for product_data in product_ids:
                                prod_val_ids = product_data.product_template_attribute_value_ids.ids
                                prod_val_ids.sort()
                                get_val_ids = op_ids
                                get_val_ids.sort()
                                if get_val_ids == prod_val_ids:
                                    prod_id_var = product_data
                                    break
                        if prod_id_var:
                            vari_vals = {
                                'default_code': vari_data.get('sku'),
                                'product_lngth': vari_data.get('dimensions').get('length'),
                                'product_width': vari_data.get('dimensions').get('width'),
                                'product_hght': vari_data.get('dimensions').get('height'),
                                'product_wght': vari_data.get('dimensions').get('weight'),
                                'woocom_variant_id': vari_data.get('id'),
                                'list_price': vari_data.get('sale_price') and float(
                                    vari_data.get('sale_price')) or 0.00,
                                'woocom_regular_price': vari_data.get('regular_price') and float(
                                    vari_data.get('regular_price')) or 0.00,
                                'woocom_price': vari_data.get('price'),
                                'description': vari_data.get('short_description'),
                            }
                            # logger.info('vari_valsVALSSSSSSSS===> %s', vari_vals)
                            prod_id_var.write(vari_vals)
                            self.env.cr.commit()
                    self.env.cr.commit()
                    # print ("vari_valssssssss",vari_vals)
                    # except:
                    #     pass
        return True

    #                 return temp_id
    ############################IMPORT PRODUCT OLD FUNCTION WITHOUT ID WISE FILTER###############
    # @api.multi
    # def importWoocomProduct(self):
    #     # print ("IMPORTTTTPRODUCTTTTTTTT",self)
    #     logger.info('IMPORTTTTPRODUCTTTTTTTT===> %s', self)
    #     for shop in self:
    #         wcapi = API(url=shop.woocommerce_instance_id.location,
    #                     consumer_key=shop.woocommerce_instance_id.consumer_key,
    #                     consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
    #         count = 1
    #         prod = wcapi.get("products?page=" + str(count))
    #         if not prod.status_code:
    #             raise UserError(_("Enter Valid url"))
    #         product_list = prod.json()
    #         print('product_list+++++++++++++++', product_list)

    #         for product in product_list:
    #             # logger.info('product1111111111111===> %s', product)
    #             shop.create_woocom_product(product, wcapi)
    #         while len(product_list) > 0:
    #             count += 1
    #             prod = wcapi.get("products?page=" + str(count))
    #             product_list = prod.json()
    #             for product in product_list:
    #                 # logger.info('product22222222222222===> %s', product)
    #                 shop.create_woocom_product(product, wcapi)
    #     return True

    ##########################IMPORT PRODUCT ID WISE############################
    def importWoocomProduct(self):
        # print ("IMPORTTTTPRODUCTTTTTTTT",self)
        logger.info('IMPORTTTTPRODUCTTTTTTTT===> %s', self)
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')

            # prod = wcapi.get("products?after:" + str(shop.last_woocommerce_product_import_date))
            # if not prod.status_code:
            #     raise UserError(_("Enter Valid url"))
            # product_list = prod.json()
            # for product in product_list:
            #     shop.create_woocom_product(product, wcapi)
            #     aa = product.get('date_modified').split('T')
            #     bb = aa[0] + ' ' + aa[1]
            #     shop.write({'last_woocommerce_product_import_date': bb})

            product_import_id = shop.product_import_last_id
            # print("<><><><>product_import_id<><>>", product_import_id)
            compare_to_import_pro = product_import_id + 300
            # print("<><><><>compare_to_import_pro<><>>", compare_to_import_pro)
            while product_import_id < compare_to_import_pro:
                product_import_id += 1
                prod = wcapi.get("products?include=" + str(product_import_id))
                if not prod.status_code:
                    raise UserError(_("Enter Valid url"))
                product_list = prod.json()
                for product in product_list:
                    shop.create_woocom_product(product, wcapi)
                    print('\nproduct+++++++++++++++', product.get('id'), product.get('name'))
                shop.write({'product_import_last_id': product_import_id})            
        return True

##########################IMPORT TAXES NEW CUSTOMIZATION##############################
    def create_taxes(self, tax_list, wcapi):
        tax_obj = self.env['account.tax']
        country_obj = self.env['res.country']
        for tax in tax_list:
            country_id = country_obj.search([('code', '=', tax.get('country'))])
            name = 'BTW(' + str(float(tax.get('rate'))) + '%)'
            vals = {
                'name': name,
                'wocomm_tax_id': tax.get('id'),
                'type_tax_use': 'sale',
                'amount': tax.get('rate'),
                'amount_type': 'percent',
                'country_id': country_id.id,
                'active': True,
            }
            tax_id = tax_obj.search([('wocomm_tax_id', '=', tax.get('id'))])
            if not tax_id:
                tax_obj.create(vals)
            else:
                tax_obj.write(vals)


    def importTaxes(self):
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            # print ("WCPIIIIIII22222",wcapi)
            count = 1
            products = wcapi.get("taxes")
            if products.status_code != 200:
                raise UserError(_("Enter Valid url"))

            tax_list = products.json()
            # print('tax_list+++++++++++', tax_list)
            shop.create_taxes(tax_list, wcapi)

        return True
        
    # @api.one
    def create_woo_inventory(self, loc_id, qty, product):
        print("create_woo_inventoryyyyyy", qty, product)
        stock_quant = self.env['stock.quant']
        inventory_obj = self.env['stock.change.product.qty']
        print("_______________oc_id_____________", loc_id, product, qty)
        if qty > 0:
            inventory_id = inventory_obj.create({
                # 'location_id' : loc_id,
                'new_quantity': qty,
                'product_id': product[0].id,
                'product_tmpl_id': product.product_tmpl_id.id,
            })
            print("inventory_id", inventory_id)
            inventory_id.change_product_qty()
            self.env.cr.commit()
        # print ("inv_wizardddddd",inv_wizard)
        # inv_wizard.change_product_qty()
        # return True

    # @api.multi
    def CreateWoocomInventory(self, product_list, wcapi):
        print("CreateWoocomInventoryyyyyyyyyyyy")

        inventory_list = []
        for prod_dict in product_list:
            print("prod_dictprod_dictprod_dictprod_dict", prod_dict)
            if isinstance(prod_dict, dict):
                print("prod_dictttttttttttttttttttt")
                product_vrt = prod_dict.get('variations', [])
                if product_vrt:
                    # print ("iiiiiffffffffproduct_vrt")
                    for variant in product_vrt:
                        prod_url = 'products/' + str(prod_dict.get('id')) + "/variations/" + str(variant)
                        products_data = wcapi.get(prod_url)
                        product_dict = products_data.json()
                        if products_data.status_code != 200:
                            raise UserError(_("Enter Valid url"))

                        prod_ids = self.env['product.product'].search([('woocom_variant_id', '=', variant)])
                        # print ("prodidssssss1111111111",prod_ids,prod_ids.name)

                        if prod_ids:
                            p_id = prod_ids[0]
                            # print ("iiiiffffffprodidsssss",p_id)
                            logger.info('product invent id ===> %s', p_id.name)
                        else:
                            data = self.create_woocom_product(product_dict, wcapi)
                            if not data:
                                continue

                            prod_ids = self.env['product.product'].search([('woocom_variant_id', '=', variant)])
                            # print ("elseeeeprod_idsssssss222222222",prod_ids,prod_ids.name)
                            if prod_ids:
                                p_id = prod_ids[0]
                                # print ("iiiiffffffprodidsssss22222222",p_id)
                        if p_id:
                            # print ("PIDDDDDDDDDDDD",p_id)
                            # print ("product_dict.get('stock_quantity11111')",product_dict.get('stock_quantity'))

                            if product_dict.get('stock_quantity'):
                                self.create_woo_inventory(self.warehouse_id.lot_stock_id.id,
                                                          product_dict.get('stock_quantity'), p_id)
                            else:
                                # print ("elseeeeeeeeeee*******")
                                continue
                else:
                    print("======ELSEEEEEEEE=========")
                    p_id = False
                    pro_ids = self.env['product.product'].search(
                        [('product_tmpl_id.woocom_id', '=', prod_dict.get('id'))])
                    # print ("pro_idsELSEEEEEEEEEE1111111111111",pro_ids,pro_ids.name)
                    # logger.info('wcapiiiiiiiiiiiiiiiii===> %s', wcapi)

                    if pro_ids:
                        p_id = pro_ids[0]
                        # print ("ELSEEEEEEEEpidddddddddddd",p_id)
                        # logger.info('1111111111111111111===> %s', p_id)

                    else:
                        product_url = 'products/' + str(prod_dict.get('id'))
                        products_data = wcapi.get(product_url)
                        if products_data.status_code != 200:
                            raise UserError(_("Enter Valid url"))

                        product_dict = products_data.json()
                        # logger.info('22222222222222222222222===>')
                        data = self.create_woocom_product(product_dict.get('product'), wcapi)
                        # logger.info('33333333333333333333333==>')
                        if not data:
                            continue

                        pro_ids = self.env['product.product'].search(
                            [('product_tmpl_id.woocom_id', '=', prod_dict.get('id'))])
                        # print ("pro_idsEELSEEEEEEEEE222222222222",pro_ids,pro_ids.name)

                        if pro_ids:
                            p_id = pro_ids[0]
                            # print ("pro_idsiiiiidddddddddELSEEEEEEEEEiffffff",pro_ids)

                    if p_id:
                        # print ("=======pro_idddd",p_id)
                        # print ("=======stock_quantity",prod_dict.get('stock_quantity'))

                        if prod_dict.get('stock_quantity'):
                            self.create_woo_inventory(self.warehouse_id.lot_stock_id.id,
                                                      prod_dict.get('stock_quantity'), p_id)
                        else:
                            continue

    # @api.multi
    def importWoocomInventory(self):
        print("importWoocomInventoryyyyyyyyyy")

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            # print ("WCPIIIIIII22222",wcapi)
            count = 1
            products = wcapi.get("products")
            if products.status_code != 200:
                raise UserError(_("Enter Valid url"))

            product_list = products.json()
            while len(product_list) > 0:
                # print ("LENNNNNNNNNNNNN------",len(product_list))

                shop.CreateWoocomInventory(product_list, wcapi)
                # print ("count1111111111------",count)

                count += 1
                # print ("count2222222222------",count)

                url = "products?page=" + str(count)
                # print ("urlllllllllllllll----",url)

                products = wcapi.get("products?page=" + str(count))
                # print ("PRODUCTSSSSSSSSS-----",products)

                product_list = products.json()
                # print ("product_listtttt-----",product_list)
        return True

    # @api.one
    def create_woo_customer(self, customer_detail, wcapi):
        print("customer_detailcustom=====================", customer_detail)
        # logger.info('create_woo_customereeeeeeee=======>>> %s', customer_detail)

        res_partner_obj = self.env['res.partner']
        country_obj = self.env['res.country']
        state_obj = self.env['res.country.state']
        account_receive_id = self.env['account.account'].search(
            [('user_type_id.type', '=', 'receivable'), ('company_id', '=', self.env.user.company_id.id)])
        account_pay_id = self.env['account.account'].search(
            [('user_type_id.type', '=', 'payable'), ('company_id', '=', self.env.user.company_id.id)])

        if customer_detail == None:
            cust_id = res_partner_obj.search([('name', '=', 'Guest Customer')])

        if customer_detail != None:

            country_ids = False
            bcountry = customer_detail.get('billing').get('country')
            if bcountry != 'False':
                country_ids = country_obj.search([('code', '=', bcountry)])
                if not country_ids:
                    country_id = country_obj.create({'name': bcountry, 'code': bcountry}).id
                    # logger.info('country id 111===> %s', country_id)
                else:
                    country_id = country_ids.id
                    # logger.info('country id 222===> %s', country_id)
            else:
                country_id = False

            bstate = customer_detail.get('billing').get('state')
            if bstate != 'False':
                state_ids = state_obj.search([('country_id', '=', country_id), ('code', '=', bstate)])
                if not state_ids:
                    state_id = state_obj.create({'name': bstate, 'code': bstate, 'country_id': country_id}).id
                    # logger.info('state id 111===> %s', state_id)
                else:
                    state_id = state_ids.id
                    # logger.info('state id 222===> %s', state_id)
            else:
                state_id = False

            #         if customer_detail.get('first_name') or customer_detail.get('last_name'):
            #            Customize code Dee
            add_lines = []
            vals = {}
            name = ''
            if customer_detail.get('first_name') and customer_detail.get('last_name'):
                name += customer_detail.get('first_name') + ' ' + customer_detail.get('last_name')
            elif customer_detail.get('first_name'):
                name += customer_detail.get('first_name')
            else:
                name += customer_detail.get('last_name')
            if customer_detail.get('billing').get('company') and customer_detail.get('billing').get(
                    'company') != 'False':
                #                print('----------------------',customer_detail.get('billing').get('company'))
                vals = {
                    'woocom_id': customer_detail.get('id'),
                    'name': customer_detail.get('billing').get('company') or customer_detail.get('username'),
                    # 'customer': True,
                    'company_type': 'company',
                    'property_account_receivable_id': account_receive_id[0].id if account_receive_id else False,
                    'property_account_payable_id': account_pay_id[0].id if account_pay_id else False,
                }
                add_lines.append((0, 0, {
                    'woocom_id': customer_detail.get('id'),
                    'name': name,
                    # 'customer': True,
                    # 'supplier': False,
                    'street': customer_detail.get('billing') and customer_detail.get('billing').get('address_1') or '',
                    'street2': customer_detail.get('billing').get('address_2'),
                    'city': customer_detail.get('billing').get('city'),
                    'zip': customer_detail.get('billing').get('postcode'),
                    'phone': customer_detail.get('billing').get('phone'),
                    'state_id': state_id,
                    'country_id': country_id,
                    'email': customer_detail.get('email'),
                    'website': customer_detail.get('website'),
                    'type': 'invoice',
                    #                    'property_account_receivable_id': account_receive_id[0].id if account_receive_id else False,
                    #                    'property_account_payable_id': account_pay_id[0].id if account_pay_id else False,
                }))
            else:
                #                print('==================')
                vals = {
                    'woocom_id': customer_detail.get('id'),
                    'name': name,
                    # 'customer': True,
                    # 'supplier': False,
                    'street': customer_detail.get('billing') and customer_detail.get('billing').get('address_1') or '',
                    'street2': customer_detail.get('billing').get('address_2'),
                    'city': customer_detail.get('billing').get('city'),
                    'zip': customer_detail.get('billing').get('postcode'),
                    'phone': customer_detail.get('billing').get('phone'),
                    'state_id': state_id,
                    'country_id': country_id,
                    'email': customer_detail.get('email'),
                    'website': customer_detail.get('website'),
                    'property_account_receivable_id': account_receive_id[0].id if account_receive_id else False,
                    'property_account_payable_id': account_pay_id[0].id if account_pay_id else False,
                }
            #            print('=============vvvvvvvvvvvvvvvvv',vals)
            #            uuuuuuuuuuuuuuuuuuuuuuu
            # logger.info('valsssssssssssss===> %s', vals)
            ####

            scountry = customer_detail.get('shipping').get('country')
            if scountry != 'False':
                scountry_ids = country_obj.search([('code', '=', scountry)])
                if not scountry_ids:
                    scountry_id = country_obj.create({'name': scountry, 'code': scountry}).id
                    # logger.info('ssscountry id111 ===> %s', scountry_id)
                else:
                    scountry_id = scountry_ids[0].id
                    # logger.info('ssscountry id222 ===> %s', scountry_id)
            else:
                scountry_id = False

            sstate = customer_detail.get('shipping').get('state')
            if sstate != 'False':
                sstate_ids = state_obj.search([('code', '=', sstate)])
                if not sstate_ids:
                    sstate_id = state_obj.create({'name': sstate, 'code': sstate, 'country_id': scountry_id}).id
                    # logger.info('sssstate id000 ===> %s', sstate_id)
                else:
                    sstate_id = sstate_ids[0].id
                    # logger.info('sstate id ===> %s', sstate_id)
            else:
                sstate_id = False

            if customer_detail.get('shipping').get('city'):
                name = ''
                if customer_detail.get('shipping').get('first_name') and customer_detail.get('shipping').get(
                        'last_name'):
                    name += customer_detail.get('shipping').get('first_name') + ' ' + customer_detail.get(
                        'shipping').get('last_name')
                elif customer_detail.get('shipping').get('first_name'):
                    name += customer_detail.get('shipping').get('first_name')
                else:
                    name += customer_detail.get('shipping').get('last_name')
                add_lines.append((0, 0, {
                    'woocom_id': customer_detail.get('id'),
                    'name': name,
                    'street': customer_detail.get('shipping').get('address_1'),
                    'street2': customer_detail.get('shipping').get('address_2'),
                    'city': customer_detail.get('shipping').get('city'),
                    'zip': customer_detail.get('shipping').get('postcode'),
                    'phone': customer_detail.get('shipping').get('phone'),
                    'country_id': scountry_id,
                    'state_id': sstate_id,
                    'type': 'delivery',
                }))

            vals.update({'child_ids': add_lines})
            customer_ids = res_partner_obj.search(
                [('woocom_id', '=', customer_detail.get('id')), ('email', '=', customer_detail.get('email'))])
            # logger.info('customer_idssssssssssssssss==> %s', customer_ids)
            # print ("customer_ids1111111111",customer_ids)
            if not customer_ids:
                #                print('=========valsvalsvalsvals',vals)
                #                djkhfsj
                cust_id = res_partner_obj.create(vals)
                # logger.info('customer_id1111==> %s', cust_id)
                # print ("customer_ids222222",cust_id)
            else:
                #                sdfhpi
                cust_id = customer_ids[0]
                # logger.info('customer_id2222===> %s', cust_id)
                vals.pop('child_ids')
                cust_id.write(vals)
            if cust_id:
                # logger.info('iiifffffffcust_id===> %s', cust_id)
                # print ("customer_ids444444444",cust_id)
                self.env.cr.execute(
                    "select cust_id from customer_shop_rel where cust_id = %s and shop_id = %s" % (cust_id.id, self.id))
                cust_data = self.env.cr.fetchone()
        self.env.cr.commit()
        return cust_id

    # @api.multi
    def importWoocomCustomer(self):

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            # logger.info('wcapiiiiiiiiiiiiiiiii===> %s', wcapi)

            count = 1
            customers = wcapi.get("customers?page=" + str(count))
            # logger.info('CUSTtttttttttttt===> %s', customers)

            if customers.status_code != 200:
                raise UserError(_("Enter Valid url"))
            customer_list = customers.json()
            # logger.info('customer_listtttttt===> %s', customer_list)

            # print("===customer_list=>",customer_list)
            for custm in customer_list:
                # logger.info('custmmmmmmmmmmmmm===> %s', custm)
                shop.create_woo_customer(custm, wcapi)

            while len(customer_list) > 0:
                # logger.info('whileeeeeeeeeeeeeee===> %s', len(customer_list))
                count += 1
                custm = wcapi.get("customers?page=" + str(count))
                # logger.info('CUSTtttttttttttt222222222===> %s', custm)

                customer_list = custm.json()
                # logger.info('customer_listttttt2222222222===> %s', customer_list)

                for custm in customer_list:
                    # logger.info('custmmmmmmmmmmmmm2222222222222===> %s', custm)
                    shop.create_woo_customer(custm, wcapi)
        return True

    # @api.one
    def create_woo_carrier(self, carrier, wcapi):
        carrier_obj = self.env['delivery.carrier']
        partner_obj = self.env['res.partner']
        product_obj = self.env['product.product']
        carrier_list_ids = []

        partner_ids = partner_obj.search([('name', '=', carrier.get('title'))])
        if partner_ids:
            partner_id = partner_ids[0]
        else:
            partner_id = partner_obj.create({'name': carrier.get('title')})
        prod_ids = product_obj.search([('name', '=', carrier.get('title'))])
        if prod_ids:
            prod_ids = prod_ids[0]
        else:
            prod_ids = product_obj.create({'name': carrier.get('title')})
        carr_vals = {
            'name': carrier.get('title'),
            # 'partner_id': partner_id.id,
            'woocom_id': carrier.get('id'),
            'product_id': prod_ids.id
        }
        car_ids = carrier_obj.search([('woocom_id', '=', carrier.get('id'))])
        if not car_ids:
            carrier_id = carrier_obj.create(carr_vals)
        else:
            carrier_id = car_ids[0]
            logger.info('carrier id ===> %s', carrier_id.name)
            carrier_id.write(carr_vals)
        self.env.cr.commit()
        return carrier_id

    # @api.multi
    def importWoocomCarrier(self):
        print("IMPORTCARRRRRRRR")
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            carriers = wcapi.get("shipping_methods")
            if carriers.status_code != 200:
                raise UserError(_("Enter Valid url"))
            carriers_list = carriers.json()
            for carrier in carriers_list:
                shop.create_woo_carrier(carrier, wcapi)
        return True

    # @api.one
    def create_woo_payment_method(self, payment, wcapi):
        payment_obj = self.env['payment.gatway']
        pay_ids = payment_obj.search([('woocom_id', '=', payment.get('id'))])
        pay_vals = {
            'title': payment.get('title'),
            'woocom_id': payment.get('id'),
            'descrp': payment.get('description'),
        }
        pay_ids.write(pay_vals)
        if not pay_ids:
            payment_id = payment_obj.create(pay_vals)
            payment_id.write(pay_vals)
        self.env.cr.commit()

    # @api.multi
    def importWooPaymentMethod(self):

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            payment_methods = wcapi.get("payment_gateways")
            if payment_methods.status_code != 200:
                raise UserError(_("Enter Valid url"))
            payments_list = payment_methods.json()
            for payment in payments_list:
                shop.create_woo_payment_method(payment, wcapi)
        return True

    def woocomManageOrderWorkflow(self, saleorderid, order_detail, status):
        print("WORKFLOWWWWWWWWWWW")

        invoice_obj = self.env['account.move']
        invoice_refund_obj = self.env['account.move.reversal']
        return_obj = self.env['stock.return.picking']
        return_line_obj = self.env['stock.return.picking.line']

        if order_detail.get('status') == 'cancelled':
            if saleorderid.state in ['draft']:
                saleorderid.action_cancel()

            #            if saleorderid.state in ['progress', 'done', 'manual']:
            else:
                invoice_ids = saleorderid.invoice_ids
                for invoice in invoice_ids:
                    refund_ids = invoice_obj.search([('origin', '=', invoice.number)])
                    # print  "==refund_ids==>",refund_ids
                    if not refund_ids:
                        if invoice.state == 'posted':
                            refund_invoice_id = invoice_refund_obj.create(dict(
                                reason='Refund To %s' % (invoice.partner_id.name),
                                date=datetime.date.today(),
                                refund_method='refund'
                            ))
                            refund_invoice_id.revers_moves()
                            saleorderid.write({'is_refund': True})
                        else:
                            invoice.action_cancel()

                for picking in saleorderid.picking_ids:
                    if picking.state not in ('done'):
                        picking.action_cancel()
                    # else:
                    #     ctx = self._context.copy()
                    #     ctx.update({'active_id': picking.id})
                    #     res = return_obj.with_context(ctx).default_get(['product_return_moves', 'move_dest_exists'])
                    #     res.update({'invoice_state': '2binvoiced'})
                    #     return_id = return_obj.with_context(ctx).create({'invoice_state': 'none'})
                    #     for record in res['product_return_moves']:
                    #         record.update({'wizard_id': return_id.id})
                    #         return_line_obj.with_context(ctx).create(record)
                    #
                    #     pick_id_return, type = return_id.with_context(ctx)._create_returns()
                    #     pick_id_return.action_assign()
                    #     pick_id_return.action_done()
            saleorderid.action_cancel()
            return True

        # ==== My code from here to make "Refund" sale orders to confirm and its invocie  and delivery created====#

        if not self.workflow_id:
            print("======else Workflow=======>>>", order_detail.get('status'))
            if order_detail.get('status') == 'refunded':
                if saleorderid.state == 'draft':
                    saleorderid.action_confirm()

                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid._create_invoices()
                    invoice_ids = invoice_obj.browse(invoice_ids)
                    invoice_ids.write({'is_woocom': True})

                for invoice_id in saleorderid.invoice_ids:
                    if invoice_id.state == 'draft':
                        # print "invoice state is draft"
                        invoice_id.action_post()

                    if invoice_id.state not in ['paid'] and invoice_id.invoice_line_ids:
                        invoice_id.pay_and_reconcile(self.sale_journal or self.env['account.journal'].search(
                            [('type', '=', 'bank')], limit=1), invoice_id.amount_total)

        #  =========My code till here    ===========  #

        if self.workflow_id:

            if self.workflow_id.validate_order:
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()

            # if complete shipment is activated in workflow
            if self.workflow_id.complete_shipment:

                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()

                for picking_id in saleorderid.picking_ids:
                    # If still in draft => confirm and assign
                    if picking_id.state == 'draft':
                        picking_id.action_confirm()
                        picking_id.action_assign()

                    if picking_id.state == 'confirmed':
                        picking_id.action_assign()
                        # picking_id.button_validate()

            # if create_invoice is activated in workflow
            if self.workflow_id.create_invoice:
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()
                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid._create_invoices()
                    print("invoice_idsinvoice_ids>>>21111111111111111>>>>>>>>>>>>>>>>", invoice_ids)
                    # invoice_ids = invoice_obj.browse(invoice_ids)
                    print("invoice_idsinvoice_ids>>>>>>>>>>>>>>>>>>>", invoice_ids)
                    invoice_ids.write({'is_woocom': True})

            # if validate_invoice is activated in workflow
            if self.workflow_id.validate_invoice:
                if saleorderid.state == 'draft':
                    saleorderid.action_confirm()

                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid._create_invoices()
                    # invoice_ids = invoice_obj.browse(invoice_ids)
                    invoice_ids.write({'is_woocom': True})

                for invoice_id in saleorderid.invoice_ids:
                    if invoice_id.state == 'draft':
                        invoice_id.action_post()

            # if register_payment is activated in workflow
            if self.workflow_id.register_payment:
                if saleorderid.state == 'draft':
                    saleorderid.action_confirm()
                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid._create_invoices()
                    # invoice_ids = invoice_obj.browse(invoice_ids)
                    invoice_ids.write({'is_woocom': True})

                for invoice_id in saleorderid.invoice_ids:
                    if invoice_id.state == 'draft':
                        # print "invoice state is draft"
                        invoice_id.action_post()
                    if invoice_id.state not in ['posted'] and invoice_id.invoice_line_ids:
                        invoice_id.pay_and_reconcile(
                            self.workflow_id and self.sale_journal or self.env['account.journal'].search(
                                [('type', '=', 'bank')], limit=1), invoice_id.amount_total)
            return True

        else:
            print("======else Another Workflow=======>>>", order_detail.get('status'))
            if order_detail.get('status') == 'on-hold':
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()

                for picking_id in saleorderid.picking_ids:
                    # If still in draft => confirm and assign
                    if picking_id.state == 'draft':
                        picking_id.action_confirm()
                        picking_id.action_assign()

                    if picking_id.state == 'confirmed':
                        picking_id.action_assign()
                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid._create_invoices()


            elif order_detail.get('status') == 'failed':
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()

                for picking_id in saleorderid.picking_ids:
                    # If still in draft => confirm and assign
                    if picking_id.state == 'draft':
                        picking_id.action_confirm()
                        picking_id.action_assign()

                    if picking_id.state == 'confirmed':
                        picking_id.action_assign()

            elif order_detail.get('status') == 'processing':
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()

                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid._create_invoices()

                for invoice_id in saleorderid.invoice_ids:
                    if invoice_id.state == 'draft':
                        invoice_id.action_post()
                    if invoice_id.state not in ['posted'] and invoice_id.invoice_line_ids:
                        invoice_id.pay_and_reconcile(
                            self.sale_journal or self.env['account.journal'].search(
                                [('type', '=', 'bank')], limit=1), invoice_id.amount_total)

            elif order_detail.get('status') == 'pending':
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()

                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid._create_invoices()


            elif order_detail.get('status') == 'completed':
                print("insideeeeeeeeeeeeeeeeeeeeeeeeee")
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()
                    print("insideeeeeeeeeeeeeeeeeeeeeeeeee222222222222")
                for picking_id in saleorderid.picking_ids:
                    if picking_id.state == 'draft':
                        picking_id.action_confirm()
                        for pick in picking_id.move_line_ids:
                            pick.qty_done = pick.product_uom_qty
                        picking_id.action_assign()
                        picking_id.button_validate()

                    if picking_id.state == 'confirmed':
                        print("insideeeeeeeeeconfirmedconfirmedeeee333333333")
                        for pick in picking_id.move_line_ids:
                            print("===picking_id.move_line_ids>>>>")
                            pick.qty_done = pick.product_uom_qty
                        picking_id.action_assign()
                        picking_id.button_validate()

                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid._create_invoices()

                for invoice_id in saleorderid.invoice_ids:
                    if invoice_id.state == 'draft':
                        invoice_id.action_post()
                    if invoice_id.state not in ['paid'] and invoice_id.invoice_line_ids:
                        invoice_id.pay_and_reconcile(
                            self.sale_journal or self.env['account.journal'].search(
                                [('type', '=', 'bank')], limit=1), invoice_id.amount_total)

                saleorderid.action_done()

    # @api.one
    def woocomManageCoupon(self, orderid, coupon_detail, wcapi):
        print("woocomManageCouponnnnnnnnn")

        sale_order_line_obj = self.env['sale.order.line']
        coupon_obj = self.env['woocom.coupons']
        product_obj = self.env['product.product']

        for coupon_value in coupon_detail:
            # print ("FORRRRcoupon_valueeeeee",coupon_value)
            c_id = False
            # c_ids = coupon_obj.search([('coupon_id','=', coupon_value.get('id'))])

            c_ids = coupon_obj.search(
                ['|', ('coupon_id', '=', coupon_value.get('id')), ('coupon_code', '=', coupon_value.get('code'))])
            # print("c_idsssssssss1111111111",c_ids)
            if c_ids:
                c_id = c_ids[0]
                # print("IIIIIIFFFFFFFc_idsssssss",c_ids)
            else:
                url = 'coupons/' + str(coupon_value.get('id'))
                # print("URLLLLLLLLLL",url)

                coupons_data = wcapi.get(url)
                # print("coupons_data11111111111",coupons_data)

                coupons_data = coupons_data.json()
                # print("coupons_data222222222222",coupons_data)

                c_id = coupon_obj.create({
                    'coupon_id': coupon_value.get('id'),
                    'coupon_code': coupon_value.get('code'),
                    # 'description': coupon_value.get('description'),
                })
                # print ("C_IDVALSSSSSSSSSSSS",c_id,coupon_value.get('id'),coupon_value.get('code'),coupon_value.get('description'))

                self._cr.commit()

            p_id = False
            p_ids = product_obj.search([('name', '=', 'Coupon'), ('type', '=', 'service')])
            # print ("P_IDSSSSSSSSSSSS",p_id)

            if p_ids:
                p_id = p_ids[0]
                # print ("iiiffffffffP_IDSSSSSSSSSSS",p_id)
            else:
                p_id = product_obj.create({
                    'name': 'Coupon',
                    'type': 'service'
                })
                # print ("elseeeeeeeeP_IDSSSSSSSSSS",p_id)
                self._cr.commit()

            line = {
                'product_id': p_id and p_id.id,
                'price_unit': -float(coupon_value.get('discount')),

                # 'name': c_id.description,

                'name': p_id.name,
                'product_uom_qty': 1,
                'order_id': orderid.id,
                'tax_id': False,
                'woocom_id': coupon_value.get('id'),
                'product_uom': p_id and p_id.uom_id.id
            }
            # print ("LINEEEEEEEEE",line)

            line_ids = sale_order_line_obj.search(
                [('order_id', '=', orderid.id), ('woocom_id', '=', coupon_value.get('id'))])
            if line_ids:
                line_id = line_ids[0]
                # print ("line_idsssssssssss",line_ids)
                # logger.info('order line id ===> %s', line_id.name)
                # line_id.write(line)
            else:
                # print "====elseeeeeeline===>",line
                line_id = sale_order_line_obj.create(line)
            self.env.cr.commit()
        return True

    #    @api.one
    def woocomManageOrderLines(self, orderid, order_detail, wcapi):
        # logger.info('woocomManageOrderLinesssssssssssssss===> %s', orderid,order_detail)
        #         print ("woocomManageOrderLineseeeeeeeee",orderid,order_detail)

        print('orderid+++++++++++++++++', orderid)
        print('order_detail+++++++++++++++++', order_detail)
        print('order_detail+++++++++++++++++', order_detail.get('shipping').get('country'))
        country_code = order_detail.get('shipping').get('country')

        sale_order_line_obj = self.env['sale.order.line']
        prod_attr_val_obj = self.env['product.attribute.value']
        prod_templ_obj = self.env['product.template']
        product_obj = self.env['product.product']
        carrier_obj = self.env['delivery.carrier']
        account_obj = self.env['account.tax']
        line = []
        #         for shipping_charge in order_detail.get('shipping_lines'):
        if order_detail.get('fee_lines'):
            for g_wrap in order_detail.get('fee_lines'):
                print("AAAAAAAg_wrapAAAa", g_wrap)
                tax_id = []
                if g_wrap.get('taxes'):
                    tax_id = self.with_context({'shipping_tax': g_wrap.get('total_tax')}).getTaxesAccountID(
                        g_wrap.get('total_tax'), country_code)
                    print("tax_idtax_id99999999999999999999999", tax_id)
                    if not tax_id == [False]:
                        tax_id = [(6, 0, [tax_id[0].id])]
                    else:
                        tax_id = []

                line = {
                    'product_id': self.gift_wrapper_fee_product_id.id,
                    'price_unit': float(g_wrap.get('amount')) or 0.0,
                    'name': g_wrap.get('name'),
                    'product_uom_qty': 1,
                    'order_id': orderid.id,
                    #                             'woocom_amount_paid':percent_paid,
                    'tax_id': tax_id or False,
                    'woocom_id': g_wrap.get('id'),
                    'product_uom': self.gift_wrapper_fee_product_id and self.gift_wrapper_fee_product_id.uom_id.id
                }
                line_ids = sale_order_line_obj.search(
                    [('order_id', '=', orderid.id), ('woocom_id', '=', g_wrap.get('id'))])
                #                print ("Linrpppppppppppps",line_ids)
                if not line_ids:
                    line_id = sale_order_line_obj.create(line)
        #                    print ("LINEErRpppppppppppppp",line_id)

        if order_detail.get('shipping_lines'):
            for avalue in order_detail.get('shipping_lines'):
                tax_id = []
                #                print ("AAAAAAAAAAAAAAAAAAAAAAAAAAAAa",avalue)
                if avalue.get('taxes'):
                    tax_id = self.with_context({'shipping_tax': avalue.get('total_tax')}).getTaxesAccountID(
                        avalue.get('total_tax'), country_code)
                    #                    print("tax_idtax_id99999999999999999999999",tax_id)
                    if not tax_id == [False]:
                        tax_id = [(6, 0, [tax_id[0].id])]
                        print("iiiiifffffffline['tax_id']ddddddddddd", tax_id)
                    else:
                        tax_id = []

                if avalue.get('method_id') == 'False':
                    car_id = False
                else:
                    car_ids = carrier_obj.search([('woocom_id', '=', avalue.get('method_id'))])
                    #                    print("car_ids0000000000000000",car_ids)
                    if car_ids:
                        car_id = car_ids[0]
                        shipping_product = car_id.product_id
                        logger.info('shipping_producti111111111111d ===> %s', shipping_product)
                        line = {
                            'product_id': shipping_product.id,
                            'price_unit': avalue.get('total') or 0.0,
                            'name': shipping_product.name,
                            'product_uom_qty': 1,
                            'order_id': orderid.id,
                            #                             'woocom_amount_paid':percent_paid,
                            'tax_id': tax_id or False,
                            'woocom_id': avalue.get('id'),
                            'product_uom': shipping_product and shipping_product.uom_id.id
                        }
                        logger.info('linelineline2111111 ===> %s', line)
                    else:
                        product_ids = self.env['product.product'].search(
                            [('name', '=', avalue.get('method_title')), ('default_code', '=', avalue.get('method_id'))])
                        if product_ids:
                            product_id = product_ids[0]
                        else:
                            product_id = self.env['product.product'].create(
                                {'name': avalue.get('method_title'), 'default_code': avalue.get('method_id')})
                        car_id = carrier_obj.create(
                            {'name': avalue.get('method_title'), 'woocom_id': avalue.get('method_id'),
                             'product_id': product_id.id, 'delivery_type': 'fixed'})
                        #                        self.importWoocomCarrier()
                        #                         car_url = 'shipping_methods'+str(avalue.get('method_id'))

                        #                        car_ids = carrier_obj.search([('woocom_id','=', avalue.get('method_id'))])
                        print("car_ids666666", car_id)
                        if car_id:
                            car_id = car_id[0]
                            shipping_product = car_id.product_id
                            logger.info('shipping_product2222222222222 ===> %s', shipping_product)
                            line = {
                                'product_id': shipping_product.id,
                                'price_unit': avalue.get('total') or 0.0,
                                'name': shipping_product.name,
                                'product_uom_qty': 1,
                                'order_id': orderid.id,
                                #                             'woocom_amount_paid':percent_paid,
                                'tax_id': tax_id or False,
                                'woocom_id': avalue.get('id'),
                                'product_uom': shipping_product and shipping_product.uom_id.id
                            }
                            logger.info('linelineline2222222222222 ===> %s', line)
                    line_ids = sale_order_line_obj.search(
                        [('order_id', '=', orderid.id), ('woocom_id', '=', avalue.get('id'))])
                    print("Linrrrrrrrrrrrrrrrrrrs", line_ids)
                    print("linelinelinelineline", line)
                    if not line_ids:
                        line_id = sale_order_line_obj.create(line)
        #                        print ("LINEErRRRRRRRRRRRRR",line_id)

        for child in order_detail.get('line_items'):
            # logger.info('childddddddddddddddddddddddd ===> %s', child)
            #            print ('childddddddddddddddddddddddd===>', child)
            p_id = False
            if child.get('sku'):
                p_ids = product_obj.search([('default_code', '=', child.get('sku'))])
                # logger.info('skuuuuuuuuuuuuuuu11111111111111111===> %s', p_ids)
            else:
                if child.get('variation_id'):
                    p_ids = product_obj.search([('woocom_variant_id', '=', child.get('variation_id'))])
                    # logger.info('skuuuuuuuuuuuuuuu22222222222===> %s', p_ids)
                else:
                    p_ids = product_obj.search([('product_tmpl_id.woocom_id', '=', child.get('product_id'))]
                                               )
                    # logger.info('skuuuuuuuuuuuuuuu333333333333333===> %s', p_ids)

            if p_ids:
                p_id = p_ids[0]
                # logger.info('pidddddddd11111111111===> %s', p_id)
            else:
                new_prd = wcapi.get("products/" + str(child.get('product_id')))
                new_prd = new_prd.json()
                self.create_woocom_product(new_prd, wcapi)

                if child.get('sku'):
                    # logger.info('SKUUUUUUUUUUUUUUUUU===> %s', child.get('sku'))
                    p_ids = product_obj.search([('default_code', '=', child.get('sku'))])
                    # logger.info('p_idssssssssssssssssssssssss===> %s', p_ids)
                else:
                    if child.get('variation_id'):
                        p_ids = product_obj.search([('woocom_variant_id', '=', child.get('variation_id'))])
                        # logger.info('p_idsssssssss11111111111===> %s', p_ids)
                    else:
                        p_ids = product_obj.search([('product_tmpl_id.woocom_id', '=', child.get('product_id'))])
                        # logger.info('p_idsssssssss2222222222===> %s', p_ids)
                if p_ids:
                    p_id = p_ids[0]
                    # logger.info('p_idsssssssss33333333333===> %s', p_id)
            if not p_id:
                return True
            #                 p_ids = product_obj.search([('default_code','=','DLTPRD')])
            #                 # logger.info('p_idsssssssss4444444444444===> %s', p_ids)
            #                 if p_ids:
            #                     p_id = p_ids[0]
            #                     # logger.info('p_idsssssssss55555555555555===> %s', p_id)
            #                 else:
            #                     p_id = product_obj.create({
            #                         'name': 'Deleted Product',
            #                         'type': 'product',
            #                         'default_code': 'DLTPRD',
            #                         })
            # logger.info('p_idsssssssss666666666666===> %s', p_id)
            # line.update({'product_id': p_id,'name': str(child.get('product_id')), 'product_id': p_id.id})
            price_unit = 0.0
            percent_paid = ''
            if child.get('meta_data'):
                for meta_info in child.get('meta_data'):
                    #                     if meta_info.get('key')=='Backordered':
                    # print("meta_infometa_info>>>>>>>>",meta_info)
                    if meta_info.get('key') == '_deposit_full_amount_ex_tax':
                        price_unit += float(meta_info['value']) / float(child.get('quantity'))
                    #                        print("price_unit>>>>>>>>>>>",price_unit)
                    if price_unit != 0:
                        if meta_info.get('key') == '_deposit_deposit_amount_ex_tax':
                            percent_deposit = float(meta_info['value']) * 100 / (
                                    price_unit * float(child.get('quantity')))
                            #                            print("percent_paidpercent_paid>>>>",percent_paid)
                            percent_paid = str(percent_deposit) + '% deposited'
            else:
                price_unit = float(child.get('price'))
                logger.info('price_unitprice_uni===> %s', price_unit)

                # bundle_by = child.get('bundled_by')
            # print ("BUNDLEEEEE_BYYYYYYYY",bundle_by)
            # if bundle_by:
            #     continue

            line = {
                'product_id': p_id and p_id.id,
                'price_unit': price_unit or float(child.get('price')),
                'name': child.get('name') or child.get('sku') or p_id.name,
                'product_uom_qty': float(child.get('quantity')),
                'order_id': orderid.id,
                #                'woocom_amount_paid':percent_paid,
                'tax_id': False,
                'woocom_id': child.get('id'),
                'product_uom': p_id and p_id.uom_id.id
            }
            logger.info('linelinelineline===> %s', line)
            #             print ("LINESSSSSSSSSSSs",line)

            if not child.get('name'):
                # print ("not child.get('name'))))))))")
                p_id = False
                p_ids = product_obj.search([('default_code', '=', 'DLTPRD')])
                # print ("p_idsssssssssssssssss",p_ids)

                if p_ids:
                    p_id = p_ids[0]
                #                    print ("iiiiiffffffffp_iddddddddddd",p_id)
                else:
                    p_id = product_obj.create({
                        'name': 'Deleted Product',
                        'type': 'product',
                        'default_code': 'DLTPRD',
                    })
                    # print ("elsesssssssssssssssssssssssss",p_id)
                line.update({'name': str(child.get('product_id')), 'product_id': p_id.id})
                # logger.info('LINEEEEEEEEEE222222===> %s', line)

            tax_id = []
            # print ("child.get('subtotal_tax')))))))))",child.get('subtotal_tax')) 
            if child.get('taxes'):
                # tax_id = self.getTaxesAccountID(child,orderid,line.get('price_unit'))
                # tax_id = self.getTaxesAccountID(child, country_code)
                tax_id = account_obj.search([('wocomm_tax_id', '=', child.get('taxes')[0].get('id'))])
                print('tax_id++++++++++++', tax_id.id)

                if tax_id:
                    line['tax_id'] = [(6, 0, [tax_id.id])]
                    print('\nline_tax+++++++++if+++++++', line['tax_id'])
                else:
                    line['tax_id'] = []
                    print('\nline_tax++++++else++++++++++', line['tax_id'])
            line_ids = sale_order_line_obj.search([('order_id', '=', orderid.id), ('woocom_id', '=', child.get('id'))])
            #             print ("Lineidddddddsssssss",line_ids)

            if line_ids:
                line_id = line_ids[0]
                #                 print ("iiiddddddLineiddddddd",line_id)
                # logger.info('order line id ===> %s', line_id.name)
                line_id.write(line)
                # print ("LINEEEEEEE",line_id)
            else:
                line_id = sale_order_line_obj.create(line)
                # logger.info('created line===> %s', line_id)
        #                 print ("elseeeeeLineiddddddd",line_id)
        #         self.env.cr.commit()
        return True

    #    # @api.one
    #    def woocomManageOrderLines(self, orderid, order_detail, wcapi):
    #        # logger.info('woocomManageOrderLinesssssssssssssss===> %s', orderid,order_detail)

    #        sale_order_line_obj = self.env['sale.order.line']
    #        prod_attr_val_obj = self.env['product.attribute.value']
    #        prod_templ_obj = self.env['product.template']
    #        product_obj = self.env['product.product']
    #        lines = []
    #        if order_detail.get('fee_lines'):
    #            for g_wrap in order_detail.get('fee_lines'):
    #                print ("AAAAAAAg_wrapAAAa",g_wrap)
    #                tax_id = []
    #                if g_wrap.get('taxes'):
    #                    tax_id = self.with_context({'shipping_tax': g_wrap.get('total_tax')}).getTaxesAccountID(
    #                        g_wrap.get('total_tax'))
    #                    print("tax_idtax_id99999999999999999999999",tax_id)
    #                    if not tax_id == [False]:
    #                        tax_id = [(6, 0, [tax_id[0].id])]
    #                    else:
    #                        tax_id = []

    #                line = {
    #                        'product_id' : self.gift_wrapper_fee_product_id.id,
    #                        'price_unit': float(g_wrap.get('amount')) or 0.0,
    #                        'name': g_wrap.get('name'),
    #                        'product_uom_qty': 1,
    #                        'order_id': orderid.id,
    #    #                             'woocom_amount_paid':percent_paid,
    #                        'tax_id': tax_id or False,
    #                        'woocom_id': g_wrap.get('id'),
    #                        'product_uom': self.gift_wrapper_fee_product_id and self.gift_wrapper_fee_product_id.uom_id.id
    #                    }
    #                line_ids = sale_order_line_obj.search([('order_id', '=', orderid.id), ('woocom_id', '=', g_wrap.get('id'))])
    ##                print ("Linrpppppppppppps",line_ids)
    #                if not line_ids:
    #                    line_id = sale_order_line_obj.create(line)
    ##                    print ("LINEErRpppppppppppppp",line_id)
    #
    #        if order_detail.get('shipping_lines'):
    #            for avalue in order_detail.get('shipping_lines'):
    #                tax_id = []
    ##                print ("AAAAAAAAAAAAAAAAAAAAAAAAAAAAa",avalue)
    #                if avalue.get('taxes'):
    #                    tax_id = self.with_context({'shipping_tax':avalue.get('total_tax')}).getTaxesAccountID(avalue.get('total_tax'))
    ##                    print("tax_idtax_id99999999999999999999999",tax_id)
    #                    if not tax_id == [False]:
    #                        tax_id = [(6, 0, [tax_id[0].id])]
    #                        print ("iiiiifffffffline['tax_id']ddddddddddd",tax_id)
    #                    else:
    #                        tax_id =[]
    #
    #                if avalue.get('method_id') == 'False':
    #                    car_id = False
    #                else:
    #                    car_ids = carrier_obj.search([('woocom_id','=',avalue.get('method_id'))])
    ##                    print("car_ids0000000000000000",car_ids)
    #                    if car_ids:
    #                        car_id = car_ids[0]
    #                        shipping_product = car_id.product_id
    #                        logger.info('shipping_producti111111111111d ===> %s', shipping_product)
    #                        line = {
    #                                'product_id' : shipping_product.id,
    #                                'price_unit': avalue.get('total') or 0.0,
    #                                'name': shipping_product.name,
    #                                'product_uom_qty': 1,
    #                                'order_id': orderid.id,
    #    #                             'woocom_amount_paid':percent_paid,
    #                                'tax_id': tax_id or False,
    #                                'woocom_id': avalue.get('id'),
    #                                'product_uom': shipping_product and shipping_product.uom_id.id
    #                            }
    #                        logger.info('linelineline2111111 ===> %s', line)
    #                    else:
    #                        self.importWoocomCarrier()
    #    #                         car_url = 'shipping_methods'+str(avalue.get('method_id'))
    #
    #                        car_ids = carrier_obj.search([('woocom_id','=', avalue.get('method_id'))])
    #                        print("car_ids666666",car_ids)
    #                        if car_ids:
    #                            car_id = car_ids[0]
    #                            shipping_product = car_id.product_id
    #                            logger.info('shipping_product2222222222222 ===> %s', shipping_product)
    #                            line = {
    #                                'product_id' : shipping_product.id,
    #                                'price_unit': avalue.get('total') or 0.0,
    #                                'name': shipping_product.name,
    #                                'product_uom_qty': 1,
    #                                'order_id': orderid.id,
    #    #                             'woocom_amount_paid':percent_paid,
    #                                'tax_id': tax_id or False,
    #                                'woocom_id': avalue.get('id'),
    #                                'product_uom': shipping_product and shipping_product.uom_id.id
    #                            }
    #                            logger.info('linelineline2222222222222 ===> %s', line)
    #                    line_ids = sale_order_line_obj.search([('order_id', '=', orderid.id), ('woocom_id', '=', avalue.get('id'))])
    #                    print ("Linrrrrrrrrrrrrrrrrrrs",line_ids)
    #                    print ("linelinelinelineline",line)
    #                    if not line_ids:
    #                        line_id = sale_order_line_obj.create(line)
    ##                        print ("LINEErRRRRRRRRRRRRR",line_id)
    #        for child in order_detail:
    #            # logger.info('childddddddddddddddddddddddd ===> %s', child)
    #            p_id = False
    #            if child.get('sku'):
    #                p_ids = product_obj.search([('default_code', '=', child.get('sku'))])
    #                # logger.info('skuuuuuuuuuuuuuuu11111111111111111===> %s', p_ids)
    #            else:
    #                if child.get('variation_id'):
    #                    p_ids = product_obj.search([('woocom_variant_id', '=', child.get('variation_id'))])
    #                    # logger.info('skuuuuuuuuuuuuuuu22222222222===> %s', p_ids)
    #                else:
    #                    p_ids = product_obj.search([('product_tmpl_id.woocom_id', '=', child.get('product_id'))]
    #                                               )
    #                    # logger.info('skuuuuuuuuuuuuuuu333333333333333===> %s', p_ids)

    #            if p_ids:
    #                p_id = p_ids[0]
    #                # logger.info('pidddddddd11111111111===> %s', p_id)
    #            else:
    #                new_prd = wcapi.get("products/" + str(child.get('product_id')))
    #                new_prd = new_prd.json()
    #                # Commented Code
    ##                self.create_woocom_product(new_prd, wcapi)
    #                if child.get('sku'):
    #                    # logger.info('SKUUUUUUUUUUUUUUUUU===> %s', child.get('sku'))
    #                    p_ids = product_obj.search([('default_code', '=', child.get('sku'))])
    #                    # logger.info('p_idssssssssssssssssssssssss===> %s', p_ids)
    #                else:
    #                    if child.get('variation_id'):
    #                        p_ids = product_obj.search([('woocom_variant_id', '=', child.get('variation_id'))])
    #                        # logger.info('p_idsssssssss11111111111===> %s', p_ids)
    #                    else:
    #                        p_ids = product_obj.search([('product_tmpl_id.woocom_id', '=', child.get('product_id'))])
    #                        # logger.info('p_idsssssssss2222222222===> %s', p_ids)
    #                if p_ids:
    #                    p_id = p_ids[0]
    #                    # logger.info('p_idsssssssss33333333333===> %s', p_id)
    #            if not p_id:
    #                p_ids = product_obj.search([('default_code', '=', 'DLTPRD')])
    #                # logger.info('p_idsssssssss4444444444444===> %s', p_ids)
    #                if p_ids:
    #                    p_id = p_ids[0]
    #                    # logger.info('p_idsssssssss55555555555555===> %s', p_id)
    #                else:
    #                    p_id = product_obj.create({
    #                        'name': 'Deleted Product',
    #                        'type': 'product',
    #                        'default_code': 'DLTPRD',
    #                    })
    #                    logger.info('productcreated===> %s', p_id)
    #                    # line.update({'product_id': p_id,'name': str(child.get('product_id')), 'product_id': p_id.id})
    #            line = {
    #                'product_id': p_id and p_id.id,
    ##                Customized code Dee
    #                'price_unit': float(child.get('subtotal'))/float(child.get('quantity')),
    #                'disc_price': float(child.get('subtotal_tax')),
    #                'name': child.get('name') or child.get('sku') or p_id.name,
    #                'product_uom_qty': float(child.get('quantity')),
    #                'order_id': orderid.id,
    #                'tax_id': [],
    #                'woocom_id': child.get('id'),
    #                'product_uom': p_id and p_id.uom_id.id
    #            }
    #            # logger.info('LINEEEEEEEEEEEEEEEEEEEEEEEEE===> %s', line)

    #            if not child.get('name'):
    #                p_id = False
    #                p_ids = product_obj.search([('default_code', '=', 'DLTPRD')])

    #                if p_ids:
    #                    p_id = p_ids[0]
    #                else:
    #                    p_id = product_obj.create({
    #                        'name': 'Deleted Product',
    #                        'type': 'product',
    #                        'default_code': 'DLTPRD',
    #                    })
    #                line.update({'name': str(child.get('product_id')), 'product_id': p_id.id})
    #                logger.info('productcreated===> %s', p_id)

    #            tax_id = []
    #            # print ("child.get('subtotal_tax')))))))))",child.get('subtotal_tax'))
    #            if child.get('subtotal_tax') != None:
    #                tax_id = self.getTaxesAccountID(child, orderid, line.get('price_unit'))
    #                # print("tax_idddddddddddddddddddddd",tax_id)

    #                if tax_id:
    #                    line['tax_id'] =  [(6, 0, tax_id)]
    #                    # print ("iiiiifffffffline['tax_id']ddddddddddd",line['tax_id'])
    #                else:
    #                    line['tax_id'] = []
    #                    # print ("elseeeeeeeeeline['tax_id']ddddddddddd",line['tax_id'])

    #            line_ids = sale_order_line_obj.search([('order_id', '=', orderid.id), ('woocom_id', '=', child.get('id'))])
    #            # print ("Lineidddddddsssssss",line_ids)

    #            if line_ids:
    #                line_id = line_ids[0]
    #                # print ("iiiddddddLineiddddddd",line_id)
    #                logger.info('order line id ===> %s', line_id.name)
    #                line_id.write(line)
    #                print ("LINEEEEEEEeeeeeeeeeeeeeeeeee",line)
    #            else:
    #                print ("elseeeeeLineiddddddddddddddddddddd------------------------------",line)
    ##                euiowr
    #                line_id = sale_order_line_obj.create(line)
    #

    #        return True

    def getTaxesAccountID(self, each_result, country_code):
        print("getTaxesAccountID ======>>>>", each_result)
        accounttax_obj = self.env['account.tax']
        country_obj = self.env['res.country']
        accounttax_id = False
        shop_data = self
        #        print('self.env.context.get',self.env.context.get('shipping_tax'))
        if self.env.context.get('shipping_tax'):
            amount = float(self.env.context.get('shipping_tax'))
        #            print("amount1111111111 =========>>>>",amount)
        else:
            amount = float(each_result.get('total_tax')) / float(each_result.get('quantity'))
        #            print("amount =========>>>>",amount)

        name = 'Sales Tax(' + str(amount) + ')'
        acctax_ids = self.env['account.tax'].search(
            [('type_tax_use', '=', 'sale'), ('amount_type', '=', 'fixed'), ('amount', '=', amount),
             ('name', '=', name)])
        #        print ("acctax_idssssssssssssssssss",acctax_ids)

        country_code_id = country_obj.search([('code', '=', country_code)])
        print('country_code_id+++++++++++++++', country_code_id.id)

        if not len(acctax_ids):
            accounttax_id = accounttax_obj.create(
                {'name': name, 'amount': amount, 'type_tax_use': 'sale', 'amount_type': 'fixed',
                 'country_id': country_code_id.id})
            # print ("iffffffffacctax_idddddddddd",accounttax_id)
        else:
            accounttax_id = acctax_ids[0]
            # print ("elseeeeeeacctax_idddddddddd",accounttax_id)

        return accounttax_id

    #    # @api.one
    #    def getTaxesAccountID(self, each_result, order_id, unit_price):
    #        print("getTaxesAccountIDDDDDDDD")

    #        accounttax_obj = self.env['account.tax']
    #        accounttax_id = False
    #        shop_data = self.browse(self._ids)
    #        #         if hasattr(each_result ,'tax_percent') and float(each_result['tax_percent']) > 0.0:
    #        # amount = float(each_result['ItemTax'])/int(each_result.get('QuantityOrdered'))
    #        # print("amountamount",amount)

    #        acctax_ids = accounttax_obj.search(
    #            [('wocomm_country_id', '=', order_id.partner_id.country_id.id), ('type_tax_use', '=', 'sale'),
    #             ('wocomm_state_id', '=', order_id.partner_id.state_id.id)])
    #        # print("acctax_idsssssssssssssssssss",acctax_ids)

    #        if acctax_ids:
    #            accounttax_id = acctax_ids[0].id
    #            # print ("iiffffaccounttax_id111111111111",accounttax_id)
    #        #             accounttax_id = accounttax_obj.create({'name':name,'amount':amount,'type_tax_use':'sale','amount_type':'fixed'})
    #        #             accounttax_id = accounttax_id.id
    #        else:
    #            accounttax_id = False
    #            # print ("elseeeeeaccounttax_id111111111111",accounttax_id)
    #        return accounttax_id

    # @api.one
    def create_guest_customer(self, order_detail, wcapi):
        res_partner_obj = self.env['res.partner']
        country_obj = self.env['res.country']
        state_obj = self.env['res.country.state']
        account_receive_id = self.env['account.account'].search(
            [('user_type_id.type', '=', 'receivable'), ('company_id', '=', self.env.user.company_id.id)])
        account_pay_id = self.env['account.account'].search(
            [('user_type_id.type', '=', 'payable'), ('company_id', '=', self.env.user.company_id.id)])

        if order_detail != None:

            country_ids = False
            bcountry = order_detail.get('billing').get('country')
            if bcountry != 'False':
                country_ids = country_obj.search([('code', '=', bcountry)])
                if not country_ids:
                    country_id = country_obj.create({'name': bcountry, 'code': bcountry}).id
                    # logger.info('country id 111===> %s', country_id)
                else:
                    country_id = country_ids.id
                    # logger.info('country id 222===> %s', country_id)
            else:
                country_id = False

            bstate = order_detail.get('billing').get('state')
            if bstate != 'False':
                state_ids = state_obj.search([('country_id', '=', country_id), ('code', '=', bstate)])
                if not state_ids:
                    state_id = state_obj.create({'name': bstate, 'code': bstate, 'country_id': country_id}).id
                    # logger.info('state id 111===> %s', state_id)
                else:
                    state_id = state_ids.id
                    # logger.info('state id 222===> %s', state_id)
            else:
                state_id = False

            #         if customer_detail.get('first_name') or customer_detail.get('last_name'):
            #            Customize code Dee
            add_lines = []
            vals = {}
            name = ''
            if order_detail.get('billing').get('first_name') and order_detail.get('billing').get('last_name'):
                name += order_detail.get('billing').get('first_name') + ' ' + order_detail.get('billing').get(
                    'last_name')
            elif order_detail.get('billing').get('first_name'):
                name += order_detail.get('billing').get('first_name')
            else:
                name += order_detail.get('billing').get('last_name')
            if order_detail.get('billing').get('company'):
                print('----------------------', order_detail.get('billing').get('company'))
                vals = {
                    'woocom_id': '',
                    'guest_user': True,
                    'name': order_detail.get('billing').get('company'),
                    # 'customer': True,
                    'company_type': 'company',
                    'property_account_receivable_id': account_receive_id[0].id if account_receive_id else False,
                    'property_account_payable_id': account_pay_id[0].id if account_pay_id else False,
                }
                add_lines.append((0, 0, {
                    'woocom_id': '',
                    'guest_user': True,
                    'name': name,
                    # 'customer': True,
                    # 'supplier': False,
                    'street': order_detail.get('billing') and order_detail.get('billing').get('address_1') or '',
                    'street2': order_detail.get('billing').get('address_2'),
                    'city': order_detail.get('billing').get('city'),
                    'zip': order_detail.get('billing').get('postcode'),
                    'state_id': state_id,
                    'country_id': country_id,
                    'email': order_detail.get('email'),
                    'type': 'invoice',
                    #                    'property_account_receivable_id': account_receive_id[0].id if account_receive_id else False,
                    #                    'property_account_payable_id': account_pay_id[0].id if account_pay_id else False,
                }))
            else:
                #                print('==================')
                vals = {
                    'woocom_id': '',
                    'guest_user': True,
                    'name': name,
                    # 'customer': True,
                    # 'supplier': False,
                    'street': order_detail.get('billing') and order_detail.get('billing').get('address_1') or '',
                    'street2': order_detail.get('billing').get('address_2'),
                    'city': order_detail.get('billing').get('city'),
                    'zip': order_detail.get('billing').get('postcode'),
                    'state_id': state_id,
                    'country_id': country_id,
                    'email': order_detail.get('billing').get('email'),
                    'property_account_receivable_id': account_receive_id[0].id if account_receive_id else False,
                    'property_account_payable_id': account_pay_id[0].id if account_pay_id else False,
                }
            scountry = order_detail.get('shipping').get('country')
            if scountry != 'False':
                scountry_ids = country_obj.search([('code', '=', scountry)])
                if not scountry_ids:
                    scountry_id = country_obj.create({'name': scountry, 'code': scountry}).id
                    # logger.info('ssscountry id111 ===> %s', scountry_id)
                else:
                    scountry_id = scountry_ids[0].id
                    # logger.info('ssscountry id222 ===> %s', scountry_id)
            else:
                scountry_id = False

            sstate = order_detail.get('shipping').get('state')
            if sstate != 'False':
                sstate_ids = state_obj.search([('code', '=', sstate)])
                if not sstate_ids:
                    sstate_id = state_obj.create({'name': sstate, 'code': sstate, 'country_id': scountry_id}).id
                    # logger.info('sssstate id000 ===> %s', sstate_id)
                else:
                    sstate_id = sstate_ids[0].id
                    # logger.info('sstate id ===> %s', sstate_id)
            else:
                sstate_id = False

            if order_detail.get('shipping'):
                name = ''
                if order_detail.get('shipping').get('first_name') and order_detail.get('shipping').get('last_name'):
                    name += order_detail.get('shipping').get('first_name') + ' ' + order_detail.get('shipping').get(
                        'last_name')
                elif order_detail.get('shipping').get('first_name'):
                    name += order_detail.get('shipping').get('first_name')
                else:
                    name += order_detail.get('shipping').get('last_name')
                add_lines.append((0, 0, {
                    'woocom_id': '',
                    'guest_user': True,
                    'name': name,
                    'street': order_detail.get('shipping').get('address_1'),
                    'street2': order_detail.get('shipping').get('address_2'),
                    'city': order_detail.get('shipping').get('city'),
                    'zip': order_detail.get('shipping').get('postcode'),
                    'country_id': scountry_id,
                    'state_id': sstate_id,
                    'type': 'delivery',
                }))

            vals.update({'child_ids': add_lines})
            cust_id = res_partner_obj.create(vals)
        self.env.cr.commit()
        return cust_id

    # @api.one
    def create_woo_order(self, order_detail, wcapi):
        # print ("create_woo_orderrrrwwwwwwwwwwwww",order_detail)
        logger.info('create_woo_orderrrrwwwwwwwwwwwww===> %s', order_detail)

        sale_order_obj = self.env['sale.order']
        res_partner_obj = self.env['res.partner']
        carrier_obj = self.env['delivery.carrier']
        status_obj = self.env['woocom.order.status']
        payment_obj = self.env['payment.gatway']
        country_obj = self.env['res.country']
        state_obj = self.env['res.country.state']
        woocom_conector = self.env['woocommerce.connector.wizard']

        if not order_detail.get('line_items'):
            #            print('=====idddddddddddd',order_detail.get('id'))
            return False
        if not order_detail.get('billing'):
            partner_ids = res_partner_obj.search([('name', '=', 'Guest Customer')])
            if partner_ids:
                partner_id = partner_ids[0].id
                billing_id = partner_id
                delivery_id = partner_id
            else:
                partner_id = res_partner_obj.create({'name': 'Guest Customer'}).id
                billing_id = partner_id
                delivery_id = partner_id
        if order_detail.get('billing'):
            # print ("==ELSEEEEORDERRRRRRRRRR==")
            part_ids = res_partner_obj.search([('email', '=', order_detail.get('billing').get('email'))])
            print("part_idssssssssss111111111111111", part_ids, order_detail.get('billing').get('email'))

            if part_ids:
                # print ("iffffff_part_ids111111111111111",part_ids)
                partner_id = part_ids[0].id
                if order_detail.get('billing'):
                    billing_ids = res_partner_obj.search(
                        [('street', '=', order_detail.get('billing').get('address_1')), ('parent_id', '=', partner_id),
                         ('city', '=', order_detail.get('billing').get('city')),
                         ('zip', '=', order_detail.get('billing').get('postcode')), ('type', '=', 'invoice')])
                    if billing_ids:
                        billing_id = billing_ids[0].id
                    else:
                        country_id = False
                        state_id = False
                        bcountry = order_detail.get('billing').get('country')
                        if bcountry != 'False':
                            country_ids = country_obj.search([('code', '=', bcountry)])
                            if not country_ids:
                                country_id = country_obj.create({'name': bcountry, 'code': bcountry}).id
                            else:
                                country_id = country_ids.id
                        else:
                            country_id = False
                        if country_id:
                            bstate = order_detail.get('billing').get('state')
                            if bstate != 'False':
                                state_ids = state_obj.search([('country_id', '=', country_id), ('code', '=', bstate)])
                                if not state_ids:
                                    state_id = state_obj.create(
                                        {'name': bstate, 'code': bstate, 'country_id': country_id}).id
                                else:
                                    state_id = state_ids.id
                            else:
                                state_id = False

                        billing_id = res_partner_obj.create({'street': order_detail.get('billing').get('address_1'),
                                                             'street2': order_detail.get('billing').get('address_2'),
                                                             'city': order_detail.get('billing').get('city'),
                                                             'zip': order_detail.get('billing').get('postcode'),
                                                             'phone': order_detail.get('billing').get('phone'),
                                                             'state_id': state_id,
                                                             'country_id': country_id,
                                                             'type': 'invoice',
                                                             'name': order_detail.get('billing').get(
                                                                 'first_name') + ' ' + order_detail.get('billing').get(
                                                                 'last_name'),
                                                             'parent_id': partner_id
                                                             }).id
                        billing_id = billing_id
                #                logger.info('partner id ::::::::::::::::::::===> %s', partner_id)
                if order_detail.get('shipping'):
                    shipping_ids = res_partner_obj.search(
                        [('street', '=', order_detail.get('shipping').get('address_1')), ('parent_id', '=', partner_id),
                         ('city', '=', order_detail.get('shipping').get('city')),
                         ('zip', '=', order_detail.get('shipping').get('postcode')), ('type', '=', 'delivery')])
                    if shipping_ids:
                        delivery_id = shipping_ids[0].id
                    else:
                        country_id = False
                        state_id = False
                        bcountry = order_detail.get('shipping').get('country')
                        if bcountry != 'False':
                            country_ids = country_obj.search([('code', '=', bcountry)])
                            if not country_ids:
                                country_id = country_obj.create({'name': bcountry, 'code': bcountry}).id
                            else:
                                country_id = country_ids.id
                        else:
                            country_id = False
                        if country_id:
                            bstate = order_detail.get('shipping').get('state')
                            if bstate != 'False':
                                state_ids = state_obj.search([('country_id', '=', country_id), ('code', '=', bstate)])
                                if not state_ids:
                                    state_id = state_obj.create(
                                        {'name': bstate, 'code': bstate, 'country_id': country_id}).id
                                else:
                                    state_id = state_ids.id
                            else:
                                state_id = False

                        delivery_id = res_partner_obj.create({'street': order_detail.get('shipping').get('address_1'),
                                                              'street2': order_detail.get('shipping').get('address_2'),
                                                              'city': order_detail.get('shipping').get('city'),
                                                              'zip': order_detail.get('shipping').get('postcode'),
                                                              'type': 'delivery',
                                                              'state_id': state_id,
                                                              'country_id': country_id,
                                                              'name': order_detail.get('shipping').get(
                                                                  'first_name') + ' ' + order_detail.get(
                                                                  'shipping').get('last_name'),
                                                              'parent_id': partner_id
                                                              }).id

            else:
                country_ids = False
                state_id = False
                bcountry = order_detail.get('billing').get('country')
                if bcountry != 'False':
                    country_ids = country_obj.search([('code', '=', bcountry)])
                    if not country_ids:
                        country_id = country_obj.create({'name': bcountry, 'code': bcountry}).id
                    else:
                        country_id = country_ids.id
                else:
                    country_id = False
                if country_id:
                    bstate = order_detail.get('billing').get('state')
                    if bstate != 'False':
                        state_ids = state_obj.search([('country_id', '=', country_id), ('code', '=', bstate)])
                        if not state_ids:
                            state_id = state_obj.create({'name': bstate, 'code': bstate, 'country_id': country_id}).id
                        else:
                            state_id = state_ids.id
                    else:
                        state_id = False
                partner_id = res_partner_obj.create({'street': order_detail.get('billing').get('address_1'),
                                                     'street2': order_detail.get('billing').get('address_2'),
                                                     'city': order_detail.get('billing').get('city'),
                                                     'zip': order_detail.get('billing').get('postcode'),
                                                     # 'customer': True,
                                                     'state_id': state_id,
                                                     'country_id': country_id,
                                                     'email': order_detail.get('billing').get('email'),
                                                     'woocom_id': order_detail.get('customer_id'),
                                                     'phone': order_detail.get('billing').get('phone'),
                                                     'name': order_detail.get('billing').get(
                                                         'first_name') + ' ' + order_detail.get('billing').get(
                                                         'last_name' or order_detail.get('billing').get('username')),
                                                     }).id
                billing_id = partner_id
                partner_id = partner_id
                if partner_id:
                    if order_detail.get('shipping'):
                        shipping_ids = res_partner_obj.search(
                            [('street', '=', order_detail.get('shipping').get('address_1')),
                             ('parent_id', '=', partner_id),
                             ('city', '=', order_detail.get('shipping').get('city')),
                             ('zip', '=', order_detail.get('shipping').get('postcode')), ('type', '=', 'delivery')])
                        if shipping_ids:
                            delivery_id = shipping_ids[0].id
                        else:
                            state_id = False
                            country_id = False
                            bcountry = order_detail.get('shipping').get('country')
                            if bcountry != 'False':
                                country_ids = country_obj.search([('code', '=', bcountry)])
                                if not country_ids:
                                    country_id = country_obj.create({'name': bcountry, 'code': bcountry}).id
                                else:
                                    country_id = country_ids.id
                            else:
                                country_id = False
                            if country_id:
                                bstate = order_detail.get('shipping').get('state')
                                if bstate != 'False':
                                    state_ids = state_obj.search(
                                        [('country_id', '=', country_id), ('code', '=', bstate)])
                                    if not state_ids:
                                        state_id = state_obj.create(
                                            {'name': bstate, 'code': bstate, 'country_id': country_id}).id
                                    else:
                                        state_id = state_ids.id
                                else:
                                    state_id = False

                            delivery_id = res_partner_obj.create(
                                {'street': order_detail.get('shipping').get('address_1'),
                                 'street2': order_detail.get('shipping').get('address_2'),
                                 'city': order_detail.get('shipping').get('city'),
                                 'zip': order_detail.get('shipping').get('postcode'),
                                 'type': 'delivery',
                                 'state_id': state_id,
                                 'country_id': country_id,
                                 'name': order_detail.get('shipping').get('first_name') + ' ' + order_detail.get(
                                     'shipping').get('last_name'),
                                 'parent_id': partner_id
                                 }).id
            # else:
            #     url = 'customers/' + str(custm_id)
            #     customer_data = wcapi.get(url)
            #     customer_data = customer_data.json()
            #     partner_id = self.create_woo_customer(customer_data, wcapi)[0].id
            #     # partner_id = partner_id.id
            #     # print ("PARTNERRRRRRRRRRRR",partner_id)

        paym_ids = payment_obj.search([('woocom_id', '=', order_detail.get('payment_method'))])
        if paym_ids:
            pay_id = paym_ids[0].id
            logger.info('payment id ===> %s', pay_id)
        else:
            pay_id = payment_obj.search([('woocom_id', '=', order_detail.get('payment_method'))])
            pay_id = pay_id.id
        car_id = False
        #        for avalue in order_detail.get('shipping_lines'):
        #            if avalue.get('method_id') == 'False':
        #                car_id = False
        #            else:
        #                car_ids = carrier_obj.search([('woocom_id', '=', avalue.get('method_id'))])
        #                if car_ids:
        #                    car_id = car_ids[0].id
        #                    logger.info('carrier id ===> %s', car_id)
        #                else:
        #                    car_id = carrier_obj.create({'name':avalue.get('method_title'),'woocom_id':avalue.get('method_id')})
        #                    self.importWoocomCarrier()
        #                    #                     car_url = 'shipping_methods'+str(avalue.get('method_id'))

        #                    car_ids = carrier_obj.search([('woocom_id', '=', avalue.get('method_id').replace(':2', ""))])
        #                    if car_ids:
        #                        car_id = car_ids[0].id
        #                    else:
        #                        car_id = False
        # print ("caridddddddddddddd",car_id)
        # carr_data = wcapi.get(car_id)
        # print ("cardataaaaaaaaaaa",carr_data)
        # carrier_data = carr_data.json()
        # print ("CARDATA2222222222",carrier_data)
        # carrier_id = self.create_woo_carrier(carrier_data.get('customer'), wcapi)[0].id
        #                     car_ids = carrier_obj.search([('woocom_id','=',avalue.get('method_id'))])
        #                     if car_ids:
        #                         car_id = car_ids[0].id
        #                         logger.info('carrier id ===> %s', car_id)
        #                     else:
        #                         car_id = False
        # llllllllllllllll
        if order_detail.get('status') == 'draft':
            # print ("order_detail.get('status1111111111')",order_detail.get('status'))

            order_detail.update({'status': 'pending'})
            # print ("order_detail.get('status22222222222')",order_detail.get('status'))
        print("<><><><><><><><><><><><STATUS<><><><><><><><><>", order_detail.get('status'))
        # invoice_obj1 = self.env['account.move']
        # if order_detail.get('status') == 'completed':
        #     invoice_obj1.action_invoice_register_payment()
        #     invoice_obj1.post()
        order_vals = {'partner_id': partner_id,
                      'partner_invoice_id': billing_id,
                      'partner_shipping_id': delivery_id,
                      'woocom_id': order_detail.get('id'),
                      'warehouse_id': self.warehouse_id.id,
                      'name': (self.prefix and self.prefix or '') + str(order_detail.get('id')) + (
                              self.suffix and self.suffix or ''),
                      'pricelist_id': self.pricelist_id.id,
                      'order_status': order_detail.get('status'),
                      'shop_id': self.id,
                      'carrier_woocommerce': car_id or False,
                      # 'l10n_in_gst_treatment': 'unregistered',
                      'woocom_payment_mode': pay_id,
                      # 'partner_billing_id': bill_partner_id,
                      # 'partner_shipping_id': ship_partner_id,
                      'company_id': self.env.company.id,
                      }
        print("ORDRVALSSSSSSSSSSSSSSSSS", order_vals)
        # logger.info('ORDRVALSSSSSSSSSSSSSSSSS===> %s', order_vals)

        sale_order_ids = sale_order_obj.search([('woocom_id', '=', order_detail.get('id'))])
        print("SALEORDERIDDDDDDDD", sale_order_ids)

        if not sale_order_ids:
            # dwdwddwwddw
            s_id = sale_order_obj.create(order_vals)
            # print ("sidd11111111111111d",s_id,s_id.name)
            self.woocomManageOrderLines(s_id, order_detail, wcapi)
            if order_detail.get('coupon_lines', False):
                # print ("IIIIIIIIINNNNNNNNN111111111111")
                self.woocomManageCoupon(s_id, order_detail.get('coupon_lines'), wcapi)
            self.woocomManageOrderWorkflow(s_id, order_detail, order_detail.get('status'))
        else:
            # dwdwddw
            # if sale_order_ids.state != 'done':
            s_id = sale_order_ids[0]
            #     # print ("SID22222222222",s_id,s_id.name)
            #
            #     # logger.info('create order ===> %s', s_id.name)
            #     # s_id.write(order_vals)
            #     self.woocomManageOrderLines(s_id, order_detail.get('line_items'), wcapi)
            #     if order_detail.get('coupon_lines', False):
            #         # print ("IIIIIIIIINNNNNNNNN111111111111")
            #         self.woocomManageCoupon(s_id, order_detail.get('coupon_lines'), wcapi)
            #     # s_id.delivery_tax_address()
            #     self.woocomManageOrderWorkflow(s_id, order_detail, order_detail.get('status'))
        self.env.cr.commit()

    # @api.multi
    def importWoocomOrder(self):
        # print ("importOrderrrrrrrrrrrrrr===========>")
        logger.info('importOrderrrrrrrrrrrrrr===>')
        sale_order_obj = self.env['sale.order']

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            # print ("WCPIIIIIIIIIIIIII",wcapi)
            count = 1
            if self.env.context.get('last_woocommerce_order_import_date'):
                method = "orders?filter[created_at_min]=" + str(
                    self.env.context.get('last_woocommerce_order_import_date'))
                # print ("METHODDDDDDDD1111111111",method)
            elif shop.last_woocommerce_order_import_date:
                today = date.today() - timedelta(days=2)
                method = "orders?filter[created_at_min]=" + str(today)
                # print ("METHODDDDDDDD222222222",method)
            else:
                method = 'orders?page=' + str(count)
                # print ("METHODDDDDDDD3333333333",method)

            orders = wcapi.get(method)
            # print ("WCPIORDERSSSSSSSSSS",orders)

            if orders.status_code != 200:
                raise UserError(_("Enter Valid url"))
            orders_list = orders.json()
            # print("ORDERLISTTTTTTTTTTT",orders_list)

            for order in orders_list:
                print("FFFFOOOORRRRRORDERLISTTTTTT", order)
                if order.get('status') != 'refunded':
                    shop.create_woo_order(order, wcapi)

            while len(orders_list) > 0:
                # print("WHILEEEEEEEEEEEEEE",len(orders_list))
                # print("====count111111",count)
                url = "orders?page=" + str(count)
                # print("=====url====>",url)

                order = wcapi.get("orders?page=" + str(count))
                count += 1
                # print ("====count22222222",count)
                orders_list = order.json()
                for order in orders_list:
                    print("<><><><><><><><><><><><><>>order--------++++++++", order, order.get('status'))
                    if order.get('status') != 'refunded':
                        shop.create_woo_order(order, wcapi)

        shop.write({'last_woocommerce_order_import_date': datetime.today()})
        self.env.cr.commit()
        return True

    # @api.multi
    def importRefundOrder(self):
        print("importRefundOrderrrrrrrrrrrrrrrrr===========>", self)
        sale_order_obj = self.env['sale.order']

        for shop in self:
            # print ("SHOPPPPPPPPPPPPPPPPP",shop)

            wcapi = woocom_api.API(url=shop.woocommerce_instance_id.location,
                                   consumer_key=shop.woocommerce_instance_id.consumer_key,
                                   consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True,
                                   version='wc/v2')
            # print ("WCPIIIIIII111111111111111111",wcapi)
            count = 1
            if self.env.context.get('last_woocommerce_refund_order_import_date'):
                method = "orders?filter[created_at_min]=" + str(
                    self.env.context.get('last_woocommerce_refund_order_import_date'))
            elif shop.last_woocommerce_refund_order_import_date:
                today = date.today() - timedelta(days=2)
                method = "orders?filter[created_at_min]=" + str(today)
            else:
                method = 'orders?page=' + str(count)
                # method = 'orders/446'
                # print ("METHODDDDDDDD",method)
            orders_list = wcapi.get(method)
            # print ("ORDERSSSSSSSSSSSS",orders_list)

            if orders_list.status_code != 200:
                raise UserError(_("Enter Valid url"))
            orders_list = orders_list.json()
            print("orders_listS", orders_list)
            if isinstance(orders_list, dict):
                orders_list = [orders_list]
            while len(orders_list) > 0:
                # print ("WHILEEEEEEEEEEEEEEEEEEE1111111111",len(orders_list))
                # print ("COUNTTTTTTTTTTRRRRRRR11111",count)
                for order in orders_list:
                    # print ("FOOOOORRRRRINNNNNNNRREEEEEFFFFFF222222222",order)

                    if order.get('status') == 'refunded':
                        sale_order_ids = sale_order_obj.search([('woocom_id', '=', order.get('id'))])
                        # print ("FOOOOORRRRRsale_order_idssssssss22222222",sale_order_ids)
                        if not sale_order_ids:
                            # print ("NOTTTTTTTTTTTT",sale_order_ids,shop)
                            sale_order_ids = shop.create_woo_order(order, wcapi)
                            # print ("sale_order_idssssss111111111222222222",sale_order_ids)
                            sale_order_ids = sale_order_obj.search([('woocom_id', '=', order.get('id'))])
                            # print ("sale_order_ids22222222222222.2.2.2.2.2",sale_order_ids)
                            self._cr.commit()
                        if sale_order_ids:
                            # print ("IIIINNNN======sale",sale_order_ids)
                            shop.importWoocomOrderRefund(order, sale_order_ids)
                            self._cr.commit()
                # self._cr.commit()
                count += 1
                orders_list = wcapi.get("orders?page=" + str(count))
                url = "orders?page=" + str(count)
                # print ("URLLLLLLLLLLLLL",url)

                # count += 1
                # print ("COUNTTTTTTTTTTRRRRRRR22222",count)
                orders_list = orders_list.json()
                print("----------------------------------------------------", len(orders_list))
        shop.write({'last_woocommerce_refund_order_import_date': datetime.today()})
        self.env.cr.commit()
        return True

    # @api.multi
    def importWoocomOrderRefund(self, order_detail, saleorderid):
        print("importWoocomOrderRefundddddddddd===========>", order_detail)

        invoice_obj = self.env['account.invoice.send']
        invoice_refund_obj = self.env['account.invoice.refund']
        return_obj = self.env['stock.return.picking']
        return_line_obj = self.env['stock.return.picking.line']
        sale_order_obj = self.env['sale.order']
        stock_pick_obj = self.env['stock.picking']

        ctx = self.env.context.copy()
        for shop in self:
            wcapi = woocom_api.API(url=shop.woocommerce_instance_id.location,
                                   consumer_key=shop.woocommerce_instance_id.consumer_key,
                                   consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True,
                                   version='wc/v2')
            # print ("WCPIIIIIII22222222222222222",wcapi)
            count = 1

            method = 'orders/' + str(order_detail.get('id')) + '/refunds'
            refund_orders = wcapi.get(method)
            if refund_orders.status_code != 200:
                raise UserError(_("Enter Valid url"))
            refund_list = refund_orders.json()
            for refund_detail in refund_list:
                # print ("refund_detailssssssssssssssssssss",refund_detail)

                if saleorderid.state == 'draft':
                    saleorderid.action_confirm()

                if not saleorderid.invoice_ids:
                    saleorderid.action_confirm()
                    invoice_id = saleorderid.action_invoice_create()

                if saleorderid.state in ['sale', 'done', 'sent']:

                    for invoice in saleorderid.invoice_ids:
                        refund_ids = invoice_obj.search([('origin', '=', invoice.number)])
                        # print ("refund_idsssss11111111111",refund_ids)
                        if refund_ids:
                            refund_ids = invoice_obj.search([('id', '=', refund_ids.refund_invoice_id.id)])
                            # print ("refund_idsssss2222222222",refund_ids)
                        if not refund_ids:
                            refund_ids = invoice_obj.search([('id', '=', invoice.refund_invoice_id.id)])
                            # print ("refund_idsssss333333333333331",refund_ids)

                            date1 = refund_detail.get('date_created')
                            date2 = date1.replace('T', " ")
                            date3 = datetime.strptime(date2, '%Y-%m-%d %H:%M:%S')
                            date4 = date3.strftime('%m/%d/%Y')
                            if not refund_ids:
                                print("==NOT refund_ids==>")
                                if invoice.state == 'paid':
                                    # if invoice.state in ['paid', 'draft']:
                                    # print ("PAIDDDDDDDDDDDD",invoice.state)
                                    ctx.update({'active_ids': invoice.id})
                                    refund_vals = {
                                        'description': refund_detail.get('reason'),
                                        'date': date4,
                                        # 'date_invoice' : datetime.today(),
                                        'filter_refund': 'refund',
                                    }
                                    # print ("RefundValssssssssss",refund_vals)
                                    refund_invoice_id = invoice_refund_obj.with_context(ctx).create(refund_vals)
                                    self._cr.commit()

                                    # print ("refund_invoice_iddddddddddddd",refund_invoice_id)

                                    invc = refund_invoice_id.with_context(ctx).invoice_refund()
                                    # print ("invvvvvvvvvvvvv",invc)

                                    a = invc.get('domain')[1][2][0]
                                    # print "1111111111111",a
                                    # b = a[1]
                                    # print "2222222222222",b
                                    # c = b[2]
                                    # print "333333333333",c[0]

                                    refunded_invoice_id = invoice_obj.browse(a)
                                    # print "invoice_refundCCCCCCCCCCC",refunded_invoice_id

                                    if refunded_invoice_id.state == 'draft':
                                        # print "invoice state is draft"
                                        refunded_invoice_id.action_invoice_open()

                                    if refunded_invoice_id.state not in [
                                        'paid'] and refunded_invoice_id.invoice_line_ids:
                                        refunded_invoice_id.pay_and_reconcile(
                                            self.workflow_id and self.sale_journal or self.env[
                                                'account.journal'].search(
                                                [('type', '=', 'bank')], limit=1), refunded_invoice_id.amount_total)

                                    saleorderid.write({'is_refund': True})
                                # else:
                                #     invoice.action_cancel()

                    for picking in saleorderid.picking_ids:
                        if picking.picking_type_id.code == "incoming":
                            continue
                        if picking.return_created:
                            continue

                        # global counter
                        # print ("counter***************",counter)

                        # print ("PICINGGGGGGG=====>>>",picking.name,picking.origin)

                        # if not picking.is_original:
                        # print ("IIIIIIIFFFFFFFFFFFFF111111",picking)
                        picking.action_confirm()
                        StockPackObj = self.env['stock.move.line']
                        for move in picking.move_lines:
                            mvals = {
                                'product_id': move.product_id.id,
                                'qty_done': move.product_uom_qty,
                                'product_uom_id': move.product_id.uom_id.id,
                                'location_id': move.location_id.id,
                                'location_dest_id': move.location_dest_id.id,
                                'move_id': move.id}
                            # print("=====mvals111111=>",mvals)
                            StockPackObj.create(mvals)
                        picking.action_done()
                        # picking.write({'is_original': 'True'})
                        self._cr.commit()
                        # print("====done validate out")

                        ctx = self._context.copy()
                        ctx.update({'active_ids': [picking.id], 'active_id': picking.id})
                        res = return_obj.with_context(ctx).default_get(['product_return_moves', 'move_dest_exists'])
                        res.update({'invoice_state': '2binvoiced'})
                        return_id = return_obj.with_context(ctx).create({'invoice_state': 'none'})
                        self._cr.commit()

                        pick_id_return, type = return_id.with_context(ctx)._create_returns()
                        new_picking_id = self.env['stock.picking'].browse([pick_id_return])
                        # print ("new_picking_idddddddddddddddddd",new_picking_id)

                        picking.return_created = True

                        # print ("IIIIIIIFFFFFFFFFFFFF",new_picking_id)
                        new_picking_id.action_confirm()
                        for move in new_picking_id.move_lines:
                            mmvals = {
                                'product_id': move.product_id.id,
                                'qty_done': move.product_uom_qty,
                                'product_uom_id': move.product_id.uom_id.id,
                                'location_id': move.location_id.id,
                                'location_dest_id': move.location_dest_id.id,
                                'move_id': move.id
                            }
                            # print("=====mvals222222222=>",mmvals)

                            StockPackObj.create(mmvals)

                        new_picking_id.action_done()
                        # new_picking_id.write({'is_return': 'True'})
                        self._cr.commit()

        return True

    # @api.one
    def createTags(self, tag_detail, wcapi):
        # print ("CREATEEEEEE_TAGSSSSSSSSSSSSSSS")
        logger.info('createtagsssssss ===> %s', tag_detail)

        prod_tag_obj = self.env['product.tags']
        tag_ids_list = []
        for tag_data in tag_detail:
            prod_tag_ids = prod_tag_obj.search([('tag_id', '=', tag_data.get('id'))])
            tag_vals = {
                'name': tag_data.get('name'),
                'slud_code': tag_data.get('slug'),
                'description': tag_data.get('description'),
                'tag_id': tag_data.get('id'),
            }
            # logger.info('tag_valsssssssssssssss ===> %s', tag_vals)
            if prod_tag_ids:
                tag_ids_list.append(prod_tag_ids[0].id)
                tag_id = prod_tag_ids[0].id
                prod_tag_ids[0].write(tag_vals)
            else:
                tag_id = prod_tag_obj.create(tag_vals)
                tag_ids_list.append(tag_id.id)
            self.env.cr.commit()
        return tag_ids_list

    # @api.multi
    def importTags(self):
        logger.info('IMPORT_TAGSSSSSSSSSSSSSSS ===>')
        prod_tag_obj = self.env['product.tags']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            try:
                count = 1

                tag_list = wcapi.get("products/tags?page=" + str(count))
                if not tag_list.status_code:
                    raise UserError(_("Enter Valid url"))
                tag_list = tag_list.json()

                while len(tag_list):
                    self.createTags(tag_list, wcapi)
                    count += 1
                    tag_list = wcapi.get("products/tags?page=" + str(count))
                    tag_list = tag_list.json()
            except Exception as e:
                # print ("Error.............%s",e)
                pass
        return True

    # @api.one
    def createCoupons(self, coupon_detail, wcapi):
        coupon_obj = self.env['woocom.coupons']
        coupon_ids_list = []
        for coupon_data in coupon_detail:
            if coupon_data.get('discount_type') == 'percent':
                new_coupon = 'percent'
            elif coupon_data.get('discount_type') == 'fixed_cart':
                new_coupon = 'fixed_cart'
            else:
                new_coupon = 'fixed_product'

            coupon_ids = coupon_obj.search(
                ['|', ('coupon_id', '=', coupon_data.get('id')), ('coupon_code', '=', coupon_data.get('code'))])

            # coupon_ids = coupon_obj.search([('coupon_id','=', coupon_data.get('id'))])

            # print ("coupon_idsssssssssssssssssssssss",coupon_ids)
            coupon_vals = {
                'coupon_code': coupon_data.get('code'),
                'description': coupon_data.get('description'),
                'coupon_id': coupon_data.get('id'),
                'coupon_type': new_coupon,
            }
            if coupon_ids:
                coupon_ids_list.append(coupon_ids[0].id)
                coupon_ids[0].write(coupon_vals)
            else:
                coupon_id = coupon_obj.create(coupon_vals)
                coupon_ids_list.append(coupon_id.id)
            self.env.cr.commit()
        return coupon_ids_list

    # @api.multi
    def importCoupons(self):
        print("IMPORT_COUPONSSSSSSSS")
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            # print ("wcapiiiiiiiiiiiiiiiiiiiii",wcapi)
            try:
                count = 1
                coupon_list = wcapi.get("coupons?page=" + str(count))
                if not coupon_list.status_code:
                    raise UserError(_("Enter Valid url"))
                coupon_list = coupon_list.json()
                while len(coupon_list):
                    self.createCoupons(coupon_list, wcapi)
                    count += 1
                    coupon_list = wcapi.get("coupons?page=" + str(count))
                    coupon_list = coupon_list.json()
            except Exception as e:
                # print ("Error.............%s",e)
                pass
        return True

    # @api.multi
    def updateWoocomCoupons(self):
        print("updateCouponssssssssss", self)

        coupon_obj = self.env['woocom.coupons']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            if shop.woocommerce_last_update_coupon_date:
                coupon_ids = coupon_obj.search(
                    [('write_date', '>', shop.woocommerce_last_update_coupon_date), ('coupon_id', '!=', False)])
            else:
                coupon_ids = coupon_obj.search([('coupon_id', '!=', False)])
            for each in coupon_ids:

                if each.coupon_type == 'percent':
                    new_coupon = 'percent'
                elif each.coupon_type == 'fixed_product':
                    new_coupon = 'fixed_product'
                else:
                    new_coupon = 'fixed_cart'

                coupon_vals = {
                    'code': each.coupon_code,
                    'description': each.description,
                    'id': each.coupon_id,
                    'discount_type': new_coupon,
                }

                coupon_url = 'coupons/' + str(each.coupon_id)
                coupon_val = wcapi.post(coupon_url, coupon_vals)

    # @api.multi
    def exportWoocomCoupons(self):
        print("ExportCuponsssssssssssssss")
        coupon_obj = self.env['woocom.coupons']

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
                coupon_ids = coupon_obj.browse(self.env.context.get('export_product_ids'))
            else:
                coupon_ids = coupon_obj.search([('to_be_exported', '=', True)])

            for coupon in coupon_ids:
                data = {
                    "code": coupon.coupon_code,
                    'description': coupon.description,
                    'id': coupon.coupon_id,
                    'discount_type': coupon.coupon_type and coupon.coupon_type or 'fixed_cart',
                }

                res = wcapi.post("coupons", data)
                res = res.json()
                if res:
                    coupon.write({'coupon_id': res.get('id'), 'to_be_exported': False})

    # @api.multi
    #     def importWooCategory(self):
    #         for shop in self:
    #             wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
    #             try:
    #                 count = 1
    #                 categ = wcapi.get("products/categories?page="+ str(count))
    #                 if not categ.status_code:
    #                     raise UserError(_("Enter Valid url"))
    #                 category_list = categ.json()
    # #                 try:
    #                 for category in category_list:
    #                     shop.create_woo_category(category, wcapi)
    #                 while len(category_list) > 0:
    #                     count += 1
    #                     categ = wcapi.get("products/categories?page="+ str(count))
    #                     category_list = categ.json()
    #                     for category in category_list:
    #                         shop.create_woo_category(category, wcapi)
    # #                 except Exception as e:
    # #                     if self.env.context.get('log_id'):
    # #                         log_id = self.env.context.get('log_id')
    # #                         self.env['log.error'].create({'log_description': str(e) + " While Getting product categories info of %s" % (category_list.get('product_categories')), 'log_id': log_id})
    # #                     else:
    # #                         log_id = self.env['woocommerce.log'].create({'all_operations':'import_categories', 'error_lines': [(0, 0, {'log_description': str(e) + " While Getting product categories info of %s" % (category_list.get('product_categories'))})]})
    # #                         self = self.with_context(log_id=log_id.id)
    #             except Exception as e:
    #                 if self.env.context.get('log_id'):
    #                     log_id = self.env.context.get('log_id')
    #                     self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
    #                 else:
    #                     log_id = self.env['woocommerce.log'].create({'all_operations':'import_categories', 'error_lines': [(0, 0, {'log_description': str(e)})]})
    #                     self = self.with_context(log_id=log_id.id)
    #         return True

    # @api.multi
    def updateWoocomCategory(self):
        categ_obj = self.env['woocom.category']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            if shop.woocommerce_last_update_category_date:
                categ_ids = categ_obj.search(
                    [('write_date', '>', shop.woocommerce_last_update_category_date), ('woocom_id', '!=', False)])
            else:
                categ_ids = categ_obj.search([('woocom_id', '!=', False)])
            for each in categ_ids:
                cat_vals = ({
                    'id': each.woocom_id,
                    'name': each.name,
                    'parent': each.parent_id and str(each.parent_id.woocom_id) or '0',
                })
                categ_url = 'products/categories/' + str(each.woocom_id)
                cat_vals = wcapi.post(categ_url, cat_vals)

    # @api.multi
    def updateWoocomProductTag(self):
        print("updateWoocomProducsTagggggggggggg", self)

        tag_obj = self.env['product.tags']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            if shop.woocommerce_last_update_product_tag_date:
                tag_ids = tag_obj.search(
                    [('write_date', '>', shop.woocommerce_last_update_product_tag_date), ('tag_id', '!=', False)])
            else:
                tag_ids = tag_obj.search([('tag_id', '!=', False)])
            for each in tag_ids:
                tag_vals = {
                    'name': each.name,
                    'slug': each.slud_code,
                    'description': each.description,
                    'id': each.tag_id,
                }
                tag_url = 'products/tags/' + str(each.tag_id)
                tag_val = wcapi.post(tag_url, tag_vals)

    # @api.multi
    def updateWoocomProduct(self):
        # update product details,image and variants
        prod_templ_obj = self.env['product.template']
        prdct_obj = self.env['product.product']
        stock_quant_obj = self.env['stock.quant']
        # inventry_line_obj = self.env['stock.inventory.line']
        prod_att_obj = self.env['product.attribute']
        prod_attr_vals_obj = self.env['product.attribute.value']
        # inventry_line_obj = self.env['stock.inventory.line']
        # inventry_obj = self.env['stock.inventory']
        stock_quanty = self.env['stock.quant']

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            if shop.woocommerce_last_update_product_data_date:
                product_data_ids = prod_templ_obj.search(
                    [('write_date', '>', shop.woocommerce_last_update_product_data_date), ('woocom_id', '!=', False)])
            else:
                product_data_ids = prod_templ_obj.search([('woocom_id', '!=', False)])
            #             product_data_ids = prod_templ_obj.browse([55])
            for each in product_data_ids:
                # categs = [{
                #     "id": each.woo_categ.woocom_id,
                # }]
                # parent_id = each.woo_categ.parent_id
                # while parent_id:
                #     categs.append({
                #         "id": parent_id.woocom_id,
                #     })
                #     parent_id = parent_id.parent_id
                categs = []
                for categories in each.woo_categories:
                    categs.append({
                        "id": categories.woocom_id,
                    })
                    parent_id = categories.parent_id
                    while parent_id:
                        categs.append({
                            "id": parent_id.woocom_id,
                        })
                        parent_id = parent_id.parent_id
                print("<>>><><>categs>><><>", categs)
                image_list = []
                count = 1
                for image_data in each.woocom_product_img_ids:
                    if image_data.woocom_img_id:
                        image_list.append({
                            'id': image_data.woocom_img_id,
                            'src': image_data.url,
                            'position': count
                        })
                    else:
                        image_list.append({
                            'src': image_data.url,
                            'position': count
                        })
                    count += 1
                prod_vals = {
                    'name': str(((each.name).encode('ascii', 'ignore')).decode('utf-8')),
                    'sku': str(each.default_code),
                    "regular_price": each.woocom_regular_price and str(each.woocom_regular_price) or '0.00',
                    'sale_price': each.woocom_price and str(each.woocom_price) or '0.00',
                    'weight': str(each.product_wght),
                    # str(each.with_context(pricelist=shop.pricelist_id.id).price),
                    'dimensions': {
                        'width': str(each.product_width),
                        'height': str(each.product_hght),
                        'length': str(each.product_lngth),

                    },
                    'description': each.description_sale and str(each.description_sale) or '',
                    'short_description': each.description_sale and str(each.description_sale) or '',
                    'images': image_list,
                    'categories': categs,
                    'id': int(each.woocom_id),
                }
                # print("<><><><><>prod_vals<><><>>", prod_vals)
                if each.attribute_line_ids:
                    p_ids = prdct_obj.search([('product_tmpl_id', '=', each.id)])
                    qaunt = 0
                    if p_ids:
                        stck_quant_id = stock_quanty.search(
                            [('product_id', 'in', p_ids.ids), ('location_id', '=', shop.warehouse_id.lot_stock_id.id)])
                        for stock in stck_quant_id:
                            qaunt += stock.quantity
                    prod_vals.update({
                        'type': 'variable',
                        'stock_quantity': int(qaunt),
                    })
                else:
                    p_ids = prdct_obj.search([('product_tmpl_id', '=', each.id)])
                    qaunt = 0
                    if p_ids:
                        stck_quant_id = stock_quanty.search(
                            [('product_id', '=', p_ids[0].id), ('location_id', '=', shop.warehouse_id.lot_stock_id.id)])
                        for stock in stck_quant_id:
                            qaunt += stock.quantity
                    prod_vals.update({
                        'type': 'simple',
                        'stock_quantity': int(qaunt),
                    })
                if prod_vals.get('type') == 'simple':
                    prod_url = 'products/' + str(each.woocom_id)
                    prd_response = wcapi.post(prod_url, prod_vals)
                attributes = []
                if each.attribute_line_ids:
                    attributes = []
                    for attr in each.attribute_line_ids:
                        values = []
                        for attr_value in attr.value_ids:
                            values.append(str(((attr.attribute_id.name).encode('ascii', 'ignore')).decode('utf-8')))
                        attributes.append({
                            'id': int(attr.attribute_id.woocom_id),
                            'name': str(((attr.attribute_id.name).encode('ascii', 'ignore')).decode('utf-8')),
                            'options': values,
                            'variation': 'true',
                            'visible': 'false'
                        })
                    if attributes:
                        prod_vals.update({'attributes': attributes})
                        prod_url = 'products/' + str(each.woocom_id)
                        prod_export_res = wcapi.post(prod_url, prod_vals)

                prod_var_id = prdct_obj.search([('product_tmpl_id', '=', each.id)])

                for var in prod_var_id:
                    if not var.product_template_attribute_value_ids:
                        continue
                    values = []
                    for att in var.product_template_attribute_value_ids:
                        values.append({
                            'id': att.attribute_id.woocom_id,
                            'option': str(((att.name).encode('ascii', 'ignore')).decode('utf-8')),
                        })
                    var_vals = {
                        'name': str((var.name).encode('ascii', 'ignore')),
                        #                     'sale_price': str(var.with_context(pricelist=shop.pricelist_id.id).price),
                        'regular_price': var.woocom_regular_price and str(var.woocom_regular_price) or '0.00',
                        'sale_price': var.woocom_price and str(var.woocom_price) or '0.00',
                        'weight': str(var.product_wght),
                        'dimensions': {
                            'width': str(var.product_width),
                            'height': str(var.product_hght),
                            'length': str(var.product_lngth),

                        },
                        'attributes': values,
                    }
                    if var.woocom_variant_id:
                        var_url = 'products/' + str(each.woocom_id) + '/variations/' + str(var.woocom_variant_id)
                    else:
                        var_url = 'products/' + str(each.woocom_id) + '/variations'
                    prd_response = wcapi.post(var_url, var_vals).json()
                    # print("<><><><><>prd_response<><><>>", prd_response)
                    var.write({'woocom_variant_id': prd_response.get('id')})
        return True

    # @api.multi
    def updateWoocomInventory(self):
        print("updateWoocomInventoryupdateWoocomInventory")
        prod_templ_obj = self.env['product.template']
        prdct_obj = self.env['product.product']
        inv_wiz = self.env['stock.change.product.qty']
        stck_quant = self.env['stock.quant']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            if self.env.context.get('product_ids'):
                print("inside itttttttttt")
                p_ids = prod_templ_obj.browse(self.env.context.get('product_ids'))
            elif shop.woocommerce_last_update_inventory_date:
                stck_ids = stck_quant.search(
                    [('write_date', '>', shop.woocommerce_last_update_inventory_date)])
                p_ids = []
                for i in stck_ids:
                    if i.product_id.product_tmpl_id not in p_ids:
                        p_ids.append(i.product_id.product_tmpl_id)
            else:
                p_ids = prod_templ_obj.search([('woocom_id', '!=', False)])

            for temp in p_ids:
                print("temp.product_variant_counttemp.product_variant_count", temp.product_variant_count)
                if (temp.product_variant_count) > 1:
                    prod_var_id = prdct_obj.search([('product_tmpl_id', '=', temp.id)])
                    print("prod_var_id", prod_var_id)
                    for var_id in prod_var_id:
                        stck_id = stck_quant.search(
                            [('product_id', '=', var_id.id), ('location_id', '=', shop.warehouse_id.lot_stock_id.id)])
                        qty = 0
                        for stck in stck_id:
                            qty += stck.quantity
                        pro_vals = {
                            'stock_quantity': int(qty),
                            'manage_stock': 'true'
                        }
                        if qty > 0:
                            pro_vals.update({'in_stock': True})
                        else:
                            pro_vals.update({'in_stock': False})
                        url = "products/" + str(temp.woocom_id) + "/variations/" + str(var_id.woocom_variant_id)
                        pro_res = wcapi.post(url, pro_vals).json()
                        print("proooooooooo_resssssss", pro_res)
                else:
                    product_ids = prdct_obj.search([('product_tmpl_id', '=', temp.id)])
                    if product_ids:
                        stck_id = stck_quant.search([('product_id', '=', product_ids[0].id),
                                                     ('location_id', '=', shop.warehouse_id.lot_stock_id.id)])
                        qty = 0
                        for stck in stck_id:
                            qty += stck.quantity
                        pro_vals = {
                            'stock_quantity': int(qty),
                            'manage_stock': 'true'
                        }
                        if qty > 0:
                            pro_vals.update({'in_stock': True})
                        else:
                            pro_vals.update({'in_stock': False})
                        pro_url = 'products/' + str(temp.woocom_id)
                        pro_res = wcapi.post(pro_url, pro_vals).json()
                        print("proooooooooo_resssssss22222222", pro_res)
            shop.write({'woocommerce_last_update_inventory_date': datetime.now()})

    # @api.multi
    def updateWoocomOrderStatus(self):
        print("updateWoocomOrderStatusssssssssswwwwwwwwwww", self)

        sale_order_obj = self.env['sale.order']

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')

            sale_order_ids = sale_order_obj.search([('woocom_id', '!=', False), (
                'order_status', 'in', ['pending', 'processing', 'on-hold', 'completed', 'refunded'])])
            for sale_order in sale_order_ids:
                ordr_url = 'orders/' + str(sale_order.woocom_id)
                order_vals = {
                    'status': sale_order.order_status,
                }

                # data1 = {
                #     'key':'_aftership_tracking_number',
                #     'value': sale_order.picking_ids.carrier_tracking_ref,
                # }
                # data2 = {
                #     'key':'_aftership_tracking_shipdate',
                #     'value': sale_order.picking_ids.scheduled_date,
                # }
                # data3 = {
                #     'key':'_aftership_tracking_postal',
                #     'value': sale_order.picking_ids.partner_id.zip,
                # }
                # track_list.append(data1)
                # track_list.append(data2)
                # track_list.append(data3)
                # order_vals.update({'meta_data': track_list})

                ord_res = wcapi.post(ordr_url, order_vals).json()
                if ord_res:
                    sale_order.write({'order_status': sale_order.order_status})

    # @api.multi
    def exportWoocomOrder(self):
        print("expotWoocomOrderrrrrrrrwwwwwwwwwwwww", self)

        sale_order_obj = self.env['sale.order']
        res_partner_obj = self.env['res.partner']
        carrier_obj = self.env['delivery.carrier']
        #         status_obj = self.env['presta.order.status']
        sale_order_line_obj = self.env['sale.order.line']
        prod_attr_val_obj = self.env['product.attribute.value']
        prod_templ_obj = self.env['product.template']
        product_obj = self.env['product.product']
        invoice_obj = self.env['account.invoice.send']
        # invoice_refund_obj = self.env['account.invoice.refund']
        return_obj = self.env['stock.return.picking']
        return_line_obj = self.env['stock.return.picking.line']
        prod_templ_obj = self.env['product.template']
        prdct_obj = self.env['product.product']
        categ_obj = self.env['product.category']

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
                order_ids = sale_order_obj.browse(self.env.context.get('export_product_ids'))
            else:
                order_ids = sale_order_obj.search([('to_be_exported', '=', True)])
            for order in order_ids:
                order_name = order.partner_id.name
                name_list = order_name.split(' ')
                first_name = name_list[0]
                if len(name_list) > 1:
                    last_name = name_list[1]
                else:
                    last_name = name_list[0]
                data = {
                    'customer_id': int(order.partner_id.woocom_id),
                    'payment_method': str(order.woocom_payment_mode),
                    'status': str(order.order_status),
                    "billing": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "address_1": order.partner_id.street,
                        "address_2": order.partner_id.street2,
                        "city": order.partner_id.city,
                        "state": str(order.partner_id.state_id.code),
                        "postcode": str(order.partner_id.zip),
                        "country": str(order.partner_id.country_id.code),
                        "email": str(order.partner_id.email),
                        "phone": str(order.partner_id.phone)
                    },

                    "shipping": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "address_1": order.partner_id.street,
                        "address_2": order.partner_id.street2,
                        "city": order.partner_id.city,
                        "state": str(order.partner_id.state_id.code),
                        "postcode": str(order.partner_id.zip),
                        "country": str(order.partner_id.country_id.code)
                    },
                    "total": str(order.amount_total),
                    "line_items": [
                    ],
                    "shipping_lines": [
                        {
                            'method_id': str(order.carrier_id.woocom_id),
                            'method_title': str(order.carrier_id.name),
                        }
                    ]
                }
                if order.order_line:
                    line_items = []
                    for line in order.order_line:
                        product = False
                        if line.product_id and line.product_id.product_template_attribute_value_ids:
                            product = line.product_id.woocom_variant_id
                        else:
                            product = line.product_id.product_tmpl_id.woocom_id
                        line_items.append({
                            "product_id": product,
                            "name": line.name,
                            "quantity": str(line.product_uom_qty),
                            "price": str(line.price_unit),
                            "shipping_total": str(line.price_unit),

                        })
                    data.update({
                        'line_items': line_items
                    })
                ordr_export_res = wcapi.post("orders", data).json()
                if ordr_export_res:
                    order.write({'woocom_id': ordr_export_res.get('id'), 'to_be_exported': False})

    # @api.multi
    def exportWoocomCategories(self):
        print("EXPOCATTTTTTTTTTt")
        categ_obj = self.env['woocom.category']

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
                category_ids = categ_obj.browse(self.env.context.get('export_product_ids'))
            else:
                category_ids = categ_obj.search([('to_be_exported', '=', True)])
            for categ in category_ids:
                name = categ.name
                print("datadatadata?name??", name)
                name = name.encode('ascii', 'ignore')
                # name = bytes(name.encode())
                name = bytes.decode(name)
                print("name???????????", name)
                data = {
                    "name": name,
                    'slug': name.replace(' ', '_'),
                    "parent": categ.parent_id.woocom_id and int(categ.parent_id.woocom_id) or 0,
                }
                # data = jsonencode(data, ensure_ascii=False)
                # data = data.encode('ascii', 'ignore')
                print("datadatadata???????????????", data)
                res = wcapi.post("products/categories", data)
                res = res.json()
                print("resresresresres>>>>>>>>>>>", res)
                if res:
                    categ.write({'woocom_id': res.get('id'), 'to_be_exported': False})

    # @api.multi
    def exportWoocomProductTags(self):
        print("ExportTagsssssssssssssssssssssssss")
        tag_obj = self.env['product.tags']

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
                tag_ids = tag_obj.browse(self.env.context.get('export_product_ids'))
            else:
                tag_ids = tag_obj.search([('to_be_exported', '=', True)])

            for tag in tag_ids:
                data = {
                    "name": tag.name,
                    'slug': tag.slud_code,
                    'id': tag.tag_id,
                    'description': tag.description,
                }
                res = wcapi.post("products/tags", data)
                res = res.json()
                if res:
                    tag.write({'tag_id': res.get('id'), 'to_be_exported': False})

    # @api.multi
    def exportWoocomCustomers(self):
        res_partner_obj = self.env['res.partner']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
                customer_ids = res_partner_obj.browse(self.env.context.get('export_product_ids'))
            else:
                customer_ids = res_partner_obj.search([('to_be_exported', '=', True)])
            print("Customer_idsss", customer_ids)
            for customer in customer_ids:
                customer_name = customer.name
                name_list = customer_name.split(' ')
                first_name = name_list[0]
                if len(name_list) > 1:
                    last_name = name_list[1]
                else:
                    last_name = name_list[0]
                custom_data = {
                    "email": str(customer.email),
                    "first_name": first_name,
                    "last_name": last_name,
                    "password": str(customer.email),
                    "billing": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "company": str(customer.parent_id.name),
                        "address_1": customer.street or '',
                        "address_2": customer.street2 or '',
                        "city": customer.city or '',
                        "state": str(customer.state_id.code),
                        "postcode": str(customer.zip) or '',
                        "country": str(customer.country_id.code),
                        "email": str(customer.email),
                        "phone": str(customer.phone),
                    },
                    "shipping": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "company": str(customer.parent_id.name),
                        "address_1": customer.street or '',
                        "address_2": customer.street2 or '',
                        "city": customer.city or '',
                        "state": str(customer.state_id.code),
                        "postcode": str(customer.zip) or '',
                        "country": str(customer.country_id.code)
                    }
                }
                cust_export_res = wcapi.post("customers", custom_data).json()
                if cust_export_res:
                    customer.write({'woocom_id': cust_export_res.get('id'), 'to_be_exported': False})

    # @api.multi
    def exportWoocomProduct(self):
        print("EXPOPRODDDDDDDD")
        prod_templ_obj = self.env['product.template']
        prdct_obj = self.env['product.product']
        stock_quanty = self.env['stock.quant']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location,
                        consumer_key=shop.woocommerce_instance_id.consumer_key,
                        consumer_secret=shop.woocommerce_instance_id.secret_key, wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
                product_ids = prod_templ_obj.browse(self.env.context.get('export_product_ids'))
            else:
                product_ids = prod_templ_obj.search([('product_to_be_exported', '=', True)])
            print('Products Iddsssss', product_ids)
            for product in product_ids:
                categs = [{
                    "id": int(product.woo_categ.woocom_id),
                }]
                parent_id = product.woo_categ.parent_id
                while parent_id:
                    categs.append({
                        "id": int(parent_id.woocom_id),
                    })
                    parent_id = parent_id.parent_id
                images = []
                count = 0
                for image_data in product.woocom_product_img_ids:
                    images.append({
                        'src': image_data.url,
                        'position': count
                    })
                    count += 1
                name = translator.translate(product.name, dest='en')
                # print("namenamenamemnamenaenamenamename>>>>>>>>>>>>>>>>>>>>>>>",(product.name).decode('utf-8'))

                prod_vals = {
                    "name": str(name.text),
                    #                     str((product.name).encode('latin-1', 'ignore').decode('latin-1')),# str(product.name), #.encode('ascii' , 'ignore')),
                    #                    "slug": str(((product.name).encode('latin-1' , 'ignore')).decode('latin-1')).replace(' ','_'),
                    "sku": str(product.sku) or str(product.default_code),
                    #                    "manage_stock": 'true',s
                    "weight": str(product.product_wght),
                    #                    "in_stock":'true',
                    #                     "stock_quantity": product.qty_available ,
                    "dimensions": {
                        "length": str(product.product_lngth),
                        "width": str(product.product_width),
                        "height": str(product.product_hght),

                    },
                    "regular_price": product.woocom_regular_price and str(product.woocom_regular_price) or '0.00',
                    "sale_price": product.woocom_price and str(product.woocom_price) or '0.00',
                    "images": images,
                    "categories": categs,
                    'description': str(product.description_sale),
                    'in_stock': 'true',
                    'manage_stock': 'true'
                }
                if product.attribute_line_ids:
                    p_ids = prdct_obj.search([('product_tmpl_id', '=', product[0].id)])
                    quant = 0
                    if p_ids:
                        stck_quant_id = stock_quanty.search(
                            [('product_id', 'in', p_ids.ids), ('location_id', '=', shop.warehouse_id.lot_stock_id.id)])
                        for stock in stck_quant_id:
                            quant += stock.quantity
                    prod_vals.update({
                        'type': 'variable',
                        'stock_quantity': int(quant),
                    })
                else:
                    p_ids = prdct_obj.search([('product_tmpl_id', '=', product[0].id)])
                    quant = 0
                    if p_ids:
                        stck_quant_id = stock_quanty.search(
                            [('product_id', '=', p_ids[0].id), ('location_id', '=', shop.warehouse_id.lot_stock_id.id)])
                        for stock in stck_quant_id:
                            quant += stock.quantity
                    prod_vals.update({
                        'type': 'simple',
                        'stock_quantity': int(quant),
                    })
                print("prodytcs valssssssssss", prod_vals)
                #                prod_export_res_d = wcapi.post("products", prod_vals)
                #                prod_export_res = prod_export_res_d.json()
                #                print("prod_export_resprod_export_res",prod_export_res,prod_export_res_d)
                #                # if prod_export_res_d.data.status == 200:
                #                product.write({'woocom_id': prod_export_res.get('id'), 'product_to_be_exported': False})
                if product.attribute_line_ids:
                    attributes = []
                    for attr in product.attribute_line_ids:
                        values = []
                        attr_name = translator.translate(attr.attribute_id.name, dest='en')
                        print("attr_nameattr_nameattr_nameattr_nameattr_name>>>>>>>>>>>>>>>>>>>>>>>", attr_name.text)
                        for attr_value in attr.value_ids:
                            values.append(attr_value.name)
                        attributes.append({
                            'name': str(attr_name.text),
                            'options': values,
                            'variation': True,
                            'visible': False
                        })
                        # data = {
                        #     "name": attr.attribute_id.name,
                        #     "slug": attr.attribute_id.name.replace(' ', '_'),
                        #     "type":'variable',
                        #     "order_by": "menu_order",
                        #     "has_archives": True
                        # }
                    print("Attirubtesss", attributes)
                    if attributes:
                        prod_vals.update({'attributes': attributes})
                        print("prod_vals.get('sku')", prod_vals.get('sku'), prod_vals.get('type'))
                        prod_export_res_attr_d = wcapi.post("products", prod_vals)
                        prod_export_res_attr = prod_export_res_attr_d.json()
                        print("prod_export_resprod_export_resprod_export_res2222222", prod_export_res_attr,
                              prod_export_res_attr_d)
                        if prod_export_res_attr:
                            product.write(
                                {'woocom_id': prod_export_res_attr.get('id'), 'product_to_be_exported': False})

                        prod_var_id = prdct_obj.search([('product_tmpl_id', '=', product.id)])
                        for variant in prod_var_id:
                            stck_id = stock_quanty.search([('product_id', '=', variant.id),
                                                           ('location_id', '=', shop.warehouse_id.lot_stock_id.id)])
                            qty = 0
                            for stck in stck_id:
                                qty += stck.quantity
                            variation_vals = {
                                'sku': str(variant.default_code),
                                'stock_quantity': int(qty),
                                'in_stock': 'true',
                                'manage_stock': 'true',
                                "sale_price": variant.woocom_price and str(variant.woocom_price) or '0.00',
                                'regular_price': variant.woocom_regular_price and str(
                                    variant.woocom_regular_price) or '0.00',
                                'weight': str(variant.product_wght),
                                'attributes': [{'option': avalue.name, 'name': str(
                                    ((avalue.attribute_id.name).encode('ascii', 'ignore')).decode('utf-8'))} for avalue
                                               in
                                               variant.product_template_attribute_value_ids],
                                "dimensions": {
                                    "length": str(variant.product_lngth),
                                    "width": str(variant.product_width),
                                    "height": str(variant.product_hght),
                                },
                            }
                            url_var = "products/" + str(prod_export_res_attr.get('id')) + "/variations"
                            print("urllll for variationsss", url_var)
                            prod_var_res_d = wcapi.post(url_var, variation_vals)
                            prod_var_res = prod_var_res_d.json()
                            print("prod_var_resprod_var_resprod_var_res", prod_var_res_d, prod_var_res)
                            if prod_var_res:
                                variant.write(
                                    {'woocom_variant_id': prod_var_res.get('id'), 'product_to_be_exported': False})
                else:
                    print("prodytcs valssssssssss", prod_vals)
                    prod_export_res_d = wcapi.post("products", prod_vals)
                    prod_export_res = prod_export_res_d.json()
                    print("prod_export_resprod_export_res", prod_export_res, prod_export_res_d)
                    # if prod_export_res_d.data.status == 200:
                    product.write({'woocom_id': prod_export_res.get('id'), 'product_to_be_exported': False})

    @api.model
    def auto_scheduler_process_import_orders(self, cron_mode=True):
        # print ("SCHEDULAR_import_orderssssssssss")
        search_ids = self.search([('auto_import_order', '=', True)])
        if search_ids:
            search_ids.importWoocomOrder()

    @api.model
    def auto_scheduler_process_import_products(self, cron_mode=True):
        # print ("SCHEDULAR_import_productsssssssssssssssss")
        search_ids = self.search([('auto_import_products', '=', True)])
        if search_ids:
            search_ids.importWoocomProduct()

    @api.model
    def auto_scheduler_process_import_inventory(self, cron_mode=True):
        # print ("SCHEDULAR_update_inventoryyyyyyyyyy")
        search_ids = self.search([('auto_update_inventory', '=', True)])
        if search_ids:
            search_ids.importWoocomInventory()

    @api.model
    def auto_scheduler_process_update_orders(self, cron_mode=True):
        # print ("SCHEDULAR_update_orderssssssssssss")
        search_ids = self.search([('auto_update_order_status', '=', True)])
        if search_ids:
            search_ids.updateWoocomOrderStatus()

    @api.model
    def auto_scheduler_process_update_products(self, cron_mode=True):
        # print ("SCHEDULAR_update_productsssssssss")
        search_ids = self.search([('auto_update_product_data', '=', True)])
        if search_ids:
            search_ids.updateWoocomProduct()

    # @api.model
    # def auto_scheduler_process_update_customers(self, cron_mode=True):
    #     # print ("SCHEDULAR_update_customerssssssssss")
    #     search_ids = self.search([('auto_update_customer_data', '=', True)])
    #     if search_ids:
    #         search_ids.updateWoocomCustomer()
    #
