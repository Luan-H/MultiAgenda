from django.shortcuts import render, redirect
from django.db import connection

def gerenciar_servicos_view(request, id_edit=None):
    login_sessao = request.session.get('usuario_login')
    perfil_sessao = request.session.get('usuario_perfil')
    
    # 1. CORREÇÃO: Incluído o perfil 'profissional' na lista de permissões da tela
    if not login_sessao or perfil_sessao not in ['admin', 'secretario', 'profissional']:
        return redirect('login')
    
    servico_para_editar = None

    with connection.cursor() as cursor:
        # 2. CORREÇÃO: Busca unificada do id_empresa para funcionário ou administrador logado
        cursor.execute("""
            SELECT id_empresa FROM usuario WHERE login = %s
            UNION
            SELECT id_empresa FROM profissional WHERE login = %s
        """, [login_sessao, login_sessao])
        
        row_empresa = cursor.fetchone()
        if not row_empresa:
            return redirect('login')
        id_empresa = row_empresa[0]

        if id_edit:
            cursor.execute("SELECT id_servico, nome, vlr_servico, duracao_em_min FROM servico WHERE id_servico = %s", [id_edit])
            row = cursor.fetchone()
            if row:
                servico_para_editar = {
                    'id': row[0], 
                    'nome': row[1], 
                    'vlr_servico': str(row[2]), 
                    'duracao_em_min': row[3]
                }

        if request.method == "POST":
            # Caso queira impedir que o profissional cadastre ou altere serviços, descomente as duas linhas abaixo:
            # if perfil_sessao == 'profissional':
            #     return redirect('gerenciar_servicos')

            nome = request.POST.get('nome')
            vlr_servico = request.POST.get('vlr_servico')
            duracao_em_min = request.POST.get('duracao_em_min')
            
            if id_edit: 
                cursor.execute("""
                    UPDATE servico 
                    SET nome=%s, vlr_servico=%s, duracao_em_min=%s 
                    WHERE id_servico=%s
                """, [nome, vlr_servico, duracao_em_min, id_edit])
            else: 
                cursor.execute("""
                    INSERT INTO servico (nome, vlr_servico, duracao_em_min, ativo, id_empresa) 
                    VALUES (%s, %s, %s, '1', %s)
                """, [nome, vlr_servico, duracao_em_min, id_empresa])
                
            return redirect('gerenciar_servicos')

        termo_busca = request.GET.get('q', '') 

        # 3. CORREÇÃO: Otimização das consultas de listagem utilizando o id_empresa capturado previamente
        if termo_busca:
            query_list = """
                SELECT id_servico AS id, nome, vlr_servico, duracao_em_min FROM servico 
                WHERE id_empresa = %s
                AND ativo = '1'
                AND nome ILIKE %s
                ORDER BY nome
            """
            param = f"%{termo_busca}%"
            cursor.execute(query_list, [id_empresa, param])
        else:
            query_list = """
                SELECT id_servico AS id, nome, vlr_servico, duracao_em_min FROM servico 
                WHERE id_empresa = %s
                AND ativo = '1'
                ORDER BY nome
            """
            cursor.execute(query_list, [id_empresa])
            
        colunas = [col[0] for col in cursor.description]
        servicos_lista = [dict(zip(colunas, row)) for row in cursor.fetchall()]

    contexto = {
        'perfil': perfil_sessao,
        'servicos': servicos_lista,
        'servico_edit': servico_para_editar,
        'termo_busca': termo_busca 
    }

    return render(request, 'servico/servicos.html', contexto)


def excluir_servico_view(request, id_servico):
    perfil_sessao = request.session.get('usuario_perfil')
    
    # Restrição para que profissionais não consigam apagar serviços digitando a URL diretamente
    if perfil_sessao == 'profissional':
        return redirect('gerenciar_servicos')

    with connection.cursor() as cursor:
        cursor.execute("UPDATE servico SET ativo = '0' WHERE id_servico = %s", [id_servico])
    
    return redirect('gerenciar_servicos')