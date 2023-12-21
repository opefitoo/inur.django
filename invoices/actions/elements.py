import decimal
from abc import ABC
from collections import OrderedDict
from datetime import datetime
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle, Spacer, Paragraph

from invoices.actions import helpers
from invoices.enums.pdf import PdfActionType
from invoices.modelspackage import InvoicingDetails


class AbstractDetails(ABC):

    __zoneinfo = ZoneInfo("Europe/Luxembourg")

    def attributes_as_array(self, count=None, except_attrs=[]) -> [str]:
        rs = []
        if count:
            rs.append(count)
        for attr, value in self.__dict__.items():
            if attr not in except_attrs:
                rs.append(value)
                continue
        return rs

    def transform_datetime_to_localized_date_str(self, datetime_param):
        return datetime_param.astimezone(self.__zoneinfo).strftime('%d/%m/%Y')

    def transform_datetime_to_localized_time_str(self, datetime_param):
        return datetime_param.astimezone(self.__zoneinfo).strftime("%H:%M")


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
        return ""


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


class MedicalCareBodyPage(AbstractDetails):
    def __init__(self, rows: RowDict, pdf_action_type: PdfActionType):
        self.rows = rows
        self.fst_gross_sub_total = 0.0
        self.snd_gross_sub_total = 0.0
        self.fst_net_sub_total = 0.0
        self.snd_net_sub_total = 0.0
        self.fst_pp_sub_total = 0.0
        self.snd_pp_sub_total = 0.0
        self.pdf_action_type = pdf_action_type

    def build_personal_participation_elements(self):
        result = [('Num. titre', 'Prestation', 'Date', 'Nombre', 'Brut', 'CNS', 'Part. Client')]
        gross_sub_total = 0
        net_sub_total = 0
        for idx in range(1, 11):
            _current_row = self.rows.dict.get(idx, None)
            if _current_row and isinstance(_current_row, CnsNursingCareDetail):
                gross_sub_total += _current_row.gross_price
                net_sub_total += _current_row.net_price
                result.append(_current_row.attributes_as_array(idx, except_attrs=['time_st', 'provider_code']))
            else:
                # filling the gaps
                result.append((idx, '', '', '', '', '', ''))
        self.fst_gross_sub_total = gross_sub_total
        self.fst_net_sub_total = net_sub_total
        self.fst_pp_sub_total = self.fst_gross_sub_total - self.fst_net_sub_total
        result.append(
            ('', '', '', 'Sous-Total', self.fst_gross_sub_total, self.fst_net_sub_total, self.fst_pp_sub_total))
        gross_sub_total = 0
        net_sub_total = 0
        for idx in range(11, 21):
            _current_row = self.rows.dict.get(idx, None)
            if _current_row and isinstance(_current_row, CnsNursingCareDetail):
                gross_sub_total += _current_row.gross_price
                net_sub_total += _current_row.net_price
                result.append(_current_row.attributes_as_array(idx, except_attrs=['time_st', 'provider_code']))
            else:
                # filling the gaps
                result.append((idx, '', '', '', '', '', ''))
        self.snd_gross_sub_total = gross_sub_total
        self.snd_net_sub_total = net_sub_total
        self.snd_pp_sub_total = self.snd_gross_sub_total - self.snd_net_sub_total
        result.append(
            ('', '', '', 'Sous-Total', self.snd_gross_sub_total, self.snd_net_sub_total, self.snd_pp_sub_total))
        result.append(('', '', '', 'Total',
                       self.fst_gross_sub_total + self.snd_gross_sub_total,
                       self.fst_net_sub_total + self.snd_net_sub_total,
                       self.fst_pp_sub_total + self.snd_pp_sub_total))
        return result

    def to_array(self):
        result = [('Num. titre', 'Prestation', 'Date', 'Nombre', 'Brut', 'Net', 'Heure', 'P. Pers', 'Exécutant')]
        # _sub_total = 0
        gross_sub_total = 0
        net_sub_total = 0
        for idx in range(1, 11):
            _current_row = self.rows.dict.get(idx, None)
            if _current_row and isinstance(_current_row, CnsNursingCareDetail):
                gross_sub_total += _current_row.gross_price
                net_sub_total += _current_row.net_price
                result.append(_current_row.attributes_as_array(idx))
            else:
                # filling the gaps
                result.append((idx, '', '', '', '', '', '', '', ''))
        self.fst_gross_sub_total = gross_sub_total
        self.fst_net_sub_total = net_sub_total
        result.append(('', '', '', 'Sous-Total', self.fst_gross_sub_total, self.fst_net_sub_total, '', '', ''))
        gross_sub_total = 0
        net_sub_total = 0
        for idx in range(11, 21):
            _current_row = self.rows.dict.get(idx, None)
            if _current_row and isinstance(_current_row, CnsNursingCareDetail):
                gross_sub_total += _current_row.gross_price
                net_sub_total += _current_row.net_price
                result.append(_current_row.attributes_as_array(idx))
            else:
                # filling the gaps
                result.append((idx, '', '', '', '', '', '', '', ''))
        self.snd_gross_sub_total = gross_sub_total
        self.snd_net_sub_total = net_sub_total
        result.append(('', '', '', 'Sous-Total', self.snd_gross_sub_total, self.snd_net_sub_total, '', '', ''))
        result.append(('', '', '', 'Total',
                       self.fst_gross_sub_total + self.snd_gross_sub_total,
                       self.fst_net_sub_total + self.snd_net_sub_total, '', '', ''))
        return result

    def get_table(self) -> Table:
        # self.attributes_as_array()
        if self.pdf_action_type == PdfActionType.CNS:
            data_array = self.to_array()
        elif self.pdf_action_type == PdfActionType.PERSONAL_PARTICIPATION:
            data_array = self.build_personal_participation_elements()
        table = Table(data_array, len(data_array[0]) * [19 / (len(data_array[0])) * cm], 24 * [0.5 * cm])
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


