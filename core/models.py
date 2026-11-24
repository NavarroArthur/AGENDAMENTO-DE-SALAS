from django.conf import settings
from django.db import models


class Organizacao(models.Model):
    nome = models.CharField(max_length=120)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'organização'
        verbose_name_plural = 'organizações'

    def __str__(self):
        return self.nome


class Perfil(models.Model):
    ADMIN = 'admin'
    OPERADOR = 'operador'
    PAPEIS = [
        (ADMIN, 'Administrador'),
        (OPERADOR, 'Operador'),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.PROTECT,
        related_name='perfis',
    )
    papel = models.CharField(max_length=20, choices=PAPEIS, default=OPERADOR)

    class Meta:
        ordering = ['organizacao__nome', 'usuario__username']
        verbose_name = 'perfil'
        verbose_name_plural = 'perfis'

    def __str__(self):
        return f'{self.usuario} — {self.get_papel_display()} ({self.organizacao})'

    @property
    def eh_admin(self):
        return self.papel == self.ADMIN


class DaOrganizacao(models.Model):
    organizacao = models.ForeignKey(
        'core.Organizacao',
        on_delete=models.PROTECT,
        related_name='%(app_label)s_%(class)s_registros',
    )

    class Meta:
        abstract = True
