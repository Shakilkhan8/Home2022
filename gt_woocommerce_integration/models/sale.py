# -*- encoding: utf-8 -*-
##############################################################################
#
#    Globalteckz
#    Copyright (C) 2012 (http://www.globalteckz.com)
#
##############################################################################
from odoo import api, fields, models, _

class sale_order(models.Model):
    _inherit = "sale.order"
                    

                                   
    shop_id=fields.Many2one('sale.shop','Shop ID')
#     order_status = fields.Many2one('woocom.order.status', string="Status")
    order_status = fields.Selection([('pending','Pending payment'),('processing','Processing'),('on-hold','On hold'),('completed','Completed'),('cancelled','Cancelled'),('refunded','Refunded'),('failed','Failed'),('customer-care','Customer Care'),('delivered','Delivered'),('exchange-request','Exchange Request')], string="Status")
    woocom_order_ref=fields.Char('Order Reference')
    woocom_payment_mode=fields.Many2one('payment.gatway',string='Payment mode')
    carrier_woocommerce=fields.Many2one('delivery.carrier',string='Carrier In Woocommerce')
    woocommerce_order=fields.Boolean('Woocommerce Order')
    token=fields.Char('Token')
    woocom_id =  fields.Char('woocom_id')
    woocom_variant_id = fields.Char('Woocommerce Variant ID')
    shop_ids = fields.Many2many('sale.shop', 'saleorder_shop_rel', 'saleorder_id', 'shop_id', string="Shop")
    to_be_exported = fields.Boolean(string="To be exported?")

class sale_order_line(models.Model):
    _inherit='sale.order.line'
    
    gift=fields.Boolean('Gift')
    gift_message=fields.Char('Gift Message')
    wrapping_cost=fields.Float('Wrapping Cost')
    woocom_id = fields.Char(string="Woocom ID")
    disc_price = fields.Float(string="Woocom Tax Amount",default=0.0)
    
    
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded']+line.disc_price,
            })
    
class WoocomOrderStatus(models.Model):
    _name = 'woocom.order.status'

    name = fields.Char(string="Status")
    woocom_id = fields.Char(string="Woocom ID")
