import logging
import os
from datetime import datetime, timedelta
from json import dumps

from constance import config
from django_rq import job
from httplib2 import Http

from invoices import settings
from invoices.actions.imagesongoogle import ImageGoogleChatSending
from invoices.actions.messageongoogle import ReportChatSending

logger = logging.getLogger('console')


def post_webhook_pic_urls(description=None, event_pictures_url=None):
    url = settings.GOOGLE_CHAT_WEBHOOK_URL
    message = "\n"
    if description:
        message += description + "👇 "
    message += "%s" % event_pictures_url
    bot_message = {
        'text': message}
    message_headers = {'Content-Type': 'application/json; charset=UTF-8'}
    http_obj = Http()
    response = http_obj.request(
        uri=url,
        method='POST',
        headers=message_headers,
        body=dumps(bot_message),
    )
    print(response)

@job("default", timeout=6000)
def post_webhook_pic_as_image(description=None, event_pictures_url=None, email=None, google_chat_message_id=None,
                              report_picture_id=None):
    url = settings.GOOGLE_CHAT_WEBHOOK_URL
    message = "\n"
    if description:
        message += description + "👇 (from %s)" % report_picture_id
    # pass None for now
    if event_pictures_url and os.environ.get('LOCAL_ENV', None):
        if not google_chat_message_id:
            ImageGoogleChatSending(email=email).send_image(message, event_pictures_url,
                                                           report_picture_id=report_picture_id)
        else:
            ImageGoogleChatSending(email=email).update_image(message, event_pictures_url, google_chat_message_id)
    elif event_pictures_url and not os.environ.get('LOCAL_ENV', None):
        if not google_chat_message_id:
            ImageGoogleChatSending(email=email).send_image.delay(message, event_pictures_url,
                                                                 report_picture_id=report_picture_id)
        else:
            ImageGoogleChatSending(email=email).update_image.delay(message, event_pictures_url, google_chat_message_id)
def post_webhook(employees, patient, event_report, state, event_date=None, event_pictures_urls=None, event=None,
                 sub_contractor=None):
    """Hangouts Chat incoming webhook quickstart.
    @param event:
    @param event_pictures_urls:
    @param event_report:
    @param state:
    @param patient:
    @param employees:
    @param event_date:
    """
    # FIXME: remove hardcoded value for state
    if patient:
        _patient_name = patient.name.capitalize() + " " + patient.first_name[0].capitalize() + "."
    if state not in [3, 5, 6]:
        return
    string_event_date = ""
    # if event date in more than 2 days in the past, we do nothing
    if event_date:
        if event_date.date() < datetime.now().date() - timedelta(days=2):
            return
    if event_date:
        if event_date.date() < datetime.now().date():
            string_event_date = "du %s programmé à %s" % (event_date.date().strftime('%d-%h-%Y'),
                                                          event_date.time().strftime("%Hh%M"))
        else:
            string_event_date = "programmé à  %s" % event_date.time().strftime("%Hh%M")
    if 3 == state and patient:
        if employees and employees.google_user_id:
            made_by = "<users/%s>" % employees.google_user_id
        elif employees and employees.user:
            made_by = "*%s*" % employees.user.first_name
        elif sub_contractor:
            made_by = "*%s*" % sub_contractor.name
        message = '<%s%s|Passage> %s FAIT par %s chez *%s* : %s  ' % (config.ROOT_URL, event.get_admin_url(),
                                                                        string_event_date,
                                                                        made_by,
                                                                        _patient_name,
                                                                        event_report
                                                                        )
    elif 3 == state and patient is None:
        if employees and employees.google_user_id:
            made_by = "<users/%s>" % employees.google_user_id
        elif employees and employees.user:
            made_by = "*%s*" % employees.user.first_name
        elif sub_contractor:
            made_by = "*%s*" % sub_contractor.name
        message = '<%s%s|Passage> %s FAIT par %s : %s  ' % (config.ROOT_URL, event.get_admin_url(),
                                                                        string_event_date,
                                                                        made_by,
                                                                        event_report
                                                                        )

    # FIXME: remove hardcoded value for state
    elif state in [5, 6] and patient:
        # if date is in the future, message will contain the date
        if event_date.date() > datetime.now().date():
            string_event_date = "du %s programmé à %s" % (event_date.date().strftime('%d-%h-%Y'),
                                                          event_date.time().strftime("%Hh%M"))
        elif event_date.date() == datetime.now().date():
            string_event_date = "d'aujourd'hui programmé à %s" % event_date.time().strftime("%Hh%M")
        else:
            # or in the past
            string_event_date = "du %s à %s" % (
                event_date.date().strftime('%d-%h-%Y'), event_date.time().strftime("%Hh%M"))
        if state == 5:
            if employees.google_user_id:
                made_by = "<users/%s>" % employees.google_user_id
            else:
                made_by = "*%s*" % employees.user.first_name
            message = 'Attention *NON FAIT* le <%s%s|passage> %s pour *%s* chez *%s* : %s' % (
                config.ROOT_URL, event.get_admin_url(),
                string_event_date, made_by,
                _patient_name,
                event_report)
        else:
            if employees.google_user_id:
                made_by = "<users/%s>" % employees.google_user_id
            else:
                made_by = "*%s*" % employees.user.first_name
            message = 'Attention *ANNULÉ* le <%s%s|passage> %s pour *%s* chez *%s* : %s' % (
                config.ROOT_URL, event.get_admin_url(),
                string_event_date,
                made_by,
                _patient_name,
                event_report)
    elif  state in [5, 6] and patient is None:
        # if date is in the future, message will contain the date
        if event_date.date() > datetime.now().date():
            string_event_date = "du %s programmé à %s" % (event_date.date().strftime('%d-%h-%Y'),
                                                          event_date.time().strftime("%Hh%M"))
        elif event_date.date() == datetime.now().date():
            string_event_date = "d'aujourd'hui programmé à %s" % event_date.time().strftime("%Hh%M")
        else:
            # or in the past
            string_event_date = "du %s à " % (
                event_date.date().strftime('%d-%h-%Y'), event_date.time().strftime("%Hh%M"))
        if state == 5:
            if employees.google_user_id:
                made_by = "<users/%s>" % employees.google_user_id
            else:
                made_by = "*%s*" % employees.user.first_name
            message = 'Attention *NON FAIT* le <%s%s|passage> %s pour *%s* : %s' % (
                config.ROOT_URL, event.get_admin_url(),
                string_event_date, made_by,
                event_report)
        else:
            if employees.google_user_id:
                made_by = "<users/%s>" % employees.google_user_id
            else:
                made_by = "*%s*" % employees.user.first_name
            message = 'Attention *ANNULÉ* le <%s%s|passage> %s pour *%s* : %s' % (
                config.ROOT_URL, event.get_admin_url(),
                string_event_date,
                made_by,
                event_report)

    url = settings.GOOGLE_CHAT_WEBHOOK_URL
    if event_pictures_urls:
        counter_pictures = 0
        for event_pictures_url in event_pictures_urls:
            counter_pictures += 1
            message += "\n cliquez sur la photo %s <%s>" % (counter_pictures, event_pictures_url)
    bot_message = {
        'text': message}
    if not os.environ.get('LOCAL_ENVXXX', None):
        if not event.google_chat_message_id or "0" == event.google_chat_message_id:
            ReportChatSending(email=employees.user.email).send_text.delay(message=message,
                                                                          event=event)
        else:
            ReportChatSending(email=employees.user.email).update_text(message=message,
                                                                      google_chat_message_id=event.google_chat_message_id)
    else:
        if not event.google_chat_message_id or "0" == event.google_chat_message_id:
            ReportChatSending(email=employees.user.email).send_text(message=message, event=event)
        else:
            ReportChatSending(email=employees.user.email).update_text(message=message,
                                                                      google_chat_message_id=event.google_chat_message_id)
    return bot_message
    # message_headers = {'Content-Type': 'application/json; charset=UTF-8'}
    # http_obj = Http()
    # response = http_obj.request(
    #     uri=url,
    #     method='POST',
    #     headers=message_headers,
    #     body=dumps(bot_message),
    # )
    # print(response)

    # response2 = http_obj.request(uri="url",
    #                              method="GET",
    #                              headers=message_headers)
    # print(response2)
    #
    # # Specify required scopes.
    # SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']
    #
    # # Specify service account details.
    # CREDENTIALS = ServiceAccountCredentials.from_json_keyfile_name(
    #     #'service_account.json', SCOPES)
    #     settings.GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE2, SCOPES)
    #
    # # Build the URI and authenticate with the service account.
    # service = build('admin', 'directory_v1', http=CREDENTIALS.authorize(Http()))
    # results = service.users().list(domain='xxx.fr').execute()
    # #results = service.users().get(userKey='toto@bibi.oxx').execute()
    # print(results)
    # #"https: // chat.googleapis.com / v1 / {parent = spaces / *} / members"
