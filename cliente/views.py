from django.shortcuts import render, redirect
from django.db import connection
from django.contrib.auth.hashers import make_password

def gerenciar_clientes_view(request, id_edit=None):
    login_sessao = request.session.get('usuario_login')
    perfil_sessao = request.session.get('usuario_perfil')
    
    if not login_sessao:
        return redirect('login')
    
    cliente_para_editar = None

    if id_edit:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id_cliente, nome, login, telefone, observacoes FROM cliente WHERE id_cliente = %s", [id_edit])
            row = cursor.fetchone()
            if row:
                cliente_para_editar = {
                    'id': row[0], 
                    'nome': row[1], 
                    'login': row[2], 
                    'telefone': row[3], 
                    'observacoes': row[4]
                }

    if request.method == "POST":
        nome = request.POST.get('nome')
        login_cliente = request.POST.get('login')
        telefone = request.POST.get('telefone')
        observacoes = request.POST.get('observacoes')
        senha_crua = request.POST.get('senha')
        
        with connection.cursor() as cursor:
            if id_edit: 
                # Se a senha foi preenchida na edição, atualiza ela também. Se não, mantém a antiga.
                if senha_crua:
                    senha_hash = make_password(senha_crua)
                    cursor.execute("""
                        UPDATE cliente 
                        SET nome=%s, login=%s, telefone=%s, observacoes=%s, senha=%s 
                        WHERE id_cliente=%s
                    """, [nome, login_cliente, telefone, observacoes, senha_hash, id_edit])
                else:
                    cursor.execute("""
                        UPDATE cliente 
                        SET nome=%s, login=%s, telefone=%s, observacoes=%s 
                        WHERE id_cliente=%s
                    """, [nome, login_cliente, telefone, observacoes, id_edit])
            else: 
                senha_hash = make_password(senha_crua) if senha_crua else ''
                cursor.execute("SELECT id_empresa FROM usuario WHERE login = %s", [login_sessao])
                id_empresa = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT INTO cliente (nome, login, senha, telefone, observacoes, ativo, id_empresa) 
                    VALUES (%s, %s, %s, %s, %s, '1', %s)
                """, [nome, login_cliente, senha_hash, telefone, observacoes, id_empresa])
                
        return redirect('gerenciar_clientes')

    termo_busca = request.GET.get('q', '') 

    with connection.cursor() as cursor:
        if termo_busca:
            query_list = """
                SELECT id_cliente AS id, nome, login, telefone FROM cliente 
                WHERE id_empresa = (SELECT id_empresa FROM usuario WHERE login = %s)
                AND ativo = '1'
                AND (nome ILIKE %s OR login ILIKE %s OR telefone ILIKE %s)
                ORDER BY nome
            """
            param = f"%{termo_busca}%"
            cursor.execute(query_list, [login_sessao, param, param, param])
        else:
            query_list = """
                SELECT id_cliente AS id, nome, login, telefone FROM cliente 
                WHERE id_empresa = (SELECT id_empresa FROM usuario WHERE login = %s)
                AND ativo = '1'
                ORDER BY nome
            """
            cursor.execute(query_list, [login_sessao])
            
        colunas = [col[0] for col in cursor.description]
        clientes_lista = [dict(zip(colunas, row)) for row in cursor.fetchall()]

    contexto = {
        'perfil': perfil_sessao,
        'clientes': clientes_lista,
        'cliente_edit': cliente_para_editar,
        'termo_busca': termo_busca 
    }

    return render(request, 'cliente/clientes.html', contexto)


def excluir_cliente_view(request, id_cliente):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE cliente SET ativo = '0' WHERE id_cliente = %s", [id_cliente])
    
    return redirect('gerenciar_clientes')