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

from odoo import http
from odoo.http import request

class GoogleSheetApi(http.Controller):

    @http.route('/sheet/authentication', type='http', auth="public")
    def oauth2callback(self, **kw):
        state =kw['state']
        cred_id= request.env['sheet.api.credentials'].sudo().search([('json_file','!=',False)],limit=1)
        if cred_id:
            try:
               
                result=cred_id.set_credentials(state=state,code=kw['code'],auth_url=request.httprequest.url)
                url = f'/web#id={cred_id.id}&view_type=list&model=sheet.api.credentials'
                #request.redirect(url)
                request.redirect('/web')
                #request.render('im_od_spreadsheet_sync.AuthSuccess') 
            except Exception as error:
                request.render('im_od_spreadsheet_sync.AuthFailed',{'error':error})