class SummaryData(AbstractDetails):

    def __init__(self, order_number, invoice_num, patient_name, total_amount, iban):
        self.order_number = order_number
        self.invoice_num = invoice_num
        self.patient_name = patient_name
        self.total_amount = total_amount
        self.iban = iban


class PersonalParticipationSummaryDataTable:
    def __init__(self, summary_data_list: [SummaryData]):
        self.summary_data_list = summary_data_list
        self.total_summary = 0.0

    def get_table(self):
        elements = [Table([[
            u"Veuillez trouver ci-joint le récapitulatif des factures ainsi que le montant total à payer"]],
            [10 * cm, 5 * cm], 1 * [0.5 * cm], hAlign='LEFT'), Spacer(1, 18)]
        data = [("No d'ordre", u"Note no°", u"Nom et prénom", "Montant")]
        total = 0.0
        for recap in self.summary_data_list:
            data.append(recap.attributes_as_array(except_attrs=['iban']))
            total = decimal.Decimal(total) + decimal.Decimal(recap.total_amount)
        self.total_summary = round(total, 2)
        data.append(("", "", u"À reporter", self.total_summary, ""))
        table = Table(data, [2 * cm, 3 * cm, 7 * cm, 3 * cm], (len(self.summary_data_list) + 2) * [0.75 * cm])
        table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                                   ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                   ('FONTSIZE', (0, 0), (-1, -1), 9),
                                   ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                   ]))

        # _date_infos = Table([["Date facture : %s " % self.summary_data_list]], [10 * cm], 1 * [0.5 * cm], hAlign='LEFT')
        elements.append(table)
        elements.append(Spacer(1, 18))
        elements.append(Table(
            [[u"Lors du virement, veuillez indiquer la référence: %s " % helpers.generate_payment_reference([i.invoice_num for i in self.summary_data_list])]],
            [10 * cm], 1 * [0.5 * cm], hAlign='LEFT'))

        elements.append(Spacer(1, 18))
        elements.append(Table([["Total à payer:", "%10.2f Euros" % self.total_summary]], [10 * cm, 5 * cm],
                          1 * [0.5 * cm],
                          hAlign='LEFT'))
        elements.append(Spacer(1, 18))
        elements.append(Table([[u"Numéro IBAN: %s" % self.summary_data_list[0].iban]], [10 * cm], 1 * [0.5 * cm], hAlign='LEFT'))


        return elements


class SummaryDataTable:
    def __init__(self, summary_data_list: [SummaryData]):
        self.summary_data_list = summary_data_list
        self.total_summary = 0.0

    def get_table(self):
        elements = []
        data = [("No d'ordre", u"Note no°", u"Nom et prénom", "Montant", u"réservé à la caisse")]
        total = 0.0
        for recap in self.summary_data_list:
            data.append(recap.attributes_as_array(except_attrs=['iban']))
            total = decimal.Decimal(total) + decimal.Decimal(recap.total_amount)
        self.total_summary = round(total, 2)
        data.append(("", "", u"à reporter", self.total_summary, ""))
        table = Table(data, [2 * cm, 3 * cm, 7 * cm, 3 * cm, 3 * cm], (len(self.summary_data_list) + 2) * [0.75 * cm])
        table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                                   ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                   ('FONTSIZE', (0, 0), (-1, -1), 9),
                                   ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                   ]))
        elements.append(table)
        return elements


class CnsFinalPage:

    def __init__(self, total_summary, order_number, invoicing_details: InvoicingDetails):
        self.total_summary = total_summary
        self.order_number = order_number
        self.invoicing_details = invoicing_details

    def get_table(self):
        elements = []
        data = [["RELEVE DES NOTES D’HONORAIRES DES"],
                ["ACTES ET SERVICES DES INFIRMIERS"]]
        table = Table(data, [10 * cm], [0.75 * cm, 0.75 * cm])
        table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                   ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
                                   ('FONTSIZE', (0, 0), (-1, -1), 12),
                                   ('BOX', (0, 0), (-1, -1), 1.25, colors.black),
                                   ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                   ]))
        elements.append(table)
        elements.append(Spacer(1, 18))
        data2 = [
            [u"Identification du fournisseur de", self.invoicing_details.name, "",
             u"réservé à l’union des caisses de maladie"],
            [u"soins de santé", "", "", ""],
            [u"Coordonnées bancaires :", self.invoicing_details.bank_account, "", ""],
            ["Code: ", self.invoicing_details.provider_code, "", ""]]
        table2 = Table(data2, [5 * cm, 3 * cm, 3 * cm, 7 * cm], [1.25 * cm, 0.5 * cm, 1.25 * cm, 1.25 * cm])
        table2.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                    ('ALIGN', (3, 0), (3, 0), 'CENTER'),
                                    ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
                                    ('SPAN', (1, 2), (2, 2)),
                                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                                    ('BOX', (3, 0), (3, 3), 0.25, colors.black),
                                    ('BOX', (3, 0), (3, 1), 0.25, colors.black),
                                    ('BOX', (1, 3), (1, 3), 1, colors.black)]))
        elements.append(table2)
        elements.append(Spacer(1, 20))
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
        elements.append(Paragraph(
            u"Récapitulation des notes d’honoraires du chef de la fourniture de soins de santé dispensés aux personnes protégées relevant de l’assurance maladie / assurance accidents ou de l’assurance dépendance.",
            styles['Justify']))
        elements.append(Spacer(2, 20))
        elements.append(
            Paragraph(
                u"Pendant la période du :.................................. au :..................................",
                styles['Justify']))
        data3 = [["Nombre des mémoires d’honoraires ou\nd’enregistrements du support informatique:",
                  self.order_number]]
        table3 = Table(data3, [9 * cm, 8 * cm], [1.25 * cm])
        table3.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'LEFT'),
                                    ('ALIGN', (-1, -1), (-1, -1), 'CENTER'),
                                    ('VALIGN', (-1, -1), (-1, -1), 'MIDDLE'),
                                    ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
                                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                                    ('BOX', (1, 0), (-1, -1), 1.25, colors.black)]))
        elements.append(Spacer(2, 20))
        elements.append(table3)
        elements.append(Spacer(2, 20))
        data4 = [[
            u"Montant total des honoraires à charge de\nl’organisme assureur (montant net cf. zone 14) du\nmém. d’honoraires):",
            "%.2f EUR" % round(self.total_summary, 2)]]
        table4 = Table(data4, [9 * cm, 8 * cm], [1.25 * cm])
        table4.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'LEFT'),
                                    ('ALIGN', (-1, -1), (-1, -1), 'CENTER'),
                                    ('VALIGN', (-1, -1), (-1, -1), 'MIDDLE'),
                                    ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
                                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                                    ('BOX', (1, 0), (-1, -1), 1.25, colors.black)]))
        elements.append(table4)
        elements.append(Spacer(40, 60))
        styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT))
        elements.append(Paragraph(
            u"Certifié sincère et véritable, mais non encore acquitté: ________________ ,le ______________________",
            styles['Left']))
        return elements


def build_cns_bottom_elements() -> []:
    elements = [Spacer(1, 18)]
    direct_payment_checkbox = Table([["", "Paiement Direct"]], [1 * cm, 4 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    direct_payment_checkbox.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'RIGHT'),
                                                 ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                                 ('FONTSIZE', (0, 0), (-1, -1), 9),
                                                 ('BOX', (0, 0), (0, 0), 0.75, colors.black),
                                                 ('SPAN', (1, 1), (1, 2)),
                                                 ]))

    elements.append(direct_payment_checkbox)
    elements.append(Spacer(1, 18))
    third_party_payment = Table([["", "Tiers payant"]], [1 * cm, 4 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    third_party_payment.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'RIGHT'),
                                             ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                             ('FONTSIZE', (0, 0), (-1, -1), 9),
                                             ('BOX', (0, 0), (0, 0), 0.75, colors.black),
                                             ('SPAN', (1, 1), (1, 2)),
                                             ]))

    elements.append(third_party_payment)
    elements.append(Spacer(1, 18))

    signature = Table([["Pour acquit, le:", "Signature et cachet"]], [10 * cm, 10 * cm], 1 * [0.5 * cm],
                      hAlign='LEFT')

    elements.append(signature)
    return elements


def build_pp_bottom_elements(summary_data: SummaryData) -> []:
    elements = [Spacer(1, 18),
                Table([["Total participation personnelle:", "%10.2f Euros" % summary_data.total_amount]],
                      [10 * cm, 5 * cm], 1 * [0.5 * cm], hAlign='LEFT'),
                Spacer(1, 18),
                Table([[u"Lors du virement, veuillez indiquer la référence: %s " % summary_data.invoice_num]],
                      [10 * cm], 1 * [0.5 * cm], hAlign='LEFT'),
                Spacer(1, 18),
                Table([[u"Numéro IBAN: %s" % summary_data.iban]], [10 * cm], 1 * [0.5 * cm], hAlign='LEFT'),
                Spacer(2, 18),
                Table([["Pour acquit, le:", "Signature et cachet"]], [10 * cm, 10 * cm], 1 * [0.5 * cm],
                      hAlign='LEFT')]

    return elements
