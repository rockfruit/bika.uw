from bika.lims import bikaMessageFactory as _
from bika.lims.browser.client import ClientBatchesView as BaseView


class ClientBatchesView(BaseView):
    """Override the default listing of batches.

    - Display additional review state filter buttons.
    - Additional columns available for display.
    """


    def __init__(self, context, request):
        super(ClientBatchesViewClientBatchesView, self).__init__(context, request)
        from zope.i18nmessageid import MessageFactory
        _b = MessageFactory('bika')
        self.title = _b("Batches")
        self.review_states = [
            {'id': 'default',
             'title': _('Active'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'cancellation_state':'active',
                               'sort_on': 'created',
                               'sort_order': 'reverse'}},
            {'id': 'requested',
             'title': _('Requested'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'review_state': 'requested',
                               'cancellation_review_state': 'active',
                               'sort_on': 'created',
                               'sort_order': 'reverse'}},
            {'id': 'approved',
             'title': _('Approved'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'review_state': 'approved',
                               'cancellation_review_state': 'active',
                               'sort_on': 'created',
                               'sort_order': 'reverse'}},
            {'id': 'received',
             'title': _('Recieved'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'review_state': 'received',
                               'cancellation_review_state': 'active',
                               'sort_on': 'created',
                               'sort_order': 'reverse'}},
            {'id': 'accepted',
             'title': _('Accepted'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'review_state': 'accepted',
                               'cancellation_review_state': 'active',
                               'sort_on': 'created',
                               'sort_order': 'reverse'}},
            {'id': 'released',
             'title': _('Released'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'review_state': 'released',
                               'cancellation_review_state': 'active',
                               'sort_on': 'created',
                               'sort_order': 'reverse'}},
            {'id': 'prepared',
             'title': _('Prepared'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'review_state': 'prepared',
                               'cancellation_review_state': 'active',
                               'sort_on': 'created',
                               'sort_order': 'reverse'}},
            {'id': 'tested',
             'title': _('Tested'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'review_state': 'tested',
                               'cancellation_review_state': 'active',
                               'sort_on': 'created',
                               'sort_order': 'reverse'}},
            {'id': 'passed_qa',
             'title': _('Passed QA'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'review_state': 'passed_qa',
                               'cancellation_review_state': 'active',
                               'sort_on': 'created',
                               'sort_order': 'reverse'}},
            {'id': 'published',
             'title': _('Published'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'review_state': 'published',
                               'cancellation_review_state': 'active',
                               'sort_on': 'created',
                               'sort_order': 'reverse'}},
            {'id': 'cancelled',
             'title': _('Cancelled'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'cancellation_state': 'cancelled',
                               'sort_on': 'created',
                               'sort_order': 'reverse'}},
            {'id': 'all',
             'title': _('All'),
             'columns': ['Title',
                         'BatchID',
                         'BatchDate',
                         'Client',
                         'Description',
                         'state_title'],
             'contentFilter': {'sort_on': 'created',
                               'sort_order': 'reverse'}},
        ]
