# Long contact strings (e.g. two numbers) for employer/worker profiles.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_worker_portfolio_item"),
    ]

    operations = [
        migrations.AlterField(
            model_name="employerprofile",
            name="contact_number",
            field=models.CharField(max_length=120),
        ),
        migrations.AlterField(
            model_name="workerprofile",
            name="contact_number",
            field=models.CharField(max_length=120),
        ),
    ]
