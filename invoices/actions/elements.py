from abc import abstractmethod, ABC
from collections import OrderedDict

import pytz
from django.utils.datetime_safe import datetime
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle, Spacer, Paragraph
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
import typing

from invoices.action_private import _compute_sum

__pytz_luxembourg = pytz.timezone("Europe/Luxembourg")


class AbstractDetails(ABC):
    __pytz_luxembourg = pytz.timezone("Europe/Luxembourg")

    def attributes_as_array(self, count=None) -> [str]:
        rs = []
        if count:
            rs.append(count)
        for attr, value in self.__dict__.items():
            rs.append(value)
        return rs

    def transform_datetime_to_localized_date_str(self, datetime_param):
        return self.__pytz_luxembourg.normalize(datetime_param).strftime('%d/%m/%Y')

    def transform_datetime_to_localized_time_str(self, datetime_param):
        return self.__pytz_luxembourg.normalize(datetime_param).strftime("%H:%M")


class CnsNursingCareDetail(AbstractDetails):
    def __init__(self, code: str, care_datetime: datetime, quantity: int,
                 net_price: int, gross_price: int, provider_code: str):
        """

        @type gross_price: int
        """
        self.code = code
        self.date_str = self.transform_datetime_to_localized_date_str(care_datetime)
        self.quantity = quantity
        self.gross_price = gross_price
        self.net_price = net_price
        self.time_st = self.transform_datetime_to_localized_time_str(care_datetime)
        self.pers_part = gross_price - net_price
        self.provider_code = provider_code

    def to_array_string(self):
        _pytz_luxembourg = pytz.timezone("Europe/Luxembourg")
        return ""
        # return (self.code, _pytz_luxembourg.normalize(self.care_datetime.date)).strftime('%d/%m/%Y'))
        #     presta.carecode.code,
        #     (pytz_luxembourg.normalize(presta.date)).strftime('%d/%m/%Y'),
        #     '1',
        #     presta.carecode.gross_amount(presta.date),
        #     presta.carecode.net_amount(presta.date, patient.is_private, (patient.participation_statutaire
        #                                                                  and patient.age > 18)),
        #     (pytz_luxembourg.normalize(presta.date)).strftime('%H:%M'),
        #     "",
        #     presta.employee.provider_code)


class NurseDetails(AbstractDetails):
    def __init__(self, fullname: str, address: str, zipcode_city: str, phone_number: str, provider_code: str):
        self.fullname = fullname
        self.address = address
        self.zipcode_city = zipcode_city
        self.phone_number = phone_number
        self.provider_code = provider_code

    def beautiful_str(self):
        return ['IDENTIFICATION DU FOURNISSEUR DE SOINS DE SANTE\n'
                + "{0}\n{1}\n{2}\n{3}".format(self.fullname, self.address, self.zipcode_city, self.phone_number),
                'CODE DU FOURNISSEUR DE SOINS DE SANTE\n{0}'.format(self.provider_code)]


class RowDict(OrderedDict):
    def __init__(self):
        self._dict = {}

    def add(self, key, val):
        self._dict[key] = val

    @property
    def dict(self):
        return self._dict


