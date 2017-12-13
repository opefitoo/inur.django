import json
from dal import autocomplete
from django.contrib.admin.widgets import AdminSplitDateTime


class AutocompleteModelSelect2CustomWidget(autocomplete.ModelSelect2):
    def __init__(self, *args, **kwargs):
        super(AutocompleteModelSelect2CustomWidget, self).__init__(*args, **kwargs)
        self.attrs['data-is_custom_autocomplete_light'] = json.dumps(True)
        self.attrs['data-forward'] = json.dumps(self.forward)

    class Media:
        js = ('js/widgets/autocomplete-light-custom.js',)


class CustomAdminSplitDateTime(AdminSplitDateTime):
    def render(self, name, value, attrs=None, renderer=None):
        self.template_name = 'widgets/split_datetime.html'
        output = super(CustomAdminSplitDateTime, self).render(name, value, attrs, renderer)

        return output

    class Media:
        js = ('js/widgets/split-datetime-default.js',)
