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
import json
import logging
_logger = logging.getLogger(__name__)


class SheetApiCredentials(models.Model):
    _name='sheet.api.credentials'
    _description='Google Sheet API Credentials'
    _rec_name='email'
    email =fields.Char('API User Email',required=True,help="This email is the Test User in Google Sheet Api Athentication")
    live=fields.Boolean('Live')
    valid=fields.Boolean('Valid')
    json_file=fields.Binary('JSON Credentials')
    scope = fields.Char(compute='_compute_help_fields')
    redirect_url=fields.Char(compute='_compute_help_fields')
    origin_domain=fields.Char(compute='_compute_help_fields')
    
    @api.depends('email')
    def _compute_help_fields(self):
        for rec in self:
            get_param = self.env['ir.config_parameter'].sudo().get_param
            base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
            rec.scope='https://www.googleapis.com/auth/spreadsheets'
            rec.redirect_url=base_url + '/sheet/authentication'
            rec.origin_domain=base_url
    #scope=fields.Char(default='https://www.googleapis.com/auth/spreadsheets')
    
    def build_flow(self):
        return
    def buil_json_from_file(self):
        data= base64.b64decode(self.json_file).decode('ascii')
        json_data=json.loads(data)
        return json_data
    def activate(self):
        self.ensure_one()
        if not self.json_file:
            raise UserError('No JSON Client file')        
        token_json=self.buil_json_from_file()

        flow=Flow.from_client_config(token_json,[self.scope])
        flow.redirect_uri = token_json['web']['redirect_uris'][0]
        authorization_url, state = flow.authorization_url(
                                    access_type='offline',
                                    login_hint=self.email,
                                    include_granted_scopes='true')
        return { "type":'ir.actions.act_url',
                "url": "%s" % authorization_url,
                "target":"new"
            }
    @api.model
    def set_credentials(self,state,code,auth_url):
        token_json=self.buil_json_from_file()
        flow = Flow.from_client_config(token_json,scopes=[self.scope],state=state)
        flow.redirect_uri = token_json['web']['redirect_uris'][0]
        authorization_response = auth_url
        kwargs=token_json['web']
        try :
            flow.fetch_token(authorization_response=auth_url)
        except Exception as e:
            return e
        credentials = flow.credentials
        if credentials:
            self.save_credentials(credentials)
            self.live =True
            self.valid=True
        else:
            self.live=False
            self.valid=True
        return 1
    def save_credentials(self,credentials):
        Config=self.env['ir.config_parameter'].sudo()
        Config.set_param('google_spreadsheet_client_id',credentials.client_id)
        Config.set_param('google_spreadsheet_client_secret',credentials.client_secret)
        Config.set_param('google_spreadsheet_refresh_token',credentials.refresh_token)
        Config.set_param('google_spreadsheet_token',credentials.token)
        Config.set_param('google_spreadsheet_token_uri',credentials.token_uri)
        Config.set_param('google_spreadsheet_scopes',credentials.scopes[0])
        Config.set_param('google_spreadsheet_expiry',credentials.expiry.strftime('%Y-%m-%dT%H:%M:%S'))
    def clear_sheet_credentials(self):
        Config=self.env['ir.config_parameter'].sudo()
        Config.set_param('google_spreadsheet_client_id','')
        Config.set_param('google_spreadsheet_client_secret','')
        Config.set_param('google_spreadsheet_refresh_token','')
        Config.set_param('google_spreadsheet_token','')
        Config.set_param('google_spreadsheet_token_uri','')
        Config.set_param('google_spreadsheet_scopes','')
        Config.set_param('google_spreadsheet_expiry','')
    def get_cred_token(self):
        params = self.env['ir.config_parameter'].sudo()
        return {
            'token': params.get_param('google_spreadsheet_token'),
            'refresh_token': params.get_param('google_spreadsheet_refresh_token'),
            'token_uri': params.get_param('google_spreadsheet_token_uri'),
            'client_id': params.get_param('google_spreadsheet_client_id'),
            'client_secret': params.get_param('google_spreadsheet_client_secret'),
            'scopes': [params.get_param('google_spreadsheet_scopes')],
            'expiry':params.get_param('google_spreadsheet_expiry')}
    def get_sheet_credentials(self):
        params = self.env['ir.config_parameter'].sudo()
        if not params.get_param('google_spreadsheet_client_id'):
            return False
        cred_token=  self.get_cred_token()
        
        creds = Credentials.from_authorized_user_info(cred_token, None)
        #If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                credential_json=self.buil_json_from_file()
                flow = InstalledAppFlow.from_client_config(
                    credential_json, [credential_json['web']['redirect_uris'][0]])
                creds = flow.run_local_server(port=0)
            self.save_credentials(creds)
        return creds   
    @api.model 
    def create(self,vals):
        return super().create(vals)
        