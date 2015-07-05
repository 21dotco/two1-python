# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BlackjackGame',
            fields=[
                ('identifier', models.CharField(max_length=512, primary_key=True, serialize=False)),
                ('blob', models.CharField(max_length=8096)),
            ],
        ),
    ]
