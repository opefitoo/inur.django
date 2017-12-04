import json
from dal import autocomplete


class AutocompleteModelSelect2CustomWidget(autocomplete.ModelSelect2):
    def __init__(self, *args, **kwargs):
        super(AutocompleteModelSelect2CustomWidget, self).__init__(*args, **kwargs)
        self.attrs['data-is_custom_autocomplete_light'] = json.dumps(True)
        self.attrs['data-forward'] = json.dumps(self.forward)

    class Media:
        js = ('js/widgets/autocomplete-light-custom.js',)
