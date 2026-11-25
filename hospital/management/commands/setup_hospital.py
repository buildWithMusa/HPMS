from django.core.management.base import BaseCommand

from hospital.models import Department, ServiceArea


class Command(BaseCommand):

    help = "Create the initial HPMS hospital departments and service areas"

    DEPARTMENTS = [
        ("PHARM", "Pharmacy", "Hospital pharmacy operations."),
        ("MED", "Medical Services", "Clinical medical services."),
        ("NURS", "Nursing", "Hospital nursing services."),
        ("PROC", "Procurement", "Purchasing and supplier management."),
        ("FIN", "Finance", "Financial management."),
        ("ADMIN", "Administration", "Hospital administration."),
    ]

    SERVICE_AREAS = [
        ("OPD", "Outpatient Department", ServiceArea.AreaType.OUTPATIENT),
        ("IPD", "Inpatient Department", ServiceArea.AreaType.INPATIENT),
        ("MAT", "Maternity", ServiceArea.AreaType.MATERNITY),
        ("ER", "Emergency", ServiceArea.AreaType.EMERGENCY),
        ("MH", "Mental Health", ServiceArea.AreaType.MENTAL_HEALTH),
        ("PEDS", "Children's Services", ServiceArea.AreaType.CHILDREN),
    ]

    def handle(self, *args, **options):

        self.stdout.write("Setting up HPMS hospital structure...")

        for code, name, description in self.DEPARTMENTS:

            department, created = Department.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description,
                }
            )

            status = "Created" if created else "Already exists"
            self.stdout.write(f"{status}: {department.name}")

        medical_department = Department.objects.get(code="MED")

        for code, name, area_type in self.SERVICE_AREAS:

            service_area, created = ServiceArea.objects.get_or_create(
                department=medical_department,
                code=code,
                defaults={
                    "name": name,
                    "area_type": area_type,
                }
            )

            status = "Created" if created else "Already exists"
            self.stdout.write(f"{status}: {service_area.name}")

        self.stdout.write(
            self.style.SUCCESS(
                "Hospital setup completed successfully."
            )
        )