import logging
from datetime import datetime, timedelta
from json import dumps

from constance import config
from httplib2 import Http

from invoices import settings

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


def post_webhook(employees, patient, event_report, state, event_date=None, event_pictures_urls=None, event=None):
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
    if patient is None:
        return
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
    if 3 == state:
        message = '<%s%s|Passage> %s FAIT par *%s* chez *%s* : %s  ' % (config.ROOT_URL, event.get_admin_url(),
                                                                        string_event_date, employees.user.first_name,
                                                                        patient.name,
                                                                        event_report
                                                                        )
    # FIXME: remove hardcoded value for state
    elif state in [5, 6]:
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
            message = 'Attention *NON FAIT* le <%s%s|passage> %s pour *%s* chez *%s* : %s' % (
                config.ROOT_URL, event.get_admin_url(),
                string_event_date, employees.user.first_name,
                patient.name,
                event_report)
        else:
            message = 'Attention *ANNULÉ* le <%s%s|passage> %s pour *%s* chez *%s* : %s' % (
                config.ROOT_URL, event.get_admin_url(),
                string_event_date,
                employees.user.first_name,
                patient.name,
                event_report)

    url = settings.GOOGLE_CHAT_WEBHOOK_URL
    if event_pictures_urls:
        counter_pictures = 0
        for event_pictures_url in event_pictures_urls:
            counter_pictures += 1
            message += "\n cliquez sur la photo %s <%s>" % (counter_pictures, event_pictures_url)
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
