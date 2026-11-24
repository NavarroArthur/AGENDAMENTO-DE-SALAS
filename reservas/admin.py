from django.contrib import admin
from django.contrib.auth import get_user_model

from core.models import Perfil
from .models import Recorrencia, Reserva, Recurso, Sala


class AdminDaOrganizacaoMixin:
    """Escopa o Django Admin à organização do administrador autenticado."""

    def _perfil(self, request):
        return getattr(request.user, 'perfil', None)

    def _pode_administrar(self, request):
        perfil = self._perfil(request)
        return request.user.is_superuser or bool(perfil and perfil.papel == Perfil.ADMIN)

    def has_module_permission(self, request):
        return self._pode_administrar(request)

    def has_view_permission(self, request, obj=None):
        return self._pode_administrar(request)

    def has_add_permission(self, request):
        return self._pode_administrar(request)

    def has_change_permission(self, request, obj=None):
        return self._pode_administrar(request)

    def has_delete_permission(self, request, obj=None):
        return self._pode_administrar(request)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        perfil = self._perfil(request)
        if request.user.is_superuser:
            return queryset
        if not perfil or perfil.papel != Perfil.ADMIN:
            return queryset.none()
        return queryset.filter(organizacao=perfil.organizacao)

    def get_form(self, request, obj=None, **kwargs):
        base_form = super().get_form(request, obj, **kwargs)
        if not any(field.name == 'nome' for field in self.model._meta.fields):
            return base_form

        perfil = self._perfil(request)
        organizacao_inicial = (
            obj.organizacao if obj else
            perfil.organizacao if perfil and not request.user.is_superuser else None
        )
        model = self.model

        class FormComunicidadePorOrganizacao(base_form):
            def clean(self):
                cleaned = super().clean()
                nome = cleaned.get('nome')
                organizacao = organizacao_inicial or cleaned.get('organizacao')
                if nome and organizacao:
                    duplicado = model.objects.filter(
                        organizacao=organizacao,
                        nome__iexact=nome,
                    )
                    if obj:
                        duplicado = duplicado.exclude(pk=obj.pk)
                    if duplicado.exists():
                        self.add_error('nome', 'Já existe um registro com esse nome na organização.')
                return cleaned

        return FormComunicidadePorOrganizacao

    def get_exclude(self, request, obj=None):
        excluded = list(super().get_exclude(request, obj) or [])
        if not request.user.is_superuser and 'organizacao' not in excluded:
            excluded.append('organizacao')
        return excluded

    def save_model(self, request, obj, form, change):
        perfil = self._perfil(request)
        if not request.user.is_superuser and perfil:
            obj.organizacao = perfil.organizacao
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        perfil = self._perfil(request)
        if not request.user.is_superuser and perfil:
            if db_field.name == 'sala':
                kwargs['queryset'] = Sala.objects.filter(organizacao=perfil.organizacao)
            elif db_field.name == 'recorrencia':
                kwargs['queryset'] = Recorrencia.objects.filter(organizacao=perfil.organizacao)
            elif db_field.name == 'criado_por':
                User = get_user_model()
                kwargs['queryset'] = User.objects.filter(perfil__organizacao=perfil.organizacao)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        perfil = self._perfil(request)
        if not request.user.is_superuser and perfil and db_field.name == 'recursos':
            kwargs['queryset'] = Recurso.objects.filter(organizacao=perfil.organizacao)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(Recurso)
class RecursoAdmin(AdminDaOrganizacaoMixin, admin.ModelAdmin):
    list_display = ('nome', 'organizacao')
    list_filter = ('organizacao',)
    search_fields = ('nome',)


@admin.register(Sala)
class SalaAdmin(AdminDaOrganizacaoMixin, admin.ModelAdmin):
    list_display = ('nome', 'capacidade', 'localizacao', 'organizacao')
    list_filter = ('organizacao',)
    search_fields = ('nome', 'localizacao')
    filter_horizontal = ('recursos',)


@admin.register(Recorrencia)
class RecorrenciaAdmin(AdminDaOrganizacaoMixin, admin.ModelAdmin):
    list_display = ('frequencia', 'intervalo', 'data_inicio', 'data_fim', 'organizacao')
    list_filter = ('organizacao', 'frequencia')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Reserva)
class ReservaAdmin(AdminDaOrganizacaoMixin, admin.ModelAdmin):
    list_display = ('titulo', 'sala', 'data', 'hora_inicio', 'hora_fim', 'organizacao')
    list_filter = ('organizacao', 'data', 'sala')
    search_fields = ('titulo', 'responsavel', 'sala__nome')
    date_hierarchy = 'data'
    readonly_fields = ('criado_por',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
