# ==========================================================
# IMPORTAÇÃO DAS BIBLIOTECAS
# ==========================================================

from django.shortcuts import render, redirect
from django.db import connection
from django.contrib.auth.hashers import make_password

# ==========================================================
# VALIDAÇÃO DE UNICIDADE DE LOGIN
# ==========================================================
def login_ja_existe(login_digitado):
    # Esta função verifica se um login já está em uso em qualquer uma das
    # tabelas de usuários do sistema (cliente, profissional, ou usuario).
    # O UNION combina os resultados para uma verificação única e eficiente.
    with connection.cursor() as cursor:
        query = """
            SELECT 1 FROM cliente WHERE login = %s
            UNION
            SELECT 1 FROM profissional WHERE login = %s
            UNION
            SELECT 1 FROM usuario WHERE login = %s
        """
        cursor.execute(query, [login_digitado, login_digitado, login_digitado])
        resultado = cursor.fetchone()
        return resultado is not None

# ==========================================================
# VIEW DE GERENCIAMENTO DE CLIENTES
# ==========================================================
def gerenciar_clientes_view(request, id_edit=None):
    # Recupera as informações do usuário logado
    login_sessao = request.session.get("usuario_login")
    perfil_sessao = request.session.get("usuario_perfil")

    # Impede acesso sem autenticação
    if not login_sessao:
        return redirect("login")
        
    # Variável utilizada quando um cliente está sendo editado
    cliente_para_editar = None
    # Variável para armazenar erro de login duplicado
    erro_login = None

    # ==========================================================
    # CARREGAMENTO DOS DADOS PARA EDIÇÃO
    # ==========================================================
    if id_edit:
        with connection.cursor() as cursor:
            # Busca os dados do cliente selecionado para preencher o formulário
            # no modo de edição.
            cursor.execute(
                """
                SELECT id_cliente, nome, login, telefone, observacoes
                FROM cliente
                WHERE id_cliente = %s
            """,
                [id_edit],
            )

            row = cursor.fetchone()

            # Monta o dicionário que será enviado ao formulário
            if row:
                cliente_para_editar = {
                    "id": row[0],
                    "nome": row[1],
                    "login": row[2],
                    "telefone": row[3],
                    "observacoes": row[4],
                }

    # ==========================================================
    # CADASTRO E ATUALIZAÇÃO DE CLIENTES
    # ==========================================================
    if request.method == "POST":
        # Recupera os dados enviados pelo formulário
        nome = request.POST.get("nome")
        login_cliente = request.POST.get("login")
        telefone = request.POST.get("telefone")
        observacoes = request.POST.get("observacoes")
        senha_crua = request.POST.get("senha")

        with connection.cursor() as cursor:
            # ==========================================================
            # EDIÇÃO DE CLIENTE EXISTENTE
            # ==========================================================
            if id_edit:
                # Se uma nova senha foi fornecida no formulário, ela é criptografada
                # e a query de UPDATE inclui o campo 'senha'.
                if senha_crua:
                    senha_hash = make_password(senha_crua)
                    cursor.execute(
                        """
                        UPDATE cliente
                        SET nome=%s,
                            login=%s,
                            telefone=%s,
                            observacoes=%s,
                            senha=%s
                        WHERE id_cliente=%s
                    """,
                        [
                            nome,
                            login_cliente,
                            telefone,
                            observacoes,
                            senha_hash,
                            id_edit,
                        ],
                    )
                # Se o campo de senha estiver vazio, a query de UPDATE não mexe
                # na senha atual, preservando a credencial do cliente.
                else:
                    cursor.execute(
                        """
                        UPDATE cliente
                        SET nome=%s,
                            login=%s,
                            telefone=%s,
                            observacoes=%s
                        WHERE id_cliente=%s
                    """,
                        [nome, login_cliente, telefone, observacoes, id_edit],
                    )
            # ==========================================================
            # CADASTRO DE NOVO CLIENTE
            # ==========================================================
            else:
                # Validação preventiva para impedir credenciais duplicadas no sistema
                if login_ja_existe(login_cliente):
                    erro_login = "Este login ja esta sendo usado por outra pessoa."
                else:
                    # Criptografa a senha antes de salvar
                    senha_hash = make_password(senha_crua) if senha_crua else ""
                    
                    # Busca o ID da empresa do usuário logado (admin ou profissional)
                    # para associar o novo cliente à empresa correta.
                    cursor.execute(
                        """
                        -- O UNION é usado aqui para encontrar o id_empresa tanto na tabela de usuários quanto na de profissionais.
                        SELECT id_empresa FROM usuario WHERE login = %s
                        UNION
                        SELECT id_empresa FROM profissional WHERE login = %s
                    """,
                        [login_sessao, login_sessao],
                    )
                    resultado_empresa = cursor.fetchone()

                    # Se a empresa for encontrada, insere o novo cliente no banco de dados,
                    # já com o 'id_empresa' correto.
                    if resultado_empresa:
                        id_empresa = resultado_empresa[0]
                        cursor.execute(
                            """
                            INSERT INTO cliente (
                                nome,
                                login,
                                senha,
                                telefone,
                                observacoes,
                                ativo,
                                id_empresa
                            )
                            VALUES (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                '1',
                                %s
                            )
                        """,
                            [
                                nome,
                                login_cliente,
                                senha_hash,
                                telefone,
                                observacoes,
                                id_empresa,
                            ],
                        )
                        
        # Se não houve erro de duplicidade de login, retorna para a listagem limpa
        if not erro_login:
            return redirect("gerenciar_clientes")

    # ==========================================================
    # FILTRO DE PESQUISA
    # ==========================================================
    termo_busca = request.GET.get("q", "")

    with connection.cursor() as cursor:
        # Identifica o 'id_empresa' do usuário logado para garantir que ele só
        # visualize clientes da sua própria empresa.
        cursor.execute(
            """
            SELECT id_empresa FROM usuario WHERE login = %s
            UNION
            SELECT id_empresa FROM profissional WHERE login = %s
            UNION
            SELECT id_empresa FROM cliente WHERE login = %s
        """,
            [login_sessao, login_sessao, login_sessao],
        )
        row_empresa = cursor.fetchone()

        if not row_empresa:
            return redirect("login")
        id_empresa = row_empresa[0]

        # ==========================================================
        # CONSULTA DOS CLIENTES
        # ==========================================================
        # Clientes visualizam apenas seus próprios dados
        if perfil_sessao == "cliente":
            # Se o perfil for de cliente, a consulta é restrita para retornar
            # apenas os dados do próprio cliente logado.
            cursor.execute(
                """
                SELECT id_cliente, nome, login, telefone
                FROM cliente
                WHERE login = %s
                AND ativo = '1'
            """,
                [login_sessao],
            )
        else:
            # Para outros perfis, a busca pode ser feita com um termo de pesquisa.
            if termo_busca:
                # A query usa ILIKE para busca case-insensitive em múltiplos campos.
                query_list = """
                    SELECT id_cliente, nome, login, telefone
                    FROM cliente
                    WHERE id_empresa = %s
                    AND ativo = '1'
                    AND (
                        nome ILIKE %s
                        OR login ILIKE %s
                        OR telefone ILIKE %s
                    )
                    ORDER BY nome
                """
                param = f"%{termo_busca}%"
                cursor.execute(query_list, [id_empresa, param, param, param])
            # Se não houver termo de busca, lista todos os clientes ativos da empresa.
            else:
                cursor.execute(
                    """
                    SELECT id_cliente, nome, login, telefone
                    FROM cliente
                    WHERE id_empresa = %s
                    AND ativo = '1'
                    ORDER BY nome
                """,
                    [id_empresa],
                )
        # O resultado da consulta é transformado em uma lista de dicionários
        # para facilitar o acesso aos dados no template.
        clientes_lista = [
            {"id": row[0], "nome": row[1], "login": row[2], "telefone": row[3]}
            for row in cursor.fetchall()
        ]
        
    # ==========================================================
    # DADOS ENVIADOS PARA O TEMPLATE
    # ==========================================================
    contexto = {
        "perfil": perfil_sessao,
        "clientes": clientes_lista,
        "cliente_edit": cliente_para_editar,
        "termo_busca": termo_busca,
    }
    
    # Adiciona o erro ao contexto apenas se ele existir
    if erro_login:
        contexto["erro_login"] = erro_login

    return render(request, "cliente/clientes.html", contexto)


# ==========================================================
# EXCLUSÃO LÓGICA DE CLIENTE
# ==========================================================
def excluir_cliente_view(request, id_cliente):
    perfil_sessao = request.session.get("usuario_perfil")
    
    if perfil_sessao not in ["admin", "secretario"]:
        return redirect("gerenciar_clientes")
    
    with connection.cursor() as cursor:
        # Realiza uma exclusão lógica, atualizando o status do cliente para '0' (inativo)
        # em vez de remover o registro. Isso preserva o histórico de agendamentos.
        cursor.execute(
            """
            UPDATE cliente
            SET ativo = '0'
            WHERE id_cliente = %s
        """,
            [id_cliente],
        )

    return redirect("gerenciar_clientes")