# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bitcoin_auth', '0002_paymentchannel_paymentchannelspend'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentchannel',
            name='refund_tx',
        ),
        migrations.AlterField(
            model_name='paymentchannel',
            name='expires_at',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='paymentchannel',
            name='last_payment_amount',
            field=models.IntegerField(default=0),
        ),
    ]
