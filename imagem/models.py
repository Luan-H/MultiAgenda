from django.db import models
from cliente.models import Cliente

class Imagem(models.Model):
    id_imagem = models.AutoField(primary_key=True)
    dt_criacao = models.DateField(auto_now_add=True)
    caminho = models.CharField(max_length=255)
    id_cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='id_cliente')

    class Meta:
        db_table = 'imagem'