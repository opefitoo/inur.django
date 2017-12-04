from dal import autocomplete
from django.db.models import Q

from invoices.models import CareCode, Prestation


class CareCodeAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return CareCode.objects.none()

        qs = CareCode.objects.all()
        at_home = self.forwarded.get('at_home', False)
        if at_home:
            qs = qs.filter(code=Prestation.AT_HOME_CARE_CODE)

        if self.q:
            qs = qs.filter(Q(name__contains=self.q) | Q(code__contains=self.q))

        return qs
