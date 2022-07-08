from django import forms
from django.contrib.admin.widgets import AdminSplitDateTime, AdminTextInputWidget
from django.forms import Select


class CustomAdminSplitDateTime(AdminSplitDateTime):
    def render(self, name, value, attrs=None, renderer=None):
        self.template_name = 'widgets/split_datetime.html'
        output = super(CustomAdminSplitDateTime, self).render(name, value, attrs, renderer)

        return output

    class Media:
        js = ('js/widgets/split-datetime-default.js',)


class CodeSnWidget(AdminTextInputWidget):
    class Media:
        js = ('js/jquery.maskedinput.min.js',
              'js/widgets/code-sn-mask.js',)


class MedicalPrescriptionSelect(Select):
    template_name = 'widgets/select-medical-prescription.html'

    def render(self, name, value, attrs=None, renderer=None):
        self.template_name = 'widgets/select-medical-prescription.html'
        output = super(MedicalPrescriptionSelect, self).render(name, value, attrs, renderer)
        return output

    def get_context(self, name, value, attrs):
        context = super(MedicalPrescriptionSelect, self).get_context(name, value, attrs)

        tags_weight = attrs.pop('user_tags_order', [])
        optgroups = context['widget']['optgroups']
        return context

    class Media:
        js = ('js/widgets/select-medical-prescription.js',)


class MedicalPrescriptionSelect2(Select):
    template_name = 'widgets/select-medical-prescription.html'
    _widget_js = [
        'js/jquery.js',  # This comes from django-jquery package
        'js/ajax/init.js',  # This is boilerplate code from Django
        'js/widgets/select-medical-prescription.js',
    ]

    def __init__(self, *args, **kwargs):
        attrs = kwargs.pop('attrs')
        # include any additional js for widget
        self._widget_js += attrs.pop('widget_js', [])
        kwargs['attrs'] = attrs
        super().__init__(*args, **kwargs)

    @property
    def media(self):
        return forms.Media(js=self._widget_js)
