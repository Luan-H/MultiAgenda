from django.db import models

class Empresa(models.Model):
    id_empresa = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    dt_criacao = models.DateField()
    tipo_empresa = models.CharField(max_length=100)

    class Meta:
        db_table = 'empresa'