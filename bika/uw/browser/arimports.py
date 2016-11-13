# -*- coding: utf-8 -*-

import os
import csv
import json
import types
import pprint
from UserDict import UserDict

from DateTime import DateTime

from zope.event import notify
from zope.interface import implements

from plone.app.layout.globals.interfaces import IViewView
from plone.protect import CheckAuthenticator

from collective.progressbar.events import ProgressBar
from collective.progressbar.events import ProgressState
from collective.progressbar.events import UpdateProgressEvent
from collective.progressbar.events import InitialiseProgressBar

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.Archetypes.event import ObjectInitializedEvent
from Products.statusmessages.interfaces import IStatusMessage
from Products.CMFPlone.utils import transaction_note
from Products.CMFPlone.utils import _createObjectByType
from Products.CMFCore.utils import getToolByName

from bika.lims.utils import tmpID
from bika.lims.browser import BrowserView
from bika.lims import bikaMessageFactory as _

from bika.uw import logger


class ClientARImportAddView(BrowserView):
    implements(IViewView)
    template = ViewPageTemplateFile('templates/arimport_add_form.pt')

    def __init__(self, context, request):
        super(ClientARImportAddView, self).__init__(context, request)
        self.bika_setup = getToolByName(context, "bika_setup")
        self.portal_workflow = getToolByName(context, "portal_workflow")
        self.context = context
        self.request = request
        self.data = None

    def __call__(self):
        CheckAuthenticator(self.request.form)

        if self.form_get('submitted'):
            csvfile = self.form_get('csvfile')
            check_mode = self.form_get('check')

            if check_mode == "1":
                data = self.check_import_data()
                valid = data["valid"]
                errors = "\n".join(data["errors"])
                if valid:
                    self.statusmessage("Import Data Valid", "info")
                else:
                    self.statusmessage(errors, "error")
                self.data = pprint.pformat(data)
                return self.template()

            data = self._import_file(csvfile)
            if data["success"]:
                self.statusmessage(_("Import Successful"), "info")
                url = self.urljoin(self.context.absolute_url(), "samples")
            else:
                errors = "\n".join(data["errors"])
                self.statusmessage(_(errors), "error")
                url = self.urljoin(self.context.absolute_url(), "arimport_add")
            return self.redirect(url)

        return self.template()

    def urljoin(self, *args):
        """simple urljoin
        """
        return "/".join(args)

    def check_import_data(self):
        """Return the parsed data as JSON
        """
        csvfile = self.form_get('csvfile')
        if not csvfile:
            return None
        data = self._prepare_import_data(csvfile)
        return data

    def redirect(self, url):
        """Write a redirect JavaScript to the given URL
        """
        return self.request.response.write("<script>document.location.href='{0}'</script>".format(url))

    def _prepare_import_data(self, csvfile):
        """Prepare data for import

            - Checks data integrity
            - Extracts the known fields from the Spreadsheet
            - Maps Spreadsheet fields to Schema names
            - Fetch objects if they exist
        """
        _data = {
            "valid": True,
            "errors": [],
        }

        # parse the CSV data into the interanl data structure
        import_data = ImportData(csvfile)
        _data["import_data"] = import_data

        # remember the csvfile
        _data["csvfile"] = csvfile

        # Validate the import data
        valid = import_data.validate()
        if type(valid) in types.StringTypes:
            _data["valid"] = False
            _data["errors"].append(valid)

        # Client Handling
        client_id = self.form_get("ClientID")
        client = self.get_client_by_id(client_id)
        if client is None:
            _data["valid"] = False
            msg = "Could not find Client {0}".format(client_id)
            _data["errors"].append(msg)

        # Store the client data to the output data
        _data["client"] = {
            "id": client_id,
            "title": client and client.Title() or "Client not Found",
            "obj": client,
        }

        # Parse the known fields from the Spreadsheet
        #
        # Note: The variable names refer to the spreadsheet cells, e.g.:
        #       _2B is the cell at column B row 2.
        #
        # File name, Client name, Client ID, Contact, Client Order Number, Client Reference
        _2B, _2C, _2D, _2E, _2F, _2G = import_data.get_data("header")[:6]
        # title, BatchID, description, ClientBatchID, ReturnSampleToClient
        _4B, _4C, _4D, _4E, _4F = import_data.get_data("batch_header")[:5]
        # Client Comment, Lab Comment
        _6B, _6C = import_data.get_data("batch_meta")[:2]
        # DateSampled, Media, SamplePoint, Activity Sampled
        _10B, _10C, _10D, _10E = import_data.get_data("samples_meta")[:4]

        # Check for valid sample Type
        sample_type = self.get_sample_type_by_name(_10C)
        if sample_type is None:
            _data["valid"] = False
            msg = "Could not find Sample Type {0} - Aborting.".format(_10C)
            _data["errors"].append(msg)

        # Store the sample type to the output data
        _data["sample_type"] = {
            "title": _10C,
            "obj": sample_type
        }

        #
        # Batch Handling
        #
        batch_title = _4B
        batch_obj = None
        if batch_title:
            existing_batch = [x for x in client.objectValues('Batch')
                              if x.title == batch_title]
            if existing_batch:
                batch_obj = existing_batch[0]

        batch_fields = dict(
            # <Field id(string:rw)>,
            # <Field BatchID(string:rw)>,
            BatchID=_4C,
            # <Field title(string:rw)>,
            title=_4B,
            # <Field Client(reference:rw)>,
            Client=client,
            # <Field description(text:rw)>,
            description=_4D,
            # <Field DateSampled(datetime_ng:rw)>,
            DateSampled=DateTime(_10B),
            # <Field BatchDate(datetime:rw)>,
            # <Field BatchLabels(lines:rw)>,
            # <Field ClientProjectName(string:rw)>,
            # <Field ClientBatchID(string:rw)>,
            ClientBatchID=_4E,
            # <Field Contact(reference:rw)>,
            Contact=self.get_contact_by_name(client, _2E),
            # <Field CCContact(reference:rw)>,
            # <Field CCEmails(lines:rw)>,
            # <Field InvoiceContact(reference:rw)>,
            # <Field ClientBatchComment(text:rw)>,
            ClientBatchComment=_6B,
            # <Field ClientPONumber(string:rw)>,
            ClientPONumber=_2F,
            # <Field ReturnSampleToClient(boolean:rw)>,
            ReturnSampleToClient=_4F,
            # <Field SampleSite(string:rw)>,
            # <Field SampleSource(string:rw)>,
            # <Field SampleType(reference:rw)>,
            # <Field SampleMatrix(reference:rw)>,
            # <Field Remarks(text:rw)>,
            # <Field InheritedObjects(reference:rw)>,
            # <Field InheritedObjectsUI(InheritedObjects:rw)>,
            # <Field constrainTypesMode(integer:rw)>,
            # <Field locallyAllowedTypes(lines:rw)>,
            # <Field immediatelyAddableTypes(lines:rw)>,
            # <Field allowDiscussion(boolean:rw)>,
            # <Field excludeFromNav(boolean:rw)>,
            # <Field nextPreviousEnabled(boolean:rw)>,
            # <Field subject(lines:rw)>,
            # <Field relatedItems(reference:rw)>,
            # <Field location(string:rw)>,
            # <Field language(string:rw)>,
            # <Field effectiveDate(datetime:rw)>,
            # <Field expirationDate(datetime:rw)>,
            # <Field creation_date(datetime:rw)>,
            # <Field modification_date(datetime:rw)>,
            # <Field creators(lines:rw)>,
            # <Field contributors(lines:rw)>,
            # <Field rights(text:rw)>,
            # <Field Analysts(lines:rw)>,
            # <Field LeadAnalyst(string:rw)>,
            # <Field Methods(reference:rw)>,
            # <Field Profile(reference:rw)>,
            # <Field NonStandardMethodInstructions(text:rw)>,
            # <Field ApprovedExceptionsToStandardPractice(text:rw)>,
            # <Field StorageLocation(reference:rw)>,
            # <Field SampleTemperature(string:rw)>,
            # <Field SampleCondition(reference:rw)>,
            # <Field Container(reference:rw)>,
            # <Field ActivitySampled(string:rw)>,
            # <Field MediaLotNr(string:rw)>,
            # <Field QCBlanksProvided(boolean:rw)>,
            # <Field MSDSorSDS(boolean:rw)>,
            # <Field SampleAndQCLotMatch(boolean:rw)>,
            # <Field ClientSampleComment(text:rw)>,
            ClientSampleComment=_6B,
            # <Field BioHazardous(boolean:rw)>,
            # <Field ExceptionalHazards(text:rw)>,
            # <Field AmountSampled(string:rw)>,
            # <Field AmountSampledMetric(string:rw)>,
            # <Field DateQADue(datetime_ng:rw)>,
            # <Field DatePublicationDue(datetime_ng:rw)>,
            # <Field DateApproved(string:rw)>,
            # <Field DateReceived(string:rw)>,
            # <Field DateAccepted(string:rw)>,
            # <Field DateReleased(string:rw)>,
            # <Field DatePrepared(string:rw)>,
            # <Field DateTested(string:rw)>,
            # <Field DatePassedQA(string:rw)>,
            # <Field DatePublished(string:rw)>,
            # <Field DateCancelled(string:rw)>,
            # <Field DateOfRetractions(lines:rw)>
        )

        # Save the Batch for the output data
        _data["batch"] = {
            "title": batch_title,
            "obj": batch_obj,
            "batch_fields": batch_fields,
        }

        # List of profile/service identifiers to search for
        _analytes = import_data.get_analytes_data()

        profiles = filter(lambda x: x is not None,
                          map(self.get_profile_by_value, _analytes))
        services = filter(lambda x: x is not None,
                          map(self.get_service_by_value, _analytes))

        # Create a list of the AnalysisServices from the profiles and services
        _analyses = set()
        for profile in profiles:
            for service in profile.getService():
                _analyses.add(service)
        for service in services:
            _analyses.add(service)
        analyses = list(_analyses)

        # Store the profiles to the output data
        _data["profiles"] = []
        for profile in profiles:
            _data["profiles"].append({
                "title": profile.Title(),
                "obj": profile
            })

        # Store the services to the output data
        _data["services"] = []
        for service in services:
            _data["services"].append({
                "title": service.Title(),
                "obj": service
            })

        # Store the Analysis to the output data
        _data["analyses"] = []
        for analysis in analyses:
            _data["analyses"].append({
                "title": analysis.Title(),
                "obj": analysis
            })

        #
        # AR Handling
        #
        _data["analysisrequests"] = []
        samples = import_data.get_sample_data()
        for n, item in enumerate(samples):

            # ClientSampleID, Amount Sampled, Metric, Remarks
            _xB, _xC, _xD, _xE = item[:4]

            sample_fields = dict(
                #  <Field id(string:rw)>,
                #  <Field description(text:rw)>,
                #  <Field SampleID(string:rw)>,
                #  <Field ClientReference(string:rw)>,
                #  <Field ClientSampleID(string:rw)>,
                ClientSampleID=_xB,
                #  <Field LinkedSample(reference:rw)>,
                #  <Field SampleType(reference:rw)>,
                SampleType=self.get_sample_type_by_name(_10C),
                #  <Field SampleTypeTitle(computed:r)>,
                #  <Field SamplePoint(reference:rw)>,
                SamplePoint=self.get_sample_point_by_name(_10D),
                #  <Field SamplePointTitle(computed:r)>,
                #  <Field SampleMatrix(reference:rw)>,
                #  <Field StorageLocation(reference:rw)>,
                #  <Field SamplingWorkflowEnabled(boolean:rw)>,
                #  <Field DateSampled(datetime:rw)>,
                DateSampled=DateTime(_10B),
                #  <Field Sampler(string:rw)>,
                #  <Field SamplingDate(datetime:rw)>,
                #  <Field PreparationWorkflow(string:rw)>,
                #  <Field SamplingDeviation(reference:rw)>,
                #  <Field SampleCondition(reference:rw)>,
                #  <Field DateReceived(datetime:rw)>,
                #  <Field ClientUID(computed:r)>,
                #  <Field SampleTypeUID(computed:r)>,
                #  <Field SamplePointUID(computed:r)>,
                #  <Field Composite(boolean:rw)>,
                #  <Field DateExpired(datetime:rw)>,
                #  <Field DisposalDate(computed:r)>,
                #  <Field DateDisposed(datetime:rw)>,
                #  <Field AdHoc(boolean:rw)>,
                #  <Field Remarks(text:rw)>,
                Remarks=_xE,
                #  <Field ClientSampleComment(text:rw)>,
                #  <Field AmountSampled(string:rw)>,
                AmountSampled=_xC,
                #  <Field AmountSampledMetric(string:rw)>,
                AmountSampledMetric=_xD,
                #  <Field ExceptionalHazards(text:rw)>,
                #  <Field SampleSite(string:rw)>,
                #  <Field allowDiscussion(boolean:rw)>,
                #  <Field subject(lines:rw)>,
                #  <Field location(string:rw)>,
                #  <Field contributors(lines:rw)>,
                #  <Field creators(lines:rw)>,
                #  <Field effectiveDate(datetime:rw)>,
                #  <Field expirationDate(datetime:rw)>,
                #  <Field language(string:rw)>,
                #  <Field rights(text:rw)>,
                #  <Field creation_date(datetime:rw)>,
                #  <Field modification_date(datetime:rw)>,
                #  <Field ReturnSampleToClient(boolean:rw)>,
                #  <Field Hazardous(boolean:rw)>,
                #  <Field SampleTemperature(string:rw)>
            )

            _item = {}
            _item["analyses"] = map(lambda an: an.UID(), analyses)
            _item["sample_fields"] = sample_fields

            sample = self.get_sample_by_sid(client, _xB)
            ar = self.get_ar_by_sample(client, sample)

            _item["analysisrequest_obj"] = ar
            _item["sample_obj"] = sample

            _data["analysisrequests"].append(_item)

        return _data

    def _import_file(self, csvfile):
        """Import the CSV file.
        """
        # get the import data
        import_data = self._prepare_import_data(csvfile)

        # Import success: switch on errors
        import_data["success"] = True

        if import_data["valid"] is False:
            import_data["success"] = False
            return import_data

        #
        # Data seems valid - importing
        #

        # Initialize the Progress Bar
        self.progressbar_init("Importing File")

        # get the client object
        client = import_data["client"]["obj"]

        # get the batch object
        batch = import_data["batch"]["obj"]
        batch_fields = import_data["batch"]["batch_fields"]
        if batch is None:
            # create a new batch
            batch = self.create_object("Batch", client, **batch_fields)
        batch.edit(**batch_fields)

        # Create ARs, Samples, Analyses and Sample Partitions
        ar_items = import_data["analysisrequests"]
        for n, item in enumerate(ar_items):
            sample = item["sample_obj"]
            sample_fields = item["sample_fields"]
            if sample is None:
                # create a new sample
                sample = self.create_object("Sample", client, **sample_fields)
            sample.edit(**sample_fields)
            self.sample_wf(sample)

            # Create a SamplePartition
            part = sample.contentValues()
            if not part:
                part = self.create_object('SamplePartition', sample, 'part-1')
            else:
                part = part[0]
            self.sample_wf(part)

            # Create an AnalysisRequest
            ar = item["analysisrequest_obj"]
            if not ar:
                # create a new AR
                ar = self.create_object('AnalysisRequest', client, Sample=sample.UID(), **sample_fields)
            # set the Sample
            ar.setSample(sample)
            # set the batch
            ar.setBatch(batch)
            # Set the list of AnalysisServices
            analyses = item["analyses"]
            ar.setAnalyses(analyses)
            for analysis in ar.getAnalyses(full_objects=True):
                analysis.setSamplePartition(part)
            # Update the data
            ar.edit(**sample_fields)
            # set the workflow
            self.sample_wf(ar)

            # progress
            self.progressbar_progress(n, len(ar_items))

        return import_data

    def get_profile_by_value(self, value):
        """Serarch a Profile by the given value and return the object of the
        first found result or None if no results were found.

        Search Precedence:
            1. Search by Title
        """
        # Profiles can be searched by the bika_setup_catalog
        bsc = self.bika_setup_catalog

        # Precedence of search queries
        queries = [
            {"title": value},
        ]
        # Return the UID of the first found result.
        for query in queries:
            q = {"portal_type": "AnalysisProfile"}
            q.update(query)
            results = bsc(q)
            if len(results) == 0:
                continue
            return results[0].getObject()
        return None

    def get_service_by_value(self, value):
        """Search a service by the given Value and return the object of the
        first found result or None if no results were found.

        Search Precedence:
            1. Search by CAS#
            2. Search by Title
            3. Search by Keyword
        """
        # Profiles can be searched by the bika_setup_catalog
        bsc = self.bika_setup_catalog

        # Precedence of search queries
        queries = [
            {"title": value},
            {"getKeyword": value},
        ]
        # Return the UID of the first found result.
        for query in queries:
            q = {"portal_type": "AnalysisService"}
            q.update(query)
            results = bsc(q)
            if len(results) == 0:
                continue
            return results[0].getObject()
        return None

    def get_ar_by_sample(self, client, sample):
        """Get the AR object by sample
        """
        ar = [x for x in client.objectValues('AnalysisRequest')
              if x.getSampleUID() == sample.UID()]
        if ar:
            return ar[0]
        return None

    def sample_wf(self, sample):
        if self.portal_workflow.getTransitionsFor(sample):
            return
        swe = self.bika_setup.getSamplingWorkflowEnabled()
        if swe:
            self.portal_workflow.doActionFor(sample, 'sampling_workflow')
        else:
            self.portal_workflow.doActionFor(sample, 'no_sampling_workflow')

    def get_sample_by_sid(self, client, sid):
        """Get the sample object by name
        """
        sample = [x for x in client.objectValues('Sample')
                  if x.getClientSampleID() == sid]
        if sample:
            return sample[0]
        return None

    def get_contact_by_name(self, client, name):
        """Get the contact object by name
        """
        contact = [x for x in client.objectValues('Contact')
                   if x.getFullname() == name]
        if contact:
            return contact[0]

        return None

    def get_sample_type_by_name(self, name):
        """Get the sample type object by name
        """
        results = self.bika_setup_catalog(
            dict(portal_type="SampleType", title=name))
        if results:
            return results[0].getObject()
        return None

    def get_sample_point_by_name(self, name):
        """Get the sample type object by name
        """
        results = self.bika_setup_catalog(
            dict(portal_type="SamplePoint", title=name))
        if results:
            return results[0].getObject()
        return None

    def create_object(self, content_type, container, id=None, **kwargs):
        """Create a new ARImportItem object by type
        """
        if id is None:
            id = tmpID()
        logger.info("Creating Content {0} in Container {1} with ID {2}".format(
            content_type, container, id))
        obj = _createObjectByType(content_type, container, id)
        obj.unmarkCreationFlag()
        obj.edit(**kwargs)
        obj._renameAfterCreation()
        obj.processForm()
        notify(ObjectInitializedEvent(obj))
        obj.at_post_create_script()
        return obj

    def progressbar_init(self, title):
        """Progress Bar
        """
        bar = ProgressBar(self.context, self.request, title, description='')
        notify(InitialiseProgressBar(bar))

    def progressbar_progress(self, n, total):
        """Progres Bar Progress
        """
        progress_index = float(n) / float(total) * 100.0
        progress = ProgressState(self.request, progress_index)
        notify(UpdateProgressEvent(progress))

    def get_client_by_id(self, id):
        """Search the Client by the given ID
        """
        results = self.portal_catalog(portal_type='Client', id=id)
        if results:
            return results[0].getObject()
        return None

    def statusmessage(self, msg, facility="info"):
        """Add a statusmessage to the response
        """
        return IStatusMessage(self.request).addStatusMessage(msg, facility)

    def form_get(self, key):
        """Get the value from the form
        """
        form = self.request.form
        value = form.get(key)
        logger.debug("key={0} -> value={1}".format(key, value))
        return value


