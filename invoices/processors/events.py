from invoices.events import Event

PLANNING_SCRIPT_CREATOR_NAME = "planning script"


def delete_events_created_by_script(year: int, month: int):
    events_to_delete = Event.objects.filter(day__year=year, day__month=month, created_by=PLANNING_SCRIPT_CREATOR_NAME)
    for e in events_to_delete:
        e.delete()
    return events_to_delete

