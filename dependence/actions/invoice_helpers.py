from dependence.invoicing import LongTermCareInvoiceFile
from invoices.models import SubContractor


def generate_aev_invoice_for_pinto(all_done_or_valid_events):
    # This function is a stub, and should be implemented by the student.
    # first get or create the invoice for the client
    pinto_patient = all_done_or_valid_events[0].patient
    subcontractor = SubContractor.objects.get(id=12)

    longterm_invoice_file = LongTermCareInvoiceFile.objects.get_or_create(patient=pinto_patient,
                                                  invoice_start_period=all_done_or_valid_events[0].day,
                                                  invoice_end_period=all_done_or_valid_events[len(all_done_or_valid_events) - 1].day)

    days_bizarre = []
    for event in all_done_or_valid_events:
        if event.duration_in_hours() > 1:
            # probably a AMDGI invoice item
            longterm_invoice_file[0].add_item_with_code(code="AMDGI", date_of_care=event.day,
                                                        quantity=event.duration_in_hours() * 2,
                                                        subcontractor=subcontractor)
        else:
            if event.day.weekday() == 0 or event.day.weekday() == 4:
                longterm_invoice_file[0].add_line_forfait(forfait_number="06", date_of_care=event.day,
                                                          subcontractor=subcontractor)
            # if event day is Saturday or Sunday forfait 7
            elif event.day.weekday() == 5 or event.day.weekday() == 6:
                longterm_invoice_file[0].add_line_forfait(forfait_number="07", date_of_care=event.day,
                                                          subcontractor=subcontractor)
            else:
                days_bizarre.append(event.day)

    return longterm_invoice_file[0], days_bizarre
