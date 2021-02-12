import sys

from rq import Queue
from worker import conn
from invoices.events import Event

PLANNING_SCRIPT_CREATOR_NAME = "planning script"


def delete_events_created_by_script(year: int, month: int):
    print("Trying to delete: %s - %s " % (year, month))
    sys.stdout.flush()
    return_events_to_delete_dict = []
    events_to_delete = Event.objects.filter(day__year=year, day__month=month,
                                            created_by=PLANNING_SCRIPT_CREATOR_NAME)

    print("Found %s events" % events_to_delete.count())
    for e in events_to_delete:
        return_events_to_delete_dict.append(e)
        e.delete()
    events_to_delete.delete()
    return return_events_to_delete_dict


def async_deletion(year: int, month: int):
    q = Queue(connection=conn)
    q.enqueue(delete_events_created_by_script, year, month)
    return None
