# Generated by Django 5.1 on 2025-02-13 12:26

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('contact_name', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('contact_email', models.EmailField(blank=True, default='', max_length=254, null=True)),
                ('phone_number', models.CharField(blank=True, default='', max_length=15, null=True)),
                ('address', models.TextField(blank=True, default='', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('supplier_code', models.CharField(blank=True, default='', max_length=50, null=True, unique=True)),
                ('payment_terms', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('notes', models.TextField(blank=True, default='', null=True)),
            ],
            options={
                'db_table': 'suppliers',
            },
        ),
    ]
