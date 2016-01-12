# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bitcoin_auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentChannel',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, verbose_name='ID', serialize=False)),
                ('deposit_txid', models.TextField(unique=True)),
                ('state', models.TextField()),
                ('deposit_tx', models.TextField(null=True, blank=True)),
                ('payment_tx', models.TextField(null=True, blank=True)),
                ('refund_tx', models.TextField()),
                ('merchant_pubkey', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.IntegerField()),
                ('amount', models.IntegerField(null=True, blank=True)),
                ('last_payment_amount', models.IntegerField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='PaymentChannelSpend',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, verbose_name='ID', serialize=False)),
                ('payment_txid', models.TextField(unique=True)),
                ('payment_tx', models.TextField()),
                ('amount', models.IntegerField()),
                ('is_redeemed', models.BooleanField(default=False)),
                ('deposit_txid', models.TextField()),
            ],
        ),
    ]
