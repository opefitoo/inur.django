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


