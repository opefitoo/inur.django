from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import models
from django_countries.fields import CountryField
from django.utils.translation import gettext_lazy as _


class InvoicingDetails(models.Model):
    class Meta(object):
        ordering = ['-id']
        verbose_name = u"Détail de facturation"
        verbose_name_plural = u"Détail de facturation"

    provider_code = models.CharField(max_length=10)
    name = models.CharField(max_length=30)
    address = models.TextField(max_length=50)
    zipcode_city = models.CharField(max_length=20)
    country = CountryField(blank_label='...', blank=True, null=True, default="LU")
    phone_number = models.CharField(max_length=30)
    email_address = models.EmailField(default=None, blank=True, null=True, validators=[EmailValidator])
    bank_account = models.CharField(max_length=50)
    default_invoicing = models.BooleanField(default=False)

    def clean(self):
        # Don't allow draft entries to have a pub_date.
        default_details = InvoicingDetails.objects.filter(default_invoicing=True).exclude(pk=self.id)
        if self.default_invoicing and default_details.count() > 0:
            raise ValidationError({
                'default_invoicing':
                    ValidationError(_('Already set "%s"  as default, unset it first.' % default_details[0]),
                                    code='invalid')
            })

    def __str__(self):
        return '%s - %s' % (self.name, self.provider_code)


def get_default_invoicing_details():
    return InvoicingDetails.objects.get(default_invoicing=True).id
