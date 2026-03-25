from django.db import migrations, models
from django.db.models import F


def backfill_hired_at(apps, schema_editor):
    Application = apps.get_model('jobs', 'Application')
    Application.objects.filter(
        status__in=('hired', 'completed'),
        hired_at__isnull=True,
    ).update(hired_at=F('updated_at'))


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('jobs', '0003_alter_application_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='hired_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_hired_at, noop_reverse),
    ]
