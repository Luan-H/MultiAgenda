# ==========================================================
# IMPORTAÇÃO DAS BIBLIOTECAS
# ==========================================================

from django.shortcuts import render, redirect
from django.db import connection

# ==========================================================
# VIEW DE GERENCIAMENTO DE SERVIÇOS
# ==========================================================
def gerenciar_servicos_view(request, id_edit=None):

    # Recupera os dados do usuário logado
    login_sessao = request.session.get("usuario_login")
    perfil_sessao = request.session.get("usuario_perfil")

    # Permite acesso apenas para perfis autorizados
    if not login_sessao or perfil_sessao not in ["admin", "secretario", "profissional"]:
        return redirect("login")

    servico_para_editar = None

    with connection.cursor() as cursor:

        # ==========================================================
        # IDENTIFICAÇÃO DA EMPRESA DO USUÁRIO
        # ==========================================================

        # Busca a empresa associada ao usuário logado
        cursor.execute(
            """
            SELECT id_empresa FROM usuario WHERE login = %s
            UNION
            SELECT id_empresa FROM profissional WHERE login = %s
        """,
            [login_sessao, login_sessao],
        )

        row_empresa = cursor.fetchone()

        if not row_empresa:
            return redirect("login")

        id_empresa = row_empresa[0]

        # ==========================================================
        # CARREGAMENTO DOS DADOS PARA EDIÇÃO
        # ==========================================================

        if id_edit:

            # Busca os dados do serviço selecionado
            cursor.execute(
                """
                SELECT
                    id_servico,
                    nome,
                    vlr_servico,
                    duracao_em_min
                FROM servico
                WHERE id_servico = %s
            """,
                [id_edit],
            )

            row = cursor.fetchone()

            if row:
                servico_para_editar = {
                    "id": row[0],
                    "nome": row[1],
                    "vlr_servico": str(row[2]),
                    "duracao_em_min": row[3],
                }

        # ==========================================================
        # CADASTRO E EDIÇÃO DE SERVIÇOS
        # ==========================================================

        if request.method == "POST":

            # Recupera os dados enviados pelo formulário
            nome = request.POST.get("nome")
            vlr_servico = request.POST.get("vlr_servico")
            duracao_em_min = request.POST.get("duracao_em_min")

            # ==========================================================
            # ATUALIZAÇÃO DE SERVIÇO EXISTENTE
            # ==========================================================
            if id_edit:

                cursor.execute(
                    """
                    UPDATE servico
                    SET nome=%s,
                        vlr_servico=%s,
                        duracao_em_min=%s
                    WHERE id_servico=%s
                """,
                    [nome, vlr_servico, duracao_em_min, id_edit],
                )

            # ==========================================================
            # CADASTRO DE NOVO SERVIÇO
            # ==========================================================
            else:

                cursor.execute(
                    """
                    INSERT INTO servico (
                        nome,
                        vlr_servico,
                        duracao_em_min,
                        ativo,
                        id_empresa
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        '1',
                        %s
                    )
                """,
                    [nome, vlr_servico, duracao_em_min, id_empresa],
                )

            return redirect("gerenciar_servicos")

        # ==========================================================
        # FILTRO DE PESQUISA
        # ==========================================================

        termo_busca = request.GET.get("q", "")

        # ==========================================================
        # CONSULTA DA LISTA DE SERVIÇOS
        # ==========================================================

        if termo_busca:

            query_list = """
                SELECT
                    id_servico AS id,
                    nome,
                    vlr_servico,
                    duracao_em_min
                FROM servico
                WHERE id_empresa = %s
                AND ativo = '1'
                AND nome ILIKE %s
                ORDER BY nome
            """

            param = f"%{termo_busca}%"

            cursor.execute(query_list, [id_empresa, param])

        else:

            query_list = """
                SELECT
                    id_servico AS id,
                    nome,
                    vlr_servico,
                    duracao_em_min
                FROM servico
                WHERE id_empresa = %s
                AND ativo = '1'
                ORDER BY nome
            """

            cursor.execute(query_list, [id_empresa])

        # Converte o resultado da consulta para uma lista de dicionários
        colunas = [col[0] for col in cursor.description]

        servicos_lista = [dict(zip(colunas, row)) for row in cursor.fetchall()]

    # ==========================================================
    # DADOS ENVIADOS PARA O TEMPLATE
    # ==========================================================

    contexto = {
        "perfil": perfil_sessao,
        "servicos": servicos_lista,
        "servico_edit": servico_para_editar,
        "termo_busca": termo_busca,
    }

    return render(request, "servico/servicos.html", contexto)


# ==========================================================
# EXCLUSÃO LÓGICA DE SERVIÇOS
# ==========================================================
def excluir_servico_view(request, id_servico):

    perfil_sessao = request.session.get("usuario_perfil")

    # Impede que profissionais ou clientes removam serviços
    if perfil_sessao not in ['admin', 'secretario']:
        return redirect('gerenciar_servicos')

    with connection.cursor() as cursor:

        # Desativa o serviço sem removê-lo fisicamente do banco
        cursor.execute(
            """
            UPDATE servico
            SET ativo = '0'
            WHERE id_servico = %s
        """,
            [id_servico],
        )

    return redirect("gerenciar_servicos")