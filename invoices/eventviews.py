from datetime import datetime

from constance import config
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from .events import Event
from .forms import EventForm


def get_object(area, model_class):
    _id = area.kwargs.get('id')
    obj = None
    if _id is not None:
        obj = get_object_or_404(model_class, id=_id)
    return obj


class Calendar1View(View):
    template = "events/calendar.html"
    context = {}
    form = EventForm

    def get(self, request, *args, **kwargs):
        object_list = Event.objects.filter(day__month=datetime.today().month)
        event_states = Event.STATES  # Assuming Event.STATES contains your states

        # Assuming you have an event_id to edit
        event_id = request.GET.get('event_id')
        current_event = None
        if event_id:
            current_event = get_object_or_404(Event, pk=event_id)

        self.context = {'object_list': object_list, 'root_url': config.ROOT_URL, 'form': self.form
            , 'event_states': event_states, 'current_event': current_event}

        return render(request, self.template, self.context)

    def post(self, request, *args, **kwargs):
        obj = get_object(self, Event)

        if obj:
            self.form = self.form(request.POST, instance=obj)
        else:
            self.form = self.form(request.POST)

        if self.form.is_valid():
            self.form.save()
            return redirect('calendar_1')

        return render(request, self.template, self.context)


def load_calendar_form(request):  # AJAX CALL
    start_date = datetime.now()
    if request.is_ajax():
        start_date = request.POST.get('start_date')
        print("AJAX")

    print('DATA', start_date, type(start_date))

    try:
        _date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
    except:
        try:
            _date = datetime.strptime(start_date, '%Y-%m-%d')
        except:
            _date = None
    print('DATE after conversion', _date, type(_date))

    form = EventForm(initial={
        'scheduled_datetime': _date,
        'effective_datetime': _date,
    })
    form.fields['scheduled_datetime'].widget = forms.DateTimeInput(
        attrs={
            'class': 'form-control',
            # 'type': 'datetime-local',
        })
    form.fields['effective_datetime'].widget = forms.DateTimeInput(
        attrs={
            'class': 'form-control',
            # 'type': 'datetime-local',
        })

    # data = {}
    # data['_date'] = _date
    # return JsonResponse(data)
    return render(request, 'event_add_form.html', {'form': form})


def update_calendar_form(request):  # AJAX CALL
    object_id = None

    # checks if the request is ajax
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        object_id = request.POST.get('object_id')
        print("AJAX")

    print('DATA', object_id, type(object_id))

    if object_id:
        try:
            obj = Event.objects.get(id=object_id)
        except:
            pass

        if obj:
            print(obj)
            form = EventForm(instance=obj)
            form.fields['time_start_event'].widget = forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                })

    return render(request, 'events/event_update_form.html', {
        'form': form,
        'object': obj
    })
