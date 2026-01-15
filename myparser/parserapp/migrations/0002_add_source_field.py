# Generated manually to fix model mismatch

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parserapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='vacancy',
            name='source',
            field=models.CharField(default='HH.ru', max_length=50, verbose_name='Источник'),
        ),
        migrations.AlterField(
            model_name='vacancy',
            name='description',
            field=models.TextField(blank=True, default='', verbose_name='Описание'),
        ),
    ]
