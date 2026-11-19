"""Carga inicial (baseline). Executa os mappers na ordem de dependencia de FK
e gera o relatorio de conferencia (relatorio_baseline.md) para validar o
baseline linha a linha antes de liberar o sistema.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .mappers.alunos_mapper import AlunoMapper, gerar_matriculas_nx
from .mappers.certificados_mapper import CertificadoMapper
from .mappers.cupons_mapper import CupomMapper
from .mappers.configuracoes_mapper import ConfigMapper, CustomizeMapper, FrontendSettingsMapper
from .mappers.escolas_legacy_mapper import EscolaLegacyMapper
from .mappers.feed_mapper import FeedPostMapper, LembreteMapper
from .mappers.licencas_mapper import LicencaMapper
from .mappers.matriculas_mapper import MatriculaMapper
from .mappers.mensagens_mapper import ConversaMapper, ConversaMembroMapper, MensagemMapper
from .mappers.notas_mapper import NotaMapper, compute_historico
from .mappers.pagamentos_mapper import OfflinePaymentMapper, PagamentoMapper, PagseguroMapper
from .mappers.pedidos_livros_mapper import PedidoLivroItemMapper, PedidoLivroMapper
from .mappers.perfis_mapper import PerfilMapper, ensure_defaults, preload_role_map
from .mappers.polos_mapper import PoloMapper
from .mappers.presencas_mapper import PresencaMapper
from .mappers.professores_mapper import ProfessorMapper
from .mappers.turmas_mapper import TurmaMapper
from .mappers.usuarios_mapper import UsuarioMapper, carregar_titulares_cpf, cpf_ou_none

logger = logging.getLogger(__name__)

# Ordem de dependencia (pai -> filho). NUNCA alterar sem revisar as FKs.
FULL_LOAD_ORDER = [
    PerfilMapper,       # roles + perfis padrao
    PoloMapper,         # users.polo distinto
    EscolaLegacyMapper, # escolas via query complexa MySQL (role 3 -> role 4)
    UsuarioMapper,      # users -> usuarios
    ProfessorMapper,    # users instrutor -> professores
    AlunoMapper,        # users aluno -> alunos
    # Cursos, disciplinas e calendários são mantidos pelo sistema; o ETL não os altera.
    TurmaMapper,        # no-op (sem origem legado)
    MatriculaMapper,    # enrol -> matriculas_ead
    NotaMapper,         # quiz -> notas
    PresencaMapper,     # presenca -> presencas
    LicencaMapper,      # licences -> licencas_atribuidas
    PedidoLivroMapper,  # p_livros -> pedidos (tipo livro)
    PedidoLivroItemMapper,  # p_livros -> pedidos_itens
    PagamentoMapper,    # pagamento -> pagamentos
    PagseguroMapper,    # pagseguro_transaction -> pagamentos
    OfflinePaymentMapper,   # offline_payment -> pagamentos
    ConversaMapper,     # message_thread -> conversas
    ConversaMembroMapper,   # sender/receiver -> conversa_membros
    MensagemMapper,     # message -> mensagens
    CertificadoMapper,  # certificates -> certificados
    CupomMapper,        # coupons -> cupons
    ConfigMapper,       # settings -> configuracoes
    FrontendSettingsMapper,  # frontend_settings -> configuracoes
    CustomizeMapper,    # customize -> configuracoes
    FeedPostMapper,     # blogs -> feed_posts
    LembreteMapper,     # noticeboard -> lembretes
]

# Passos agregados que rodam DEPOIS dos mappers (nao tem origem 1:1).
# (nome, funcao(target), mapper que precisa ter rodado para o passo rodar)
POST_STEPS = [
    ("historico_unificado (maior nota)", compute_historico, "NotaMapper"),
    ("matricula NX dos alunos", gerar_matriculas_nx, "AlunoMapper"),
]


def selecionar_mappers(only: str | None) -> list:
    """--only aceita um ou varios mappers separados por virgula
    (ex.: PoloMapper,EscolaLegacyMapper,UsuarioMapper). A execucao segue
    sempre a ordem de dependencia de FULL_LOAD_ORDER, nao a da lista."""
    if not only:
        return list(FULL_LOAD_ORDER)
    pedidos = {n.strip().lower() for n in only.split(",") if n.strip()}
    conhecidos = {m.__name__.lower() for m in FULL_LOAD_ORDER}
    desconhecidos = sorted(pedidos - conhecidos)
    if desconhecidos or not pedidos:
        raise SystemExit(f"Mapper(s) desconhecido(s) em --only: {', '.join(desconhecidos) or only}")
    return [m for m in FULL_LOAD_ORDER if m.__name__.lower() in pedidos]


def rodar_pos_passos(source, target, mappers: list) -> None:
    """Passos pos-carga, apenas os ligados aos mappers executados."""
    nomes = {m.__name__ for m in mappers}
    for nome, step, requer in POST_STEPS:
        if requer in nomes:
            logger.info("Passo pos-migracao: %s", nome)
            step(target)
    if nomes & {"PoloMapper", "UsuarioMapper"}:
        link_polo_coordenadores(source, target)


def link_polo_coordenadores(source, target) -> None:
    """Define o coordenador de cada polo (conta role 3).

    Coordenador = titular do CPF da conta role 3 (menor users.id role 2; sem
    role 2, a menor conta role 3/4 com o CPF -- mesma regra do UsuarioMapper).
    Conta role 3 sem CPF valido: ela mesma (foi migrada como usuario). CPFs
    comparados so por digitos. Idempotente.
    """
    titulares = carregar_titulares_cpf(source)
    coord_lid_por_polo: dict[int, int] = {}
    for u3 in source.stream("users", ["id", "cpf"], where="role_id = 3", order="id"):
        cpf = cpf_ou_none(u3.get("cpf"))
        coord_lid_por_polo[int(u3["id"])] = titulares.get(cpf, int(u3["id"])) if cpf else int(u3["id"])
    if not coord_lid_por_polo:
        logger.warning("Nenhuma conta role 3 na origem; pulando vinculo polo/coordenador")
        return

    with target.conn.cursor() as cur:
        cur.execute(
            "SELECT legacy_id, id FROM usuarios "
            "WHERE legacy_table = 'users' AND legacy_id = ANY(%s)",
            (list(set(coord_lid_por_polo.values())),),
        )
        usuario_por_lid = {int(r[0]): r[1] for r in cur.fetchall()}

    updates = sem_usuario = 0
    with target.conn.cursor() as cur:
        cur.execute("SELECT legacy_id, id FROM polos WHERE legacy_table = 'users' AND legacy_id IS NOT NULL")
        polos = cur.fetchall()
        for legacy_id, polo_id in polos:
            coord_id = usuario_por_lid.get(coord_lid_por_polo.get(int(legacy_id)))
            if not coord_id:
                sem_usuario += 1
                continue
            cur.execute(
                "UPDATE polos SET coordenador_usuario_id = %s, atualizado_em = now() "
                "WHERE id = %s AND coordenador_usuario_id IS DISTINCT FROM %s",
                (coord_id, polo_id, coord_id),
            )
            updates += cur.rowcount
    target.commit()
    logger.info(
        "coordenador vinculado/atualizado em %d polos (%d polos sem usuario coordenador migrado)",
        updates, sem_usuario,
    )


def update_escolas_polo_id(source, target) -> None:
    """Atualiza polo_id das escolas via join MySQL users (role 3) -> polos PG.

    Le users.role_id=3, expande campo CSV `escolas`, faz lookup em polos.legacy_id = u3.id,
    e atualiza escolas.legacy_id = escola_id com o polo_id correspondente.
    """
    logger.info("Atualizando polo_id das escolas...")
    # 1. Carrega mapa legacy_id -> polo_id da tabela polos (PG)
    with target.conn.cursor() as cur:
        cur.execute("SELECT legacy_id, id FROM polos WHERE legacy_id IS NOT NULL")
        polo_map = {int(r[0]): r[1] for r in cur.fetchall()}
    if not polo_map:
        logger.warning("Nenhum polo com legacy_id encontrado; pulando atualizacao de escolas")
        return

    # 2. Le do MySQL: users role_id=3 com campo escolas
    cols = ["id", "escolas"]
    where = "role_id = 3 AND COALESCE(escolas, '') <> ''"
    # Escola listada por mais de um polo: vale o de MENOR users.id (mesma
    # regra do EscolaLegacyMapper; os usuarios herdam esse polo). Por isso a
    # leitura e ordenada por id e cada escola so e atribuida uma vez.
    updates = 0
    atribuidas: set[int] = set()
    for u3 in source.stream("users", cols, where=where, order="id"):
        u3_id = int(u3["id"])
        polo_id = polo_map.get(u3_id)
        if not polo_id:
            continue
        escolas_csv = u3.get("escolas", "")
        escola_ids = [
            int(e) for e in escolas_csv.replace("[", "").replace("]", "").replace('"', "").split(",")
            if e.strip().isdigit() and int(e) not in atribuidas
        ]
        if not escola_ids:
            continue
        atribuidas.update(escola_ids)
        # 3. Atualiza escolas em batch (so as que mudam)
        placeholders = ",".join(["%s"] * len(escola_ids))
        sql = f"""
            UPDATE escolas
            SET polo_id = %s, atualizado_em = NOW()
            WHERE legacy_table = 'users' AND legacy_id IN ({placeholders})
              AND polo_id IS DISTINCT FROM %s
        """
        with target.conn.cursor() as cur:
            cur.execute(sql, (polo_id, *escola_ids, polo_id))
            updates += cur.rowcount
    target.commit()
    logger.info("polo_id atualizado em %d escolas", updates)


def run_full_load(source, target, registry, run_log, runner, only: str | None = None) -> None:
    ensure_defaults(target)
    preload_role_map(source, registry)

    mappers = selecionar_mappers(only)
    logger.info("Mappers: %s", ", ".join(m.__name__ for m in mappers))
    for cls in mappers:
        mapper = cls(registry=registry)
        runner.run(mapper)

    # escolas.polo_id via campo `escolas` das contas role 3 (precisa do MySQL)
    if any(m.__name__ == "EscolaLegacyMapper" for m in mappers):
        update_escolas_polo_id(source, target)
    rodar_pos_passos(source, target, mappers)


# Conferencia legado x novo, usada no relatorio do baseline.
FONTE_CONTAGEM = [
    ("usuarios", ["users"]),
    ("polos", ["users"]),
    ("escolas", ["users"]),
    ("professores", ["users"]),
    ("alunos", ["users"]),
    ("cursos", ["pacotes"]),
    ("disciplinas", ["section"]),
    ("disciplina_conteudos", ["lesson"]),
    ("calendarios_oficiais", ["section"]),
    ("matriculas_ead", ["enrol"]),
    ("notas", ["quiz"]),
    ("presencas", ["presenca"]),
    ("licencas_atribuidas", ["licences"]),
    ("pedidos", ["p_livros"]),
    ("pedidos_itens", ["p_livros"]),
    ("pagamentos", ["pagamento", "pagseguro_transaction", "offline_payment"]),
    ("conversas", ["message_thread"]),
    ("mensagens", ["message"]),
    ("certificados", ["certificates"]),
    ("cupons", ["coupons"]),
    ("configuracoes", ["settings", "frontend_settings", "customize"]),
    ("feed_posts", ["blogs"]),
    ("lembretes", ["noticeboard"]),
]


def generate_baseline_report(source, target, output_dir: Path) -> Path:
    """Contagem legado x novo por tabela (para conferencia manual do baseline)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "relatorio_baseline.md"
    linhas = [
        "# Relatorio de Conferencia do Baseline",
        "",
        "Contagem de linhas: tabelas de origem (MySQL) x tabelas de destino (PostgreSQL).",
        "",
        "| Tabela destino | Tabela origem | Origem | Destino | Delta |",
        "|---|---|---|---|---|",
    ]
    for target_name, sources in FONTE_CONTAGEM:
        origem = 0
        for t in sources:
            try:
                origem += source.count(t)
            except Exception as exc:  # noqa: BLE001
                origem = -1
                logger.warning("Nao foi possivel contar %s: %s", t, exc)
                break
        with target.conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {target_name}")
            destino = cur.fetchone()[0]
        delta = "" if origem < 0 else f"{origem - destino:+d}"
        linhas.append(
            f"| {target_name} | {', '.join(sources)} | {origem if origem >= 0 else 'erro'} "
            f"| {destino} | {delta} |"
        )
    texto = "\n".join(linhas) + "\n"
    path.write_text(texto, encoding="utf-8")
    logger.info("Relatorio de conferencia gerado em %s", path)
    return path