from zoneinfo import ZoneInfo

from constance import config
from django.db.models import Case, When, Value, IntegerField
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _


def generate_file_line_for_calculation_control(data):
    for key, value in data.items():
        if isinstance(value, int):
            data[key] = str(value)
    line = "{version:<1.1};{date:<8.8};{payer:<1.1};{provider:<6.6};{patient:<13.13};{accident_number:<10.10};{invoice_number:<15.15};{prescription_date:<8.8};{validity_date:<8.8};{prescribing_doctor:<6.6};{nurse:<6.6};{service_code:<10.10};{service_date:<8.8};{end_date:<8.8};{start_time:<4.4};{end_time:<4.40};{times_executed:<3.3};{gross_amount:<7.7};{gross_amount_decimals:<2.2};{net_amount:<7.7};{net_amount_decimals:<2.2};{insurance_code:<4.4};{denial_code:<3.3};{currency:<3.3}\n".format(
        version=data.get('version') or ' ' * 1,
        date=data.get('date') or ' ' * 8,
        payer=data.get('payer') or ' ' * 1,
        provider=data.get('provider') or ' ' * 6,
        patient=data.get('patient') or ' ' * 13,
        accident_number=data.get('accident_number') or ' ' * 10,
        invoice_number=data.get('invoice_number') or ' ' * 15,
        prescription_date=data.get('prescription_date') or ' ' * 8,
        validity_date=data.get('validity_date') or 8 * ' ',
        prescribing_doctor=data.get('prescribing_doctor') or ' ' * 6,
        nurse=data.get('nurse') or ' ' * 6,
        service_code=data.get('service_code') or ' ' * 10,
        service_date=data.get('service_date') or ' ' * 8,
        end_date=data.get('end_date') or ' ' * 8,
        start_time=data.get('start_time') or ' ' * 4,
        end_time=data.get('end_time') or ' ' * 4,
        times_executed=data.get('times_executed') or ' ' * 3,
        gross_amount=data.get('gross_amount') or ' ' * 7,
        gross_amount_decimals=data.get('gross_amount_decimals') or ' ' * 2,
        net_amount=data.get('net_amount') or ' ' * 7,
        net_amount_decimals=data.get('net_amount_decimals') or ' ' * 2,
        insurance_code=data.get('insurance_code') or ' ' * 4,
        denial_code=data.get('denial_code') or ' ' * 3,
        currency=data.get('currency') or ' ' * 3
    )

    return line


def generate_file_line(data):
    for key, value in data.items():
        if isinstance(value, int):
            data[key] = str(value)
    line = "{version:<1.1}{date:<8.8}{payer:<1.1}{provider:<6.6}{patient:<13.13}{accident_number:<10.10}{invoice_number:<15.15}{prescription_date:<8.8}{validity_date:<8.8}{prescribing_doctor:<6.6}{nurse:<6.6}{service_code:<10.10}{service_date:<8.8}{end_date:<8.8}{start_time:<4.4}{end_time:<4.40}{times_executed:<3.3}{gross_amount:<7.7}{gross_amount_decimals:<2.2}{net_amount:<7.7}{net_amount_decimals:<2.2}{insurance_code:<4.4}{denial_code:<3.3}{currency:<3.3}\n".format(
        version=data.get('version') or ' ' * 1,
        date=data.get('date') or ' ' * 8,
        payer=data.get('payer') or ' ' * 1,
        provider=data.get('provider') or ' ' * 6,
        patient=data.get('patient') or ' ' * 13,
        accident_number=data.get('accident_number') or ' ' * 10,
        invoice_number=data.get('invoice_number') or ' ' * 15,
        prescription_date=data.get('prescription_date') or ' ' * 8,
        validity_date=data.get('validity_date') or 8 * ' ',
        prescribing_doctor=data.get('prescribing_doctor') or ' ' * 6,
        nurse=data.get('nurse') or ' ' * 6,
        service_code=data.get('service_code') or ' ' * 10,
        service_date=data.get('service_date') or ' ' * 8,
        end_date=data.get('end_date') or ' ' * 8,
        start_time=data.get('start_time') or ' ' * 4,
        end_time=data.get('end_time') or ' ' * 4,
        times_executed=data.get('times_executed') or ' ' * 3,
        gross_amount=data.get('gross_amount') or ' ' * 7,
        gross_amount_decimals=data.get('gross_amount_decimals') or ' ' * 2,
        net_amount=data.get('net_amount') or ' ' * 7,
        net_amount_decimals=data.get('net_amount_decimals') or ' ' * 2,
        insurance_code=data.get('insurance_code') or ' ' * 4,
        denial_code=data.get('denial_code') or ' ' * 3,
        currency=data.get('currency') or ' ' * 3
    )

    return line