class ImportData(UserDict):
    """Dictionary wrapper to hold the spreadsheet data.
    """

    # Internal data representation of the spreadsheet table.
    # Description:
    # The keys (sections) must match the values of the first column (lowered
    # and underdashified). Value of the same row get stored in fields key.
    # Following lines matching no section get appended to the data key.
    _data = {
        "header": {
            "fields": [],
            "data": [],
        },
        "batch_header": {
            "fields": [],
            "data": [],
        },
        "batch_meta": {
            "fields": [],
            "data": [],
        },
        "analytes": {
            "fields": [],
            "data": [],
        },
        "samples_meta": {
            "fields": [],
            "data": [],
        },
        "samples": {
            "fields": [],
            "data": [],
        },
    }

    def __init__(self, csvfile, delimiter=";", quotechar="'"):
        logger.info("ImportData::__init__")
        self.csvfile = csvfile
        self.csvfile.seek(0)
        self.reader = csv.reader(csvfile, delimiter=delimiter, quotechar="'")
        self.data = self.clone_data()
        self.parse()

    def clone_data(self):
        """Make a deepcopy of the data structure
        """
        import copy
        return copy.deepcopy(self._data)

    def parse(self):
        """Parse the CSV to the internal data structure
        """
        logger.info("Parsing CSV.")

        section = None
        for n, row in enumerate(self.reader):
            # we use row[0] as an identifier per row to match the key in the
            # data dict, e.g. Batch Header -> batch_header
            identifier = row[0].replace(" ", "_").lower()

            # get the row data
            row_data = self.get_row_data(row)

            # skip empty cells
            if row_data is None:
                # logger.warn("Row {0} contains no data, skipping.".format(n))
                continue

            # check if the current identifier matches a key in the data dict
            if identifier in self.data:
                # a new section begins
                section = identifier
                # remember the fields
                self.data[identifier]["fields"] = row_data
                # go to the next row
                continue

            try:
                # append the row data to the "data" key of the current section
                self.data[section]["data"].append(row_data)
            except KeyError:
                logger.error("Found invalid identifier '{0}' in Line {1}".format(row[0], n + 1))
                # XXX: Mark the whole set as invalid or continue?
                continue
        return self.data

    def clear_data(self):
        """Clear the internal data structure
        """
        logger.info("************* CLEAR ***************")
        self.data = self.clone_data()

    def get_row_data(self, row, start=1, remove_trailing_empty=True):
        """extract the row values starting from 'start' and removes trailing
        empty values, e.g.: ['a', 'b', '', 'd', '', ''] -> ['b', '', 'd']
        """
        end = len(row)
        if remove_trailing_empty:
            # we iterate from the end of the list to the start to remove
            # empty cells
            rev = reversed(row)
            for n, i in enumerate(rev):
                if n + 1 == len(row):
                    return None
                if i != "":
                    return row[start:end - n]
        return row[start:end]

    def validate(self):
        """Validate the internal data structure
        """
        # Validate the sections
        for section in self.keys():
            logger.info("Processing Section {0}".format(section))

            fields = self.get_fields(section)
            data = self.get_data(section)

            if not fields:
                return "Invalid section {0}: No fields".format(section)
            if not data:
                return "Invalid section {0}: No data".format(section)

        # Validate the filename
        # XXX: Why do we need to do this?
        csv_filename = str(self.get_csv_filename())
        data_filename = str(self.get_data_filename())

        if csv_filename.lower() != data_filename.lower():
            return "Filename '{0}' does not match entered filename '{1}'".format(
                csv_filename, data_filename)

        return True

    def to_json(self):
        """Return the data as a JSON string
        """
        return json.dumps(self.data, indent=2, sort_keys=True, ensure_ascii=False)

    def get_csv_filename(self):
        """Return the filename of the CSV
        """
        filename = os.path.basename(self.csvfile.filename)
        return os.path.splitext(filename)[0]

    def get_data_filename(self):
        """Return the filename of the "Header" section
        """
        header = self.get_data("header")
        return header[0]

    def get_fields(self, section):
        """Fields accessor for the named section
        """
        return self.data[section]["fields"]

    def get_data(self, section):
        """Data accessor for the named section
        """
        data = self.data[section]["data"]
        if len(data) == 1:
            return data[0]
        return data

    def get_sample_data(self):
        """Return the data of the "Samples" section
        """
        return self.get_data("samples")

    def get_analytes_data(self):
        """Return the data of the "Analytes" section
        """
        return self.get_data("analytes")
