# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BitcoinToken',
            fields=[
                ('key', models.CharField(max_length=40, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('balance', models.IntegerField()),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL, related_name='auth_token')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
