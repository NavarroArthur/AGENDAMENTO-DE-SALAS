from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def preencher_organizacao_padrao(apps, schema_editor):
    banco = schema_editor.connection.alias
    Organizacao = apps.get_model('core', 'Organizacao')
    organizacao, _ = Organizacao.objects.using(banco).get_or_create(
        nome='Organização padrão'
    )

    for nome_model in ('Recurso', 'Sala', 'Recorrencia', 'Reserva'):
        Model = apps.get_model('reservas', nome_model)
        Model.objects.using(banco).filter(organizacao__isnull=True).update(
            organizacao_id=organizacao.pk
        )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
        ('reservas', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='recurso',
            name='nome',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='sala',
            name='nome',
            field=models.CharField(max_length=100),
        ),
        migrations.AddField(
            model_name='recurso',
            name='organizacao',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='reservas_recurso_registros',
                to='core.organizacao',
            ),
        ),
        migrations.AddField(
            model_name='sala',
            name='organizacao',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='reservas_sala_registros',
                to='core.organizacao',
            ),
        ),
        migrations.AddField(
            model_name='recorrencia',
            name='organizacao',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='reservas_recorrencia_registros',
                to='core.organizacao',
            ),
        ),
        migrations.AddField(
            model_name='reserva',
            name='organizacao',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='reservas_reserva_registros',
                to='core.organizacao',
            ),
        ),
        migrations.AddField(
            model_name='recorrencia',
            name='criado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='series_reservas_criadas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='reserva',
            name='criado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reservas_criadas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(preencher_organizacao_padrao, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='recurso',
            name='organizacao',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='reservas_recurso_registros',
                to='core.organizacao',
            ),
        ),
        migrations.AlterField(
            model_name='sala',
            name='organizacao',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='reservas_sala_registros',
                to='core.organizacao',
            ),
        ),
        migrations.AlterField(
            model_name='recorrencia',
            name='organizacao',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='reservas_recorrencia_registros',
                to='core.organizacao',
            ),
        ),
        migrations.AlterField(
            model_name='reserva',
            name='organizacao',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='reservas_reserva_registros',
                to='core.organizacao',
            ),
        ),
        migrations.AddConstraint(
            model_name='recurso',
            constraint=models.UniqueConstraint(
                fields=('organizacao', 'nome'), name='uniq_recurso_org_nome'
            ),
        ),
        migrations.AddConstraint(
            model_name='sala',
            constraint=models.UniqueConstraint(
                fields=('organizacao', 'nome'), name='uniq_sala_org_nome'
            ),
        ),
    ]
