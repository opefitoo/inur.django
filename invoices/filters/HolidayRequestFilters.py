from django.contrib.admin import SimpleListFilter
from django.db.models import Count
from django.db.models.functions import TruncYear, TruncMonth

from invoices.holidays import HolidayRequest


class FilteringYears(SimpleListFilter):
    title = 'holiday_request_year'
    parameter_name = 'holiday_request_year'

    def lookups(self, request, model_admin):
        years = HolidayRequest.objects.annotate(year=TruncYear("start_date")).values("year").annotate(
            c=Count("id")).values("year", "c")
        years_tuple = []
        for year in years:
            years_tuple.append((str(year['year'].year), "%s (%s)" % (str(year['year'].year), str(year['c']))))
        return tuple(years_tuple)

    def queryset(self, request, queryset):
        value = self.value()
        if value is not None:
            return queryset.filter(start_date__year=value)
        return queryset


class FilteringMonths(SimpleListFilter):
    title = 'holiday_request_month'
    parameter_name = 'holiday_request_month'

    def lookups(self, request, model_admin):
        months = HolidayRequest.objects.annotate(month=TruncMonth("start_date")).values("month").annotate(
            c=Count("id")).values("month", "c").order_by("-start_date__year", "-start_date__month")
        month_tuple = []
        for month in months:
            month_tuple.append(("%s-%s" % (str(month['month'].year), str(month['month'].month)), "%s/%s (%s)" % (str(month['month'].year), str(month['month'].month), str(month['c']))))

            # month_tuple.append("%s/%s (%s)" % (str(month['month'].year), str(month['month'].month), str(month['c'])))
        return tuple(month_tuple)

    def queryset(self, request, queryset):
        value = self.value()
        if value is not None:
            return queryset.filter(start_date__year=value.split("-")[0], start_date__month=value.split("-")[1])
        return queryset
