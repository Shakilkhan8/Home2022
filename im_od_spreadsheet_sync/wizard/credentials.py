from odoo import models, fields, api
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from odoo.exceptions import  UserError
from datetime import timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import datetime
import base64
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
import json
import logging
_logger = logging.getLogger(__name__)

class JSONCredentials(models.TransientModel):
    _name='google.json.credentials'
    _description='Credential loader'
    
    email =fields.Char('Authorized Email')
    json_credentials=fields.Binary()
    scope = fields.Char(compute='_compute_help_fields')
    redirect_url=fields.Char(compute='_compute_help_fields')
    origin_domain=fields.Char(compute='_compute_help_fields')
    loaded=fields.Boolean(compute='check_loaded')
    
    @api.depends('email')
    def check_loaded(self):
        for rec in self:
            cred = self.env['sheet.api.credentials'].sudo().search([('live','=',True)],limit=1)
            if cred:
                rec.loaded=True 
            else:
                rec.loaded=False
    @api.depends('email')
    def _compute_help_fields(self):
        for rec in self:
            get_param = self.env['ir.config_parameter'].sudo().get_param
            base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
            rec.scope='https://www.googleapis.com/auth/spreadsheets'
            rec.redirect_url=base_url + '/sheet/authentication'
            rec.origin_domain=base_url
    def save_credentials_from_json(self):
        cred = self.env['sheet.api.credentials'].sudo().search([],limit=1)
        if cred:
            cred.live = False
            cred.email=self.email 
        else:
            cred = self.env['sheet.api.credentials'].sudo().create({'email':self.email})
        cred.clear_sheet_credentials()
        cred.json_file=self.json_credentials
        return cred.activate()
        