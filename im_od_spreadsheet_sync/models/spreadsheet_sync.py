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
from odoo import models, fields, api, _
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from odoo.exceptions import RedirectWarning, UserError
from datetime import timedelta
from odoo.tools.safe_eval import safe_eval, test_python_expr
import string
import json
import logging
from ast import literal_eval
_logger = logging.getLogger(__name__)
# FIELD_TYPES = [(key, key) for key in sorted(fields.Field.by_type)]


class SheetFilter(models.Model):
    _name = 'spreadsheet.filter'
    _description = 'Spreadhseet Filter'
    field_id = fields.Many2one('ir.model.fields', 'Model Field', required=True, ondelete='cascade')
    filter_operation = fields.Selection([('=', '='),
                                       ('ilike', 'ilike'),
                                       ('>', '>'),
                                       ('<', '>'),
                                       ('>=', '>='),
                                       ('<=', '<='),
                                       ('!=', '!=')], 'Operator')
    value = fields.Char('Value')
    filter_string = fields.Char('Filter String', compute="_compute_filter_string")
    value_type = fields.Selection([('value', 'Value'), ('field', 'Field')], default='value', required=True, string='Value Type')
    value_field_id = fields.Many2one('ir.model.fields', 'Value Field', ondelete='cascade')
    
    @api.onchange('value_type')
    def onchange_value_type(self):
        if self.value_type=='value':
            self.value_field_id=None
        elif self.value_type=='field':
            self.value=''
        else:
            self.value_field_id=None 
            self.value=''

#===============================================================================
# class SheetQueryBuilder(models.Model):
#     _name='sheet.query.builder'
#     _description='Sheet query Builder'
#     model_id =fields.Many2one('res.model','Model', required=True, ondelete='cascade')
#     relation_field_id=fields.Many2one('res.model.fields','Relation Field', ondelete='cascade')
#     related_model_id=fields.Many2one('res.model','Releted Model', ondelete='cascade')
#     related_field_id=fields.Many2one('res.model.fields','Related Field',ondelete='cascade')
#     relation_type=fields.Selection([('base','Base'),('join','Join')],required=True)    
#===============================================================================
class SpreadSheetFields(models.Model):
    _name = 'spreadsheet.sync.fields'
    _description='Spreadsheet Sync Fields'
    _rec_name = 'field_id'
    # name=fields.Char(related="field_id.name")
    modelsync_id = fields.Many2one('ir.model', 'Model Name', required=True, index=True, ondelete='cascade')
    sequence = fields.Integer(default=1)
    field_id = fields.Many2one('ir.model.fields', 'Model Field', required=True, ondelete='cascade')
    displayfield_id = fields.Many2one('ir.model.fields', 'Display Field', required=True, ondelete='cascade')
    is_childfield = fields.Boolean(compute="_compute_is_childfield")
    displayfield_id_domain = fields.Char(compute='_compute_displayfield_domain', readonly=True, store=False)
    filter_visibility = fields.Selection([('sheet', 'Sheet Column'), ('filter', 'Filter Only')], 'Column Visibility', default='sheet', required=True)

    @api.depends('field_id')
    def _compute_displayfield_domain(self):
        for rec in self:
            if rec.is_childfield:
                comodel_id = self.env['ir.model'].search([('model', '=', rec.field_id.relation)], limit=1)
                rec.displayfield_id_domain = json.dumps([('model_id', '=', comodel_id.id)])
            else:
                rec.displayfield_id_domain = json.dumps([('id', '=', rec.field_id.id)])
                rec.displayfield_id = rec.field_id

    @api.depends('field_id', 'displayfield_id')
    def _compute_is_childfield(self):
        for rec in self:
            if rec.field_id.ttype in ['many2many', 'many2one', 'many2one_reference', 'one2many']:
                rec.is_childfield = True
            else:
                rec.is_childfield = False

        
class SpreadSheetSync(models.Model):
    _name = 'imanis.spreadsheet.sync'
    _description = 'Synced Spreadsheet'
    spreadsheet_id = fields.Char('Google Spreadsheet ID')
    name = fields.Char('Spreadsheet Name')
    sheet_id = fields.Char('Sheet ID')
    sheet_name = fields.Char('Sheet Name', required=True)
    modelsync_id = fields.Many2one('ir.model', 'Model Name', ondelete='cascade')
    model_fields_ids = fields.One2many('spreadsheet.sync.fields', 'sheet_id' , string='Fields')
    spreadsheet_link = fields.Char('Open Sheet', compute="_compute_open_sheet")
    filter_type = fields.Selection([('&', 'AND'), ('|', 'OR')], 'Filter type', default='&')
    filter_string = fields.Char('Filter String', compute="_compute_filter_string")
    filter_ids = fields.One2many('spreadsheet.filter', 'sheet_id', 'Filter')
    pure_sql = fields.Boolean('Pure SQL')
    search_query = fields.Text('Search Query* ONLY SELECT')
    is_valid_sql = fields.Boolean('Query is valid')
    html_result = fields.Html('Result')
    code = fields.Text(string='Python Code', help="Write Python code for your query ")
    # query_builder_ids=fields.One2many('sheet.query.builder','sheet_id','Query Builder')
    def execute_query(self):
        if self.pure_sql and self.search_query:
            if not self.search_query.lower().startswith('select'):
                return (False, False)
            headers = []
            datas = []

            try:
                self.sudo().env.cr.execute(self.search_query)
            except Exception as e:
                raise UserError(e)

            try:
                no_fetching = ['update', 'delete', 'create', 'insert', 'alter', 'drop']
                max_n = len(max(no_fetching))

                is_insides = [(o in self.name.lower().strip()[:max_n]) for o in no_fetching]
                if True not in is_insides:
                    headers = [d[0] for d in self.env.cr.description]
                    datas = self.env.cr.fetchall()
            except Exception as e:
                raise UserError(e)
            
            return (headers, datas)
    def build_html(self,headers,datas):
        if headers and datas:
                
                header_html = "".join(["<th style='border: 1px solid'>" + str(header) + "</th>" for header in headers])
                header_html = "<tr>" + "<th style='background-color:white !important'/>" + header_html + "</tr>"

                body_html = ""
                i = 0
                for data in datas:
                    i += 1
                    body_line = "<tr>" + "<td style='border-right: 3px double; border-bottom: 1px solid; background-color: grey;color:white'>{0}</td>".format(i)
                    for value in data:
                        body_line += "<td style='border: 1px solid; background-color: {0};color:{2};'>{1}</td>".format('gray' if i % 2 == 0 else 'white', str(value) if (value is not None) else '', 'white' if i % 2 == 0 else 'grey')

                    body_line += "</tr>"
                    body_html += body_line

                self.html_result = """
<table style="text-align: center">
  <thead style="background-color: lightgrey">
    {0}
  </thead>

  <tbody>
    {1}
  </tbody>
</table>
""".format(header_html, body_html)

    def test_live_query(self):
        values,sheet_name=self.get_values()
        headers =values[0]
        datas=[]
        i=0
        for value in values:
            if i >0:
                datas.append(value)
            i+=1
        self.build_html(headers,datas)

    def test_query(self):
        if self.pure_sql and self.search_query:
            if not self.search_query.lower().startswith('select'):
                raise UserError(_('ONLY SELECT QUERY ALLOWED'))
            headers, datas = self.execute_query()
            self.build_html(headers, datas)
            
    @api.depends('filter_ids.filter_string', 'filter_type')
    def _compute_filter_string(self):
        for rec in self:
            filter_operators = ''
            if len(rec.filter_ids) > 1:
                flen = 1
                while flen < len(rec.filter_ids):
                    filter_operators += "'" + rec.filter_type + "'" + ","
                    flen += 1
            filters = ""
            filter_len = 0
            for filter_id in rec.filter_ids:
                filter_len += 1
                filters += filter_id.filter_string
                if filter_len < len(rec.filter_ids):
                    filters += ","
            if rec.filter_ids: 
                rec.filter_string = f'[{filter_operators}{filters}]'
            else:
                rec.filter_string = ''

    def compute_filter_array_string(self):
        filter_operators = ''
        if len(self.filter_ids) > 1:
            flen = 1
            while flen < len(self.filter_ids):
                filter_operators += self.filter_type + ";"
                flen += 1
        filters = ""
        filter_len = 0
        for filter_id in self.filter_ids:
            filter_len += 1
            filters += filter_id.filter_string
            if filter_len < len(self.filter_ids):
                filters += ";"
        if self.filter_ids: 
            return  f'[{filter_operators}{filters}]'
        else:
            return ''            

    @api.depends('spreadsheet_id')
    def _compute_open_sheet(self):
        for rec in self:
            if rec.spreadsheet_id:
                rec.spreadsheet_link = f'https://docs.google.com/spreadsheets/d/{rec.spreadsheet_id}'
            else:
                rec.spreadsheet_link = ''
                
    @api.onchange('modelsync_id')
    def onchange_modelsync_id(self):
        if self.modelsync_id:
            name = f'{self.modelsync_id.name}_{self.env.company.name}'
            self.name = name.replace(' ', '_')

    def get_access_token(self):
        Config = self.env['sheet.api.credentials'].sudo().search([('live', '=', True)], limit=1)
        return Config.get_sheet_credentials()
        
    def createSpreadsheet(self):
        access_token = self.get_access_token()
        try:
            if access_token:
                service = build('sheets', 'v4', credentials=access_token)
                spreadsheet = {
                            'properties': {
                                'title': self.name
                                },
                             'sheets': [
                                    {
                                      'properties': {
                                        'title': f'{self.sheet_name}'
                                      }
                                    }
                                ]
                             }
                spreadsheet = service.spreadsheets().create(body=spreadsheet,
                                                            fields='spreadsheetId').execute()
            else:
                return None
        except HttpError as err:
            raise UserError(err)

        # return (spreadsheet.get('spreadsheetId'), spreadsheet.get('sheets.sheetId'))
        return (spreadsheet.get('spreadsheetId'))

    def get_values(self):
        if self.pure_sql and self.search_query:
            if not self.search_query.startwith('SELECT'):
                return (False, False)
            headers, datas = self.execute_query()
            if headers and datas:
                values = []
                values.append(headers)
                column_size = len(headers)
                record_size = len(datas)
                alphabet_string = string.ascii_uppercase
                alphabet_list = list(alphabet_string)
                sheet_range = f'{self.sheet_name}!A1:{alphabet_list[column_size]}{record_size+2}'
                for data in datas:
                    data_row = []
                    for value in data:
                        data_row.append(value)
                    values.append(data_row)
                return (values, sheet_range)
            return (False, False)
            
        model_object = self.env[self.modelsync_id.model].sudo()
        filter_string = self.filter_string
        if filter_string:
            computed_filter_string = filter_string#.replace('[', '').replace(']', '')
            domain = list(eval(computed_filter_string))
            
            model_data = model_object.search(domain)
        else:
            model_data = model_object.search([])
        record_size = len(model_data)
        column_data = self.model_fields_ids.filtered(lambda x:x.filter_visibility == 'sheet')
        column_size = len(column_data)
        
        alphabet_string = string.ascii_uppercase
        alphabet_list = list(alphabet_string)
        sheet_range = f'{self.sheet_name}!A1:{alphabet_list[column_size]}{record_size+2}'
        values = []
        header = []
        for col in column_data:
            header.append(col.displayfield_id.field_description)
        values.append(header)
        for data in model_data:
            row = []
            for column in column_data:
                if column.is_childfield:
                    val=getattr(getattr(data, column.field_id.name), column.displayfield_id.name)
                    #if hasattr(val,'display_name'):
                    #    row.append(getattr(val,'display_name'))
                    #else:
                    #    row.append(getattr(val))
                    row.append(val)
                else:
                    row.append(getattr(data, column.field_id.name))
            values.append(row)
        return (values, sheet_range)
    
    @api.model 
    def sync_Allspreadsheet(self):
        objs = self.search([])
        for obj in objs:
            obj.sync_spreadsheet()
            
    def sync_spreadsheet(self):
        access_token = self.get_access_token()
        try:
            if access_token:
                if not self.spreadsheet_id:
                    # self.spreadsheet_id, self.sheet_id = self.createSpreadsheet()
                    self.spreadsheet_id = self.createSpreadsheet()
                if self.spreadsheet_id:
                    service = build('sheets', 'v4', credentials=access_token)
                    values, sheet_range = self.get_values()
                    # Call the Sheets API
                    if values and sheet_range:
                        result = service.spreadsheets().values().update(
                                            spreadsheetId=self.spreadsheet_id, range=sheet_range,
                                            valueInputOption='USER_ENTERED', body={'values':values}).execute()
        
        except HttpError as err:
            print(err)

        return

    @api.model 
    def create(self, vals):
        # vals['spreadsheet_id'], vals['sheet_id'] = self.createSpreadsheet()
        result = super().create(vals)
        result.spreadsheet_id = result.createSpreadsheet()
        return result

    
class SpreadSheetFieldsInh(models.Model):
    _inherit = 'spreadsheet.sync.fields'
    sheet_id = fields.Many2one('imanis.spreadsheet.sync', 'Spreadsheet')


class SheetFilterInh(models.Model):
    _inherit = 'spreadsheet.filter'
    sheet_id = fields.Many2one('imanis.spreadsheet.sync', 'Spreadsheet')
    displayfield_id_domain = fields.Char(compute='_compute_displayfield_domain', readonly=True, store=False)
    valuefield_id_domain=fields.Char(compute='compute_valuefield_id_domain')
    
    @api.depends('value_type')
    def compute_valuefield_id_domain(self):
        for rec in self:
            mapped_ids = rec.sheet_id.model_fields_ids.mapped('field_id')
            mapped_relations=mapped_ids.mapped('relation')
            comodel_ids = self.env['ir.model'].search([('model', 'in', mapped_relations)])
            rec.valuefield_id_domain = json.dumps([('model_id', 'in', comodel_ids.ids)])
    @api.depends('field_id')
    def _compute_displayfield_domain(self):
        for rec in self:
            mapped_ids = rec.sheet_id.model_fields_ids.mapped('displayfield_id')
            rec.displayfield_id_domain = json.dumps([('id', 'in', mapped_ids.ids)])
    
    @api.depends('field_id', 'filter_operation', 'value')
    def _compute_filter_string(self):
        for rec in self:
            search_field = '('
            if rec.field_id in rec.sheet_id.model_fields_ids.mapped('field_id') or rec.field_id.model_id == rec.sheet_id.modelsync_id:
                search_field += f"'{rec.field_id.name}'"
            elif rec.field_id in rec.sheet_id.model_fields_ids.mapped('displayfield_id'):
                parent_field = rec.sheet_id.model_fields_ids.filtered(lambda x:x.displayfield_id == rec.field_id)[0]
                search_field += f"'{parent_field.field_id.name}.{rec.field_id.name}'"
            search_field += f",'{rec.filter_operation}',"
            if rec.value_type == 'value':
                value = rec.value
                search_field += f"{value}"
            elif rec.value_type == 'field':
                value = f'{rec.value_field_id.model_id.name}.{rec.value_field_id.name}'
                search_field += f"{value}"
            search_field += ')'
            rec.filter_string = search_field
#===============================================================================
# class SheetQueryBuilderInh(models.Model):
#     _inherit='sheet.query.builder'
#     sheet_id = fields.Many2one('imanis.spreadsheet.sync', 'Spreadsheet')
#===============================================================================
