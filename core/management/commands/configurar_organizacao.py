from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Organizacao, Perfil


class Command(BaseCommand):
    help = 'Cria uma organização e associa a ela um superusuário como administrador.'

    def add_arguments(self, parser):
        parser.add_argument('--nome', required=True, help='Nome da organização inicial.')
        parser.add_argument('--usuario', required=True, help='Username do superusuário.')

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        try:
            usuario = User.objects.get(username=options['usuario'])
        except User.DoesNotExist as exc:
            raise CommandError('Usuário não encontrado; crie o superusuário primeiro.') from exc

        if not usuario.is_superuser:
            raise CommandError('A conta indicada precisa ser superusuária.')

        organizacao = Organizacao.objects.filter(nome=options['nome']).first()
        criada = False
        if organizacao is None:
            organizacao = Organizacao.objects.filter(nome='Organização padrão').first()
            if organizacao is not None:
                organizacao.nome = options['nome']
                organizacao.save(update_fields=['nome'])
            else:
                organizacao = Organizacao.objects.create(nome=options['nome'])
                criada = True
        perfil, perfil_criado = Perfil.objects.get_or_create(
            usuario=usuario,
            defaults={'organizacao': organizacao, 'papel': Perfil.ADMIN},
        )
        if not perfil_criado and perfil.organizacao_id != organizacao.pk:
            raise CommandError('O usuário já tem perfil em outra organização.')
        if not perfil_criado and perfil.papel != Perfil.ADMIN:
            perfil.papel = Perfil.ADMIN
            perfil.save(update_fields=['papel'])

        acao = 'criada' if criada else 'já existia'
        self.stdout.write(self.style.SUCCESS(
            f'Organização {acao}; {usuario.username} é administrador de {organizacao.nome}.'
        ))
