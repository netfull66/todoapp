# Generated by Django 5.1.2 on 2024-12-22 10:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('welcome', '0008_customuser_subscription_end_date_subscriptionorder'),
    ]

    operations = [
        migrations.AddField(
            model_name='invitation',
            name='role',
            field=models.CharField(choices=[('team_member', 'Team Member'), ('product_owner', 'Product Owner')], default='team_member', max_length=20),
        ),
    ]