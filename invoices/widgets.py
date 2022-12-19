import base64

import requests
from django.contrib.admin.widgets import AdminSplitDateTime, AdminTextInputWidget, AdminFileWidget


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


class ContaboImageWidget(AdminFileWidget):
    template_name = "widgets/contabo_image_preview.html"

    def get_context(self, name, value, attrs):
        super().get_context(name, value, attrs)
        if value:
            r = requests.get(value.url, stream=True)
            encoded = ("data:" +
                       r.headers['Content-Type'] + ";" +
                       "base64," + base64.b64encode(r.content).decode('utf-8'))  # Convert to a string first
            context = {'imagedata': encoded, 'pdf_url': value.instance.file_upload.url}
            return context

    def render(self, name, value, attrs=None, renderer=None):
        self.template_name = "widgets/contabo_image_preview.html"
        output = super(ContaboImageWidget, self).render(name, value, attrs, renderer)
        return output
