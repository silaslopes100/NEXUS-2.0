"""Script CLI para criar ou atualizar um usuário Administrador no banco de dados NeonDB/PostgreSQL."""
from __future__ import annotations

import argparse
import sys
import uuid

import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import settings
from app.core.security import hash_password

PERMISSOES_ADMIN = [
    "p_cadastro",
    "p_edicao",
    "p_acomp",
    "p_vendas",
    "p_matriculas",
    "p_matricula_manual",
    "p_ranking",
    "p_cursos",
    "p_users",
    "p_chat",
    "p_academico",
    "p_financeiro",
]


def create_or_update_admin(
    nome: str = "Administrador",
    sobrenome: str = "Central",
    email: str = "admin@nexus2.com.br",
    senha: str = "Admin@2026!",
    cpf: str | None = None,
) -> None:
    if not settings.PG_DSN:
        print("[-] PG_DSN não configurado no .env. Configure o banco PostgreSQL / NeonDB.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Conectando ao PostgreSQL...")
    conn = psycopg2.connect(settings.PG_DSN)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Garante perfil admin
            cur.execute("SELECT id FROM perfis WHERE lower(nome) = 'admin' LIMIT 1")
            row = cur.fetchone()
            if row:
                perfil_id = row["id"]
            else:
                perfil_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO perfis (id, nome, descricao, criado_em, atualizado_em) VALUES (%s, 'admin', 'Administrador Central do Sistema', now(), now()) RETURNING id",
                    (perfil_id,),
                )
                print(f"[+] Perfil 'admin' criado com ID: {perfil_id}")

            # 2. Garante permissões na tabela permissoes
            for perm in PERMISSOES_ADMIN:
                cur.execute(
                    "INSERT INTO permissoes (id, chave, descricao, criado_em, atualizado_em) VALUES (%s, %s, %s, now(), now()) ON CONFLICT (chave) DO NOTHING",
                    (str(uuid.uuid4()), perm, f"Permissão {perm}"),
                )

            # 3. Gera hash Argon2id da senha
            senha_hash = hash_password(senha)

            # 4. Cria ou atualiza usuário admin
            email_clean = email.strip().lower()
            cur.execute("SELECT id FROM usuarios WHERE lower(email) = %s LIMIT 1", (email_clean,))
            user_row = cur.fetchone()

            if user_row:
                user_id = user_row["id"]
                cur.execute(
                    """
                    UPDATE usuarios
                    SET nome = %s, sobrenome = %s, senha_hash = %s, senha_algoritmo = 'argon2id',
                        perfil_id = %s, status = 'ativo', cpf = COALESCE(%s, cpf), atualizado_em = now()
                    WHERE id = %s
                    """,
                    (nome, sobrenome, senha_hash, perfil_id, cpf, user_id),
                )
                print(f"[+] Usuário admin '{email_clean}' ATUALIZADO com sucesso (ID: {user_id}).")
            else:
                user_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO usuarios (id, nome, sobrenome, email, cpf, senha_hash, senha_algoritmo, perfil_id, status, criado_em, atualizado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, 'argon2id', %s, 'ativo', now(), now())
                    """,
                    (user_id, nome, sobrenome, email_clean, cpf, senha_hash, perfil_id),
                )
                print(f"[+] Novo usuário admin '{email_clean}' CRIADO com sucesso (ID: {user_id}).")

            # 5. Vincula permissões ao usuário
            cur.execute("DELETE FROM usuario_permissoes WHERE usuario_id = %s", (user_id,))
            for perm in PERMISSOES_ADMIN:
                cur.execute("SELECT id FROM permissoes WHERE chave = %s", (perm,))
                p_row = cur.fetchone()
                if p_row:
                    cur.execute(
                        "INSERT INTO usuario_permissoes (usuario_id, permissao_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (user_id, p_row["id"]),
                    )

            # 6. Grava log de auditoria
            cur.execute(
                """
                INSERT INTO logs_auditoria (usuario_id, acao, entidade, entidade_id, dados_depois, criado_em, atualizado_em)
                VALUES (%s, 'usuario_admin_seed', 'usuarios', %s, %s, now(), now())
                """,
                (
                    user_id,
                    str(user_id),
                    psycopg2.extras.Json({"email": email_clean, "nome": f"{nome} {sobrenome}", "perfil": "admin"}),
                ),
            )

        conn.commit()
        print("=" * 60)
        print(" CREDENCIAIS DE ACESSO ADMINISTRADOR NEXUS 2.0")
        print("=" * 60)
        print(f" E-mail:    {email_clean}")
        print(f" Senha:     {senha}")
        print(f" Perfil:    admin")
        print(f" Algoritmo: Argon2id")
        print("=" * 60)
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Criar usuário administrador no NEXUS 2.0")
    parser.add_argument("--nome", default="Administrador", help="Nome do administrador")
    parser.add_argument("--sobrenome", default="Central", help="Sobrenome do administrador")
    parser.add_argument("--email", default="admin@nexus2.com.br", help="E-mail de login")
    parser.add_argument("--senha", default="Admin@2026!", help="Senha de acesso")
    parser.add_argument("--cpf", default=None, help="CPF (opcional)")

    args = parser.parse_args()
    create_or_update_admin(
        nome=args.nome,
        sobrenome=args.sobrenome,
        email=args.email,
        senha=args.senha,
        cpf=args.cpf,
    )
