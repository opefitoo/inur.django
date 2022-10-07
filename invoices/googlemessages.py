import logging
from json import dumps

from httplib2 import Http

from invoices import settings

logger = logging.getLogger('console')


def post_webhook(employees, patient, event_report, state):
    """Hangouts Chat incoming webhook quickstart."""
    # FIXME: remove hardcoded value for state
    if patient is None:
        return
    if state not in [3, 5]:
        return
    if 3 == state:
        message = "Soin FAIT par %s chez %s : %s" % (employees.user.first_name, patient.name, event_report)
    # FIXME: remove hardcoded value for state
    elif 5 == state:
        message = "Soin non FAIT par %s chez %s : %s" % (employees.user.first_name, patient.name, event_report)
    url = settings.GOOGLE_CHAT_WEBHOOK_URL
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
