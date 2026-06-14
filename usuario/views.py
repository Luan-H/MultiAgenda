from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.contrib.auth.hashers import check_password, make_password

def buscar_usuario_para_login(login_digitado):
    with connection.cursor() as cursor:
        query = """
            SELECT login, senha, 'cliente' AS perfil 
            FROM cliente 
            WHERE login = %s AND ativo = '1'
            UNION
            SELECT login, senha, 'profissional' AS perfil 
            FROM profissional 
            WHERE login = %s AND ativo = '1'
            UNION
            SELECT login, senha, cargo AS perfil 
            FROM usuario 
            WHERE login = %s AND ativo = '1';
        """
        cursor.execute(query, [login_digitado, login_digitado, login_digitado])
        return cursor.fetchone()


def login_view(request):
    contexto = {}

    if request.method == "POST":
        login_form = request.POST.get("login")
        senha_form = request.POST.get("senha")
        dados_usuario = buscar_usuario_para_login(login_form)
        
        if dados_usuario:
            login_db, senha_db, perfil = dados_usuario
            if check_password(senha_form, senha_db):
                request.session["usuario_login"] = login_db
                request.session["usuario_perfil"] = perfil
                
                if perfil == "cliente":
                    return redirect("agenda_cliente")
                elif perfil == "profissional":
                    return redirect("gerenciar_agendamentos")
                else:
                    return redirect("dashboard_admin")
            else:
                contexto["erro"] = "Senha incorreta."
        else:
            contexto["erro"] = "Usuario nao encontrado."
            
    return render(request, "login.html", contexto)


def buscar_nome_pelo_login(login):
    with connection.cursor() as cursor:
        query = """
            SELECT nome FROM cliente WHERE login = %s
            UNION
            SELECT nome FROM profissional WHERE login = %s
            UNION
            SELECT nome FROM usuario WHERE login = %s;
        """
        cursor.execute(query, [login, login, login])
        resultado = cursor.fetchone()
        return resultado[0] if resultado else "Utilizador"


def dashboard_admin_view(request):
    login_sessao = request.session.get("usuario_login")
    perfil_sessao = request.session.get("usuario_perfil")

    if not login_sessao:
        return redirect("login")

    nome = buscar_nome_pelo_login(login_sessao)

    contexto = {"nome_usuario": nome, "perfil": perfil_sessao}

    return render(request, "dashboard/dashboard.html", contexto)


def gerenciar_usuarios_view(request, login_edit=None):
    login_sessao = request.session.get("usuario_login")
    perfil_sessao = request.session.get("usuario_perfil")

    # Garante que o usuário está logado e é admin
    if not login_sessao or perfil_sessao != "admin":
        return redirect("login")

    usuario_para_editar = None

    # Se houver um login na URL, buscamos os dados dele para preencher o modal
    if login_edit:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT nome, login, cargo FROM usuario WHERE login = %s", [login_edit]
            )
            row = cursor.fetchone()
            if row:
                usuario_para_editar = {"nome": row[0], "login": row[1], "cargo": row[2]}

    # --- LÓGICA DE POST (SALVAR NOVO OU ATUALIZAR) ---
    if request.method == "POST":
        nome = request.POST.get("nome")
        cargo = request.POST.get("cargo")

        with connection.cursor() as cursor:
            if login_edit:  # CASO 1: Atualiza um usuário existente
                cursor.execute(
                    "UPDATE usuario SET nome=%s, cargo=%s WHERE login=%s",
                    [nome, cargo, login_edit],
                )

            else:  # CASO 2: Cadastra um novo usuário
                login_novo = request.POST.get("login_novo")
                senha_crua = request.POST.get("senha_nova")
                senha_hash = make_password(senha_crua)

                # Busca o ID da empresa do administrador logado
                cursor.execute(
                    "SELECT id_empresa FROM usuario WHERE login = %s", [login_sessao]
                )
                id_empresa = cursor.fetchone()[0]

                # Insert para adicionar o novo usuário
                query_insert = """
                    INSERT INTO usuario (nome, login, senha, cargo, ativo, id_empresa)
                    VALUES (%s, %s, %s, %s, '1', %s)
                """
                cursor.execute(
                    query_insert, [nome, login_novo, senha_hash, cargo, id_empresa]
                )

        return redirect("gerenciar_usuarios")

    # --- LÓGICA DE GET (LISTAGEM COM BUSCA E ORDENAÇÃO) ---
    termo_busca = request.GET.get("q", "")

    with connection.cursor() as cursor:
        if termo_busca:
            # Com busca: Usa o ILIKE e ordena por nome
            query_list = """
                SELECT nome, login, cargo FROM usuario 
                WHERE id_empresa = (SELECT id_empresa FROM usuario WHERE login = %s)
                AND (nome ILIKE %s OR login ILIKE %s)
                ORDER BY nome
            """
            param_busca = f"%{termo_busca}%"
            cursor.execute(query_list, [login_sessao, param_busca, param_busca])
        else:
            # Sem busca: Traz todos da empresa ordenados por nome
            query_list = """
                SELECT nome, login, cargo FROM usuario 
                WHERE id_empresa = (SELECT id_empresa FROM usuario WHERE login = %s)
                ORDER BY nome
            """
            cursor.execute(query_list, [login_sessao])

        colunas = [col[0] for col in cursor.description]
        usuarios_lista = [dict(zip(colunas, row)) for row in cursor.fetchall()]

    contexto = {
        "perfil": perfil_sessao,
        "usuarios": usuarios_lista,
        "usuario_edit": usuario_para_editar,
        "termo_busca": termo_busca,
    }

    return render(request, "usuarios/usuarios.html", contexto)


# DELETE - Excluir
def excluir_usuario_view(request, login_usuario):
    if request.session.get("usuario_perfil") != "admin":
        return redirect("dashboard_admin")

    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM usuario WHERE login = %s", [login_usuario])

    return redirect("gerenciar_usuarios")
