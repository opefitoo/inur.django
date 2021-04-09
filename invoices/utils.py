__author__ = 'mehdi'

# credit goes to: http://stackoverflow.com/questions/18593661/how-do-i-strftime-a-date-object-in-a-different-locale

# import locale
# import threading
#
# from contextlib import contextmanager

from calendar import HTMLCalendar

from django.utils.datetime_safe import date

from invoices.events import Event


# LOCALE_LOCK = threading.Lock()


# @contextmanager
# def setlocale(name):
#     with LOCALE_LOCK:
#         saved = locale.setlocale(locale.LC_ALL)
#         try:
#             yield locale.setlocale(locale.LC_ALL, name)
#         finally:
#             locale.setlocale(locale.LC_ALL, saved)


class EventCalendar(HTMLCalendar):
    def __init__(self, events=None) -> HTMLCalendar:
        super(EventCalendar, self).__init__()
        self.events = events

    def formatday(self, day, weekday, events):
        """
        Return a day as a table cell.
        """
        events_from_day = events.filter(day__day=day)
        events_html = '<ul>'
        for event in events_from_day:
            events_html += event.get_absolute_url() + '<br>'
        events_html += "</ul>"
        if day == 0:
            return '<td class="noday">&nbsp;</td>'  # day outside month
        elif date.today().day == day:
            return '<td style="background-color:B7E1CD;" class="%s">%d%s</td>' % (self.cssclasses[weekday], day,
                                                                                  events_html)
        else:
            return '<td class="%s">%d%s</td>' % (self.cssclasses[weekday], day, events_html)

    def formatweek(self, theweek, events):
        """
        Return a complete week as a table row.
        """
        s = ''.join(self.formatday(d, wd, events) for (d, wd) in theweek)
        return '<tr>%s</tr>' % s

    def formatmonth(self, theyear, themonth, withyear=True, employee_id=None):
        """
        Return a formatted month as a table.
        """
        if employee_id:
            events = Event.objects.filter(day__year=theyear, day__month=themonth, employees_id=employee_id).order_by('-day', 'time_start_event')
        else:
            events = Event.objects.filter(day__year=theyear, day__month=themonth).order_by('-day', 'time_start_event')
        v = []
        a = v.append
        a('<table border="0" cellpadding="0" cellspacing="0" class="month">')
        a('\n')
        a(self.formatmonthname(theyear, themonth, withyear=withyear))
        a('\n')
        a(self.formatweekheader())
        a('\n')
        for week in self.monthdays2calendar(theyear, themonth):
            a(self.formatweek(week, events))
            a('\n')
        a('</table>')
        a('\n')
        return ''.join(v)
