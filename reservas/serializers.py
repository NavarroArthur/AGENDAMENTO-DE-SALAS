from rest_framework import serializers

from .models import Recorrencia, Reserva, Recurso, Sala
from .services import ConflitosDeAgenda, criar_reserva


class RecursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recurso
        fields = ['id', 'nome', 'descricao']

    def validate_nome(self, value):
        organizacao = self.context['request'].user.perfil.organizacao
        qs = Recurso.objects.filter(organizacao=organizacao, nome__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Já existe um recurso com esse nome na organização.')
        return value


class SalaSerializer(serializers.ModelSerializer):
    recursos = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Recurso.objects.none(),
        required=False,
    )

    class Meta:
        model = Sala
        fields = ['id', 'nome', 'capacidade', 'localizacao', 'recursos']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated and hasattr(request.user, 'perfil'):
            self.fields['recursos'].child_relation.queryset = Recurso.objects.filter(
                organizacao=request.user.perfil.organizacao
            )

    def validate_nome(self, value):
        organizacao = self.context['request'].user.perfil.organizacao
        qs = Sala.objects.filter(organizacao=organizacao, nome__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Já existe uma sala com esse nome na organização.')
        return value

    def create(self, validated_data):
        recursos = validated_data.pop('recursos', [])
        organizacao = self.context['request'].user.perfil.organizacao
        sala = Sala.objects.create(organizacao=organizacao, **validated_data)
        sala.recursos.set(recursos)
        return sala

    def update(self, instance, validated_data):
        recursos = validated_data.pop('recursos', None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if recursos is not None:
            instance.recursos.set(recursos)
        return instance


class ReservaSerializer(serializers.ModelSerializer):
    sala = serializers.PrimaryKeyRelatedField(
        queryset=Sala.objects.none(),
    )
    recorrencia = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Reserva
        fields = [
            'id', 'sala', 'titulo', 'responsavel', 'data',
            'hora_inicio', 'hora_fim', 'observacoes', 'recorrencia',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated and hasattr(request.user, 'perfil'):
            self.fields['sala'].queryset = Sala.objects.filter(
                organizacao=request.user.perfil.organizacao
            )

    def validate(self, attrs):
        sala = attrs.get('sala', getattr(self.instance, 'sala', None))
        data = attrs.get('data', getattr(self.instance, 'data', None))
        inicio = attrs.get('hora_inicio', getattr(self.instance, 'hora_inicio', None))
        fim = attrs.get('hora_fim', getattr(self.instance, 'hora_fim', None))
        if inicio and fim and inicio >= fim:
            raise serializers.ValidationError({'hora_fim': 'Precisa ser posterior ao início.'})
        if sala and data and inicio and fim:
            if sala.organizacao_id != self.context['request'].user.perfil.organizacao_id:
                raise serializers.ValidationError({'sala': 'Escolha uma sala da sua organização.'})
            conflitos = sala.reservas.filter(
                organizacao=sala.organizacao,
                data=data,
                hora_inicio__lt=fim,
                hora_fim__gt=inicio,
            )
            if self.instance:
                conflitos = conflitos.exclude(pk=self.instance.pk)
            if conflitos.exists():
                raise serializers.ValidationError({
                    'non_field_errors': ['A sala já está reservada nesse horário.']
                })
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        reserva = Reserva(
            organizacao=request.user.perfil.organizacao,
            criado_por=request.user,
            **validated_data,
        )
        try:
            return criar_reserva(reserva)
        except ConflitosDeAgenda as exc:
            raise serializers.ValidationError({
                'non_field_errors': ['A sala foi reservada por outra solicitação.']
            }) from exc

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        try:
            return criar_reserva(instance)
        except ConflitosDeAgenda as exc:
            raise serializers.ValidationError({
                'non_field_errors': ['A sala foi reservada por outra solicitação.']
            }) from exc


class RecorrenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recorrencia
        fields = ['id', 'frequencia', 'intervalo', 'data_inicio', 'data_fim']
