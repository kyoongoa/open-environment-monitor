from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_alter_airqualitydata_options_and_more")]
    operations = [
        migrations.CreateModel(
            name="EnvironmentObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("city", models.CharField(max_length=128)), ("observed_at", models.DateTimeField()), ("collected_at", models.DateTimeField(auto_now_add=True)),
                ("source", models.CharField(max_length=64)), ("source_url", models.URLField(blank=True)), ("aqi", models.IntegerField(blank=True, null=True)),
                ("quality", models.CharField(blank=True, max_length=64)), ("provider_aqi_category", models.IntegerField(blank=True, null=True)),
                ("pm25", models.FloatField(blank=True, null=True)), ("pm10", models.FloatField(blank=True, null=True)), ("so2", models.FloatField(blank=True, null=True)),
                ("no2", models.FloatField(blank=True, null=True)), ("co", models.FloatField(blank=True, null=True)), ("o3", models.FloatField(blank=True, null=True)),
                ("temperature", models.FloatField(blank=True, null=True)), ("humidity", models.FloatField(blank=True, null=True)), ("wind_speed", models.FloatField(blank=True, null=True)),
                ("weather", models.CharField(blank=True, max_length=128, null=True)), ("latitude", models.FloatField(blank=True, null=True)), ("longitude", models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.AddConstraint(model_name="environmentobservation", constraint=models.UniqueConstraint(fields=("city", "observed_at"), name="unique_environment_observation")),
        migrations.AddIndex(model_name="environmentobservation", index=models.Index(fields=["city", "-observed_at"], name="accounts_en_city_b71b68_idx")),
    ]
