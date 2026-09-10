from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_environmentobservation")]

    operations = [
        migrations.DeleteModel(name="AirQualityData"),
        migrations.DeleteModel(name="WeatherData"),
    ]
