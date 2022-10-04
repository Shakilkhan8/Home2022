# -*- coding: utf-8 -*-
"""
                                                             ###                 
                                                          #########&             
                                                         ###########             
                                                          ##########             
                                                           #######               
                                                                                
  #####    ######%#######         #####         ##########   #####   #############
  ##### ###################      #######     ############### ##### #############  
  ##### #####   ####   #####    ########     #####     &#### ##### #####          
  ##### #####   ####   #####    #########    #####     &#### ##### ############   
  ##### #####   ####   #####   ##### #####   #####     &#### #####   ############&
  ##### #####   ####   #####  #####   ####   #####     &#### #####           #####
  ##### #####   ####   #####  ####    #####  #####     &#### ##### ###############
  ##### #####   ####   ##### #####     ##### #####     &#### ##### #############  
  
  See manifest for license information
"""

from odoo import api, fields, models, _
from datetime import timedelta
from google.auth.transport.requests import Request

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow


import base64
import json
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    spreadsheet_client_id = fields.Char("Client_id", config_parameter='google_spreadsheet_client_id', default='')
    spreadsheet_client_secret = fields.Char("Client_key", config_parameter='google_spreadsheet_client_secret', default='')
    spreadsheet_refresh_token = fields.Char("Refresh Tokent", config_parameter='google_spreadsheet_refresh_token', default='')
    spreadsheet_user_email=fields.Char('User Email',config_parameter="google_spreadsheet_user_email",default='')
    spreadsheet_token = fields.Char("Tokent", config_parameter='google_spreadsheet_token', default='')
    spreadsheet_expiry = fields.Char("Expiry", config_parameter='google_spreadsheet_expiry', default='')
    google_spreadsheet_authorization_code = fields.Char(string='Sheets Authorization Code', config_parameter='google_spreadsheet_authorization_code')
    google_spreadsheet_uri =fields.Char( string='Authorization URI', help="The URL to generate the authorization code from Google")
    is_google_spreadsheet_token_generated = fields.Boolean(string='Refresh Sheet Token Generated')
    spreadsheet_json_file=fields.Binary('JSON Credential')
    @api.depends('google_spreadsheet_authorization_code')
    
            
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        refresh_token = self.env['ir.config_parameter'].sudo().get_param('google_spreadsheet_refresh_token')
        res.update(is_google_spreadsheet_token_generated=bool(refresh_token))
        return res
    
    def action_load_json(self):
        self.ensure_one()
        template = self.env.ref('im_od_spreadsheet_sync.google_spreadsheet_auth_code_wizard')
        return {
            'name': _('Load JSON Credentials'),
            'type': 'ir.actions.act_window',
            'res_model': 'google.json.credentials',
            'views': [(template.id, 'form')],
            'target': 'new',
        }        
     
   
        