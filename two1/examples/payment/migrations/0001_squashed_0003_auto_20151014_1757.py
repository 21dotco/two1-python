# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    replaces = [('payment', '0001_initial'), ('payment', '0002_channel_deposit_tx_id'), ('payment', '0003_auto_20151014_1757')]

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('base58_string', models.CharField(max_length=256)),
            ],
        ),
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('expires_at', models.DateTimeField()),
                ('status', models.CharField(default='op', max_length=2, choices=[('op', 'opening'), ('cf', 'confirming'), ('rd', 'ready'), ('ci', 'closing'), ('pa', 'paying'), ('re', 'refunding'), ('cl', 'closed')])),
                ('customer', models.ForeignKey(related_name='c_channels', to='payment.Address')),
                ('merchant', models.ForeignKey(related_name='m_channels', to='payment.Address')),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('transaction_id', models.CharField(max_length=256)),
                ('transaction_hex', models.CharField(max_length=1024)),
                ('amount', models.FloatField()),
                ('category', models.CharField(max_length=2, choices=[('dp', 'deposit'), ('rf', 'refund'), ('py', 'payment'), ('lp', 'last_payment')])),
                ('is_broadcast', models.BooleanField(default=False)),
                ('is_confirmed', models.BooleanField(default=False)),
                ('is_redeemed', models.BooleanField(default=False)),
                ('channel', models.ForeignKey(related_name='transactions', to='payment.Channel')),
            ],
        ),
        migrations.AddField(
            model_name='channel',
            name='deposit_tx_id',
            field=models.CharField(default='oops', max_length=256),
            preserve_default=False,
        ),
        migrations.RenameModel(
            old_name='Address',
            new_name='PublicKey',
        ),
        migrations.RenameField(
            model_name='publickey',
            old_name='base58_string',
            new_name='hex_string',
        ),
    ]
