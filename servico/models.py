from django.db import models
from empresa.models import Empresa

class Servico(models.Model):
    id_servico = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    vlr_servico = models.DecimalField(max_digits=7, decimal_places=2)
    duracao_em_min = models.IntegerField()
    id_empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, db_column='id_empresa')

    class Meta:
        db_table = 'servico'