def generate_flat_file(modeladmin, request, queryset):
    # action only for super user
    if not request.user.is_superuser:
        raise ValueError(_("Only super user can use this action"))
    # all invoice items must have same year and month if not then raise error
    invoices = queryset.order_by('patient')
    line = generate_all_invoice_lines(invoices)
    response = HttpResponse(line, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="flat_file.txt"'
    return response


def generate_flat_file_for_control(modeladmin, request, queryset):
    # action only for super user
    if not request.user.is_superuser:
        raise ValueError(_("Only super user can use this action"))
    if len(queryset) > 1:
        raise ValueError(_("Only one batch can be selected"))
    # all invoice items must have same year and month if not then raise error
    from .models import InvoiceItem
    invoices = InvoiceItem.objects.filter(batch=queryset[0])
    line = generate_all_invoice_lines_for_control(invoices.order_by('patient'))
    response = HttpResponse(line, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="flat_file.txt"'
    return response


def generate_all_invoice_lines_for_control(invoices, sending_date=None):
    lines = ""
    for invoice in invoices.order_by('invoice_number'):
        if invoice.invoice_date.year != invoice.invoice_date.year or invoice.invoice_date.month != invoice.invoice_date.month:
            raise ValueError(_("All invoice items must have same year and month"))
        invoice_dtls = invoice.invoice_details
        for prest in invoice.prestations.order_by('date'):
            valid_prescription_list = invoice.get_first_valid_medical_prescription(prest.date)
            if not valid_prescription_list:
                print(_("No valid prescription found for invoice item: " + str(invoice.id)))
                valid_prescription = None
            else:
                valid_prescription = valid_prescription_list.medical_prescription
            data = {
                "version": "2",
                # format date to YYYYMM00 for sending date replace days with 00 or now
                "date": format(prest.date, '%Y%m00'),
                "payer": "U",
                "provider": config.CODE_PRESTATAIRE,
                # patient cns code only 11 digits
                "patient": invoice.patient.code_sn.replace(" ", "")[:13],
                # accident number if exists or empty 10 spaces
                "accident_number": invoice.accident_id if invoice.accident_id else '0' * 10,
                # invoice number on 15 digits completed with 0
                "invoice_number": invoice.invoice_number.ljust(15, '0'),
                "prescription_date": format(valid_prescription.date,'%Y%m%d') if valid_prescription else None,
                "validity_date": format(valid_prescription.end_date,'%Y%m%d') if valid_prescription else None,
                "prescribing_doctor": valid_prescription.prescriptor.provider_code.replace("-", "").replace(" ", "").strip() if valid_prescription else None,
                "nurse": invoice_dtls.provider_code.replace("-", "").replace(" ",
                                                                             "").strip() if prest.carecode.is_package else prest.employee.provider_code.replace(
                    "-", "").replace(" ", "").strip(),
                "service_code": prest.carecode.code,
                "service_date": format(prest.date, '%Y%m%d'),
                "end_date": format(prest.date, '%Y%m%d'),
                "start_time": format(prest.date.astimezone(ZoneInfo("Europe/Luxembourg")), '%H%M'),
                # add one minute to end time to avoid 0000
                "end_time": format(prest.date.astimezone(ZoneInfo("Europe/Luxembourg")), '%H%M'),
                "times_executed": "001",
                # gross amount with int part only
                "gross_amount": str(int(prest.carecode.gross_amount(prest.date))).zfill(7),
                "gross_amount_decimals": str(int((prest.carecode.gross_amount(prest.date) - int(
                    prest.carecode.gross_amount(prest.date))) * 100)).zfill(2),
                "net_amount": str(int(
                    prest.carecode.net_amount(prest.date, False,
                                              invoice.patient.participation_statutaire and invoice.patient.age > 18))).zfill(
                    7),
                "net_amount_decimals": str(int((prest.carecode.net_amount(prest.date, False,
                                                                          invoice.patient.participation_statutaire) - int(
                    prest.carecode.net_amount(prest.date, False,
                                              invoice.patient.participation_statutaire))) * 100)).zfill(2),
                "insurance_code": None,
                "denial_code": None,
                "currency": "EUR"
            }
            # print(data)
            lines += generate_file_line_for_calculation_control(data)
    if lines.endswith("\n"):
        lines = lines[:-1]
    return lines


def generate_all_invoice_lines(invoices, invoice_batch_date=None, batch_type=None):
    lines = ""
    for invoice in invoices.annotate(
            is_under_dependence_insurance_order=Case(
                When(patient__is_under_dependence_insurance=False, then=Value(0)),
                When(patient__is_under_dependence_insurance=True, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )).order_by('is_under_dependence_insurance_order', 'patient_id'):
        invoice_dtls = invoice.invoice_details
        if invoice.invoice_date.year != invoice.invoice_date.year or invoice.invoice_date.month != invoice.invoice_date.month:
            raise ValueError(_("All invoice items must have same year and month"))
        for prest in invoice.prestations.order_by('date'):
            valid_prescription_list = invoice.get_first_valid_medical_prescription(prest.date)
            if not valid_prescription_list:
                print(_("No valid prescription found for invoice item: " + str(invoice.id)))
                valid_prescription = None
            else:
                valid_prescription = valid_prescription_list.medical_prescription
            data = {
                "version": "2",
                # format date to YYYYMM00 for sending date replace days with 00
                "date": format(invoice_batch_date, '%Y%m00'),
                "payer": "U",
                "provider": config.CODE_PRESTATAIRE,
                # patient cns code only 11 digits
                "patient": invoice.patient.code_sn.replace(" ", "")[:13],
                # accident number if exists or empty 10 spaces
                "accident_number": invoice.accident_id if invoice.accident_id else '0' * 10,
                # invoice number on 15 digits completed with 0
                "invoice_number": invoice.invoice_number.ljust(15, '0'),
                "prescription_date": format(valid_prescription.date,'%Y%m%d') if valid_prescription else None,
                "validity_date": format(valid_prescription.end_date, '%Y%m%d') if valid_prescription else None,
                "prescribing_doctor": valid_prescription.prescriptor.provider_code.replace("-", "").replace(" ", "").strip() if valid_prescription else None,
                # "nurse": invoice_dtls.provider_code.replace("-", "").replace(" ",
                #                                                              "").strip() if BatchTypeChoices.CNS_PAL == batch_type else prest.employee.provider_code.replace(
                #     "-", "").replace(" ", "").strip(),
                "nurse": invoice_dtls.provider_code.replace("-", "").replace(" ",
                                                                             "").strip() if prest.carecode.is_package else prest.employee.provider_code.replace(
                    "-", "").replace(" ", "").strip(),
                "service_code": prest.carecode.code,
                "service_date": format(prest.date, '%Y%m%d'),
                "end_date": format(prest.date, '%Y%m%d'),
                "start_time": format(prest.date.astimezone(ZoneInfo("Europe/Luxembourg")), '%H%M'),
                # add one minute to end time to avoid 0000
                "end_time": format(prest.date.astimezone(ZoneInfo("Europe/Luxembourg")), '%H%M'),
                "times_executed": "001",
                # gross amount with int part only
                "gross_amount": str(int(prest.carecode.gross_amount(prest.date))).zfill(7),
                "gross_amount_decimals": str(int((prest.carecode.gross_amount(prest.date) - int(
                    prest.carecode.gross_amount(prest.date))) * 100)).zfill(2),
                "net_amount": str(int(
                    prest.carecode.net_amount(prest.date, False,
                                              invoice.patient.participation_statutaire and invoice.patient.age > 18))).zfill(
                    7),
                "net_amount_decimals": str(int((prest.carecode.net_amount(prest.date, False,
                                                                          invoice.patient.participation_statutaire and invoice.patient.age > 18) - int(
                    prest.carecode.net_amount(prest.date, False,
                                              invoice.patient.participation_statutaire and invoice.patient.age > 18))) * 100)).zfill(
                    2),
                "insurance_code": None,
                "denial_code": None,
                "currency": "EUR"
            }
            # print(data)
            lines += generate_file_line(data)
    if lines.endswith("\n"):
        lines = lines[:-1]
    return lines
