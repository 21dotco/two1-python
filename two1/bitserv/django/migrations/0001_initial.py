# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BlockchainTransaction',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('txid', models.TextField()),
                ('amount', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='PaymentChannel',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('deposit_txid', models.TextField(unique=True)),
                ('state', models.TextField()),
                ('deposit_tx', models.TextField(blank=True, null=True)),
                ('payment_tx', models.TextField(blank=True, null=True)),
                ('merchant_pubkey', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.IntegerField()),
                ('amount', models.IntegerField(blank=True, null=True)),
                ('last_payment_amount', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='PaymentChannelSpend',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('payment_txid', models.TextField(unique=True)),
                ('payment_tx', models.TextField()),
                ('amount', models.IntegerField()),
                ('is_redeemed', models.BooleanField(default=False)),
                ('deposit_txid', models.TextField()),
            ],
        ),
    ]
