# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import HttpCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleDelivery(HttpCase):

    def setUp(self):
        super().setUp()

        self.env.ref('base.user_admin').write({
            'name': 'Mitchell Admin',
            'street': '215 Vine St',
            'phone': '+1 555-555-5555',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_39').id,
        })

        # Remove taxes completely during the following tests.
        self.env.companies.account_sale_tax_id = False
        self.env['product.product'].create({
            'name': "Plumbus",
            'list_price': 100.0,
            'website_published': True,
        })

        self.gift_card = self.env['product.product'].create({
            'name': 'TEST - Gift Card',
            'list_price': 50,
            'type': 'service',
            'is_published': True,
            'sale_ok': True,
        })

        # Disable any other program
        self.env['loyalty.program'].search([]).write({'active': False})

        self.gift_card_program = self.env['loyalty.program'].create({
            'name': 'Gift Cards',
            'program_type': 'gift_card',
            'applies_on': 'future',
            'trigger': 'auto',
            'rule_ids': [Command.create({
                'reward_point_amount': 1,
                'reward_point_mode': 'money',
                'reward_point_split': True,
                'product_ids': self.gift_card,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
                'discount_applicability': 'order',
                'required_points': 1,
                'description': 'PAY WITH GIFT CARD',
            })],
        })

        # Create a gift card to be used
        self.env['loyalty.card'].create({
            'program_id': self.gift_card_program.id,
            'points': 50000,
            'code': '123456',
        })

        self.ewallet_program = self.env['loyalty.program'].create({
            'name': "eWallet",
            'program_type': 'ewallet',
            'applies_on': 'future',
            'trigger': 'auto',
            'reward_ids': [Command.create({
                'description': "Pay with eWallet",
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
            })],
        })

        self.ewallet = self.env['loyalty.card'].create({
            'program_id': self.ewallet_program.id,
            'points': 6e66,
            'code': 'infinite-money-glitch',
        })

        self.product_delivery_normal1 = self.env['product.product'].create({
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
        })

        self.product_delivery_normal2 = self.env['product.product'].create({
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
        })

        self.normal_delivery = self.env['delivery.carrier'].create({
            'name': 'delivery1',
            'fixed_price': 5,
            'delivery_type': 'fixed',
            'website_published': True,
            'product_id': self.product_delivery_normal1.id,
        })

        self.normal_delivery2 = self.env['delivery.carrier'].create({
            'name': 'delivery2',
            'fixed_price': 10,
            'delivery_type': 'fixed',
            'website_published': True,
            'product_id': self.product_delivery_normal2.id,
        })

    def test_shop_sale_gift_card_keep_delivery(self):
        # Get admin user and set his preferred shipping method to normal delivery
        # This test also tests that we can indeed pay delivery fees with gift cards/ewallet
        admin_user = self.env.ref('base.user_admin')
        admin_user.partner_id.write({'property_delivery_carrier_id': self.normal_delivery.id})

        self.start_tour("/", 'shop_sale_loyalty_delivery', login='admin')

    def test_shipping_discount(self):
        """
        Check display of shipping discount promotion on checkout,
        combined with another reward (eWallet).
        """
        self.env['loyalty.program'].create({
            'name': "Buy 3, get up to $75 discount on shipping",
            'program_type': 'promotion',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'minimum_qty': 3.0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'shipping',
                'discount_max_amount': 75.0,
            })],
        })
        self.normal_delivery.fixed_price = 100
        self.start_tour("/", 'check_shipping_discount', login="admin")