class AnotherBodyPage(AbstractDetails):
    def __init__(self, rows: RowDict):
        self.rows = rows
        self.fst_gross_sub_total = None
        self.snd_gross_sub_total = None
        self.fst_net_sub_total = None
        self.snd_net_sub_total = None

    def to_array(self):
        result = [('Num. titre', 'Prestation', 'Date', 'Nombre', 'Brut', 'Net', 'Heure', 'P. Pers', 'Exécutant')]
        _sub_total = 0
        gross_sub_total = 0
        net_sub_total = 0
        for idx in self.rows.dict:
            _current_row = self.rows.dict[idx]
            if isinstance(_current_row, CnsNursingCareDetail):
                gross_sub_total += _current_row.gross_price
                net_sub_total += _current_row.net_price
                result.append(_current_row .attributes_as_array(idx))
                if idx == 10:
                    self.fst_gross_sub_total = gross_sub_total
                    self.fst_net_sub_total = net_sub_total
                    result.append(('', '', '', 'Sous-Total', self.fst_gross_sub_total, self.fst_net_sub_total, '', '', ''))
                    gross_sub_total = 0
                    net_sub_total = 0
                elif idx == len(self.rows.dict) or idx == 20:
                    self.snd_gross_sub_total = gross_sub_total
                    self.snd_net_sub_total = net_sub_total
        for x in range(len(self.rows.dict)+1, 21):
            result.append((x, '', '', '', '', '', '', '', ''))
        result.append(
            ('', '', '', 'Sous-Total', self.snd_gross_sub_total, self.snd_net_sub_total, '', '', ''))
        result.append(('', '', '', 'Total',
                       self.fst_gross_sub_total + self.snd_gross_sub_total,
                       self.fst_net_sub_total + self.snd_net_sub_total, '', '', ''))
        return result

    def get_table(self) -> Table:
        self.attributes_as_array()
        table = Table(self.to_array(), 9 * [2 * cm], 24 * [0.5 * cm])
        table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                                   ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                   ('ALIGN', (0, -1), (-6, -1), 'RIGHT'),
                                   ('INNERGRID', (0, -1), (-6, -1), 0, colors.white),
                                   ('ALIGN', (0, -2), (-6, -2), 'RIGHT'),
                                   ('INNERGRID', (0, -2), (-6, -2), 0, colors.white),
                                   ('FONTSIZE', (0, 0), (-1, -1), 8),
                                   ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                   ]))
        return table

    def __str__(self):
        return self.to_array()


class InvoiceNumberDate(AbstractDetails):
    def __init__(self, invoice_number: str, invoice_date: str):
        self.invoice_date = invoice_date
        self.invoice_number = invoice_number


class PatientAbstractDetails(AbstractDetails):
    def __init__(self, sn_code: str, fst_nm: str, last_nm: str, adr: str, zip_code: str, city: str,
                 accident_date: str, accident_num: str):
        self.city = city.strip()
        self.zip_code = zip_code.strip()
        self.adr = adr.strip()
        self.last_nm = last_nm.strip()
        self.fst_nm = fst_nm.strip()
        self.sn_code = sn_code.strip()
        self.accident_date = accident_date
        self.accident_num = accident_num

    def beautiful_patient_coordinates(self):
        return [u'Matricule patient: %s\n' % self.sn_code
                + u'Nom et Prénom du patient: %s %s' % (self.last_nm, self.fst_nm),
                u'Nom: %s\n' % self.last_nm
                + u'Prénom: %s\n' % self.fst_nm
                + u'Rue: %s\n' % self.adr
                + u'Code postal: %s\n' % self.zip_code
                + u'Ville: %s' % self.city]

    def beautiful_accident_details(self):
        return [u'Date accident: %s\n' % (self.accident_date if self.accident_date else "")
                + u'Num. accident: %s' % (self.accident_num if self.accident_num else "")]


class InvoiceHeaderData:

    def __init__(self, nurse_details: NurseDetails, patient_details: PatientAbstractDetails,
                 invoice_nbr_date: InvoiceNumberDate) -> object:
        self.invoice_nbr_date = invoice_nbr_date
        self.nurse_details = nurse_details
        self.patient_details = patient_details

    def build_element(self) -> [Table]:
        elements = []
        hdr_tbl = Table([self.nurse_details.beautiful_str(),
                         self.patient_details.beautiful_patient_coordinates(),
                         self.patient_details.beautiful_accident_details()], 2 * [10 * cm],
                        [2.5 * cm, 1 * cm, 1.5 * cm])
        hdr_tbl.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                                     ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                     ('FONTSIZE', (0, 0), (-1, -1), 9),
                                     ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                     ('SPAN', (1, 1), (1, 2)),
                                     ]))
        elements.append(hdr_tbl)

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
        elements.append(Spacer(1, 18))
        elements.append(
            Paragraph(u"Mémoire d'Honoraires Num. %s en date du : %s" % (self.invoice_nbr_date.invoice_number,
                                                                         self.invoice_nbr_date.invoice_date),
                      styles['Center']))
        elements.append(Spacer(1, 18))
        return elements
