from AccessControl import ClassSecurityInfo
from Products.CMFCore.permissions import View, \
    ModifyPortalContent
from Products.CMFDynamicViewFTI.browserdefault import \
    BrowserDefaultMixin
from Products.Archetypes.public import *
from bika.lims.content.bikaschema import BikaSchema
from bika.lims.config import PROJECTNAME

schema = BikaSchema.copy()

class ClientStatus(BrowserDefaultMixin, BaseContent):
    security = ClassSecurityInfo()
    archetype_name = 'ClientStatus'
    schema = schema
    allowed_content_types = ()
    immediate_view = 'tool_base_edit'
    content_icon = 'client.png'
    global_allow = 0
    filter_content_types = 0
    use_folder_tabs = 0

    actions = (
    
       {'id': 'edit',
        'name': 'Edit',
        'action': 'string:${object_url}/tool_base_edit',
        'permissions': (ModifyPortalContent,),
        },
    )

    factory_type_information = {
        'title': 'Client status'
    }


registerType(ClientStatus, PROJECTNAME)

def modify_fti(fti):
    for a in fti['actions']:
        if a['id'] in ('view', 'syndication', 'references', 'metadata',
                       'localroles'):
            a['visible'] = 0
    return fti