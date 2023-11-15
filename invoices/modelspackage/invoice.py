from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField


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
    # registre de commerce
    rc = models.CharField("Registre de commerce", max_length=50, null=True, blank=True)
    # autorisation ministère de la famille activités soins à domicile
    af = models.CharField("Autorisation ministère de la famille activités soins à domicile" , max_length=50, null=True, blank=True)
    # autorisation ministère de la famille activités aides à domicile
    aa = models.CharField("Autorisation ministère de la famille activités aides à domicile", max_length=50, null=True, blank=True)
    default_invoicing = models.BooleanField(default=False)
    xero_tenant_id = models.CharField(max_length=50, null=True, blank=True)

    def get_full_address(self):
        return '%s, %s %s' % (self.address, self.zipcode_city, self.country)

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
    # if rc column does not exist, return None
    if not InvoicingDetails._meta.get_field('rc'):
        return None
    # if called before migration, return None
    try:
        return InvoicingDetails.objects.get(default_invoicing=True)
    except Exception:
        return None
