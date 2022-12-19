from datetime import datetime
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

        self.context = {'object_list': object_list, 'form': self.form}

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

    if request.is_ajax():
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
            form.fields['scheduled_datetime'].widget = forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                })
            form.fields['effective_datetime'].widget = forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                })

    return render(request, 'event_update_form.html', {
        'form': form,
        'object': obj
    })