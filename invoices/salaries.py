import os
from email.mime.application import MIMEApplication

from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_rq import job

from invoices import settings
from invoices.employee import Employee
from invoices.helpers.pdf import extract_individual_paylip_pdf


#from scripts.extract_salaries_from_pdf import read_pdf


class EmployeesMonthlyPayslipFile(models.Model):
    class Meta:
        verbose_name = _("Fichier de bulletin de salaire mensuel")
        verbose_name_plural = _("Fichiers de bulletin de salaire mensuel")

    year = models.IntegerField(_("Année"))
    month = models.IntegerField(_("Mois"))
    file = models.FileField(_("Fichier"), upload_to='payslips/')
    created_at = models.DateTimeField(_("Date de création"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Dernière mise à jour"), auto_now=True)

    def __str__(self):
        return f"Salaires {self.year} - {self.month}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Open the file from the FileField
        with self.file.open('rb') as file_obj:
            payslips = extract_individual_paylip_pdf(file_obj)

        # Process the extracted payslips asynchronously if not local environment
        if os.environ.get('LOCAL_ENV', None):
            self.async_process_extracted_payslip(payslips)
        else:
            self.async_process_extracted_payslip.delay(payslips)
    @job('default',timeout=600)
    def async_process_extracted_payslip(self, payslips):
        for name, pdf_data in payslips.items():
            print("Processing payslip for %s" % name)
            employee = Employee.objects.get(user__last_name__istartswith=name.split()[0])
            if not employee:
                raise ValueError(f"Employee with last name {name.split()[0]} not found")
            payslip = EmployeePaySlip(employee=employee, year=self.year, month=self.month)

            # Create a ContentFile object from the PDF data
            pdf_file = ContentFile(pdf_data, name=f"{self.year}_{self.month}_{name.replace(' ', '_')}_payslip.pdf")

            # Save the PDF file to the file field of the EmployeePaySlip object
            payslip.file.save(pdf_file.name, pdf_file)

            payslip.save()


class EmployeePaySlip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    file = models.FileField(upload_to='payslip_per_employee/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee} - {self.year} - {self.month}"

    def send_payslip_by_email_in_attachment(self):
        # Send the payslip by email as an attachment
        email_address = self.employee.user.email
        subject = f"Bulletin de salaire {self.year} - {self.month}"
        message = "Veuillez trouver ci-joint votre bulletin de salaire. Si ce message vous est parvenu par erreur, veuillez le supprimer et nous en informer, merci. Cordialement."
        # Configure S3
        #s3 = boto3.client('s3')
        #load_dotenv(verbose=True)
        import os
        bucket_name = os.environ['AWS_STORAGE_BUCKET_NAME']
        key = self.file.name  # The file's path in S3
        # Get the file content from S3
        #response = s3.get_object(Bucket=bucket_name, Key=key)
        file_content = self.file.read()
        if not self.employee.personal_email:
            emails = [email_address]
        else:
            emails = [email_address, self.employee.personal_email]
        mail = EmailMessage(subject, message, settings.EMAIL_HOST_USER, emails)
        part = MIMEApplication(file_content, 'pdf')
        part.add_header('Content-Disposition', 'attachment',
                        filename= f"{self.year}_{self.month}_{self.employee.user.last_name}_{self.employee.user.first_name}_bulletin_de_salaire.pdf")
        mail.attach(part)
        # Open the file from the FileField and attach it to the email

        try:
            status = mail.send(fail_silently=False)
            print("Email sent successfully to %s" % email_address)
            return status
        except Exception as e:
            print("Error sending email to %s" % email_address)
            return False
