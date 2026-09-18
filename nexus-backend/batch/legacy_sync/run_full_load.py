"""Carga inicial (baseline). Executa os mappers na ordem de dependencia de FK
e gera o relatorio de conferencia (relatorio_baseline.md) para validar o
baseline linha a linha antes de liberar o sistema.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .mappers.alunos_mapper import AlunoMapper
from .mappers.certificados_mapper import CertificadoMapper
from .mappers.cupons_mapper import CupomMapper
from .mappers.configuracoes_mapper import ConfigMapper, CustomizeMapper, FrontendSettingsMapper
from .mappers.cursos_mapper import CursoMapper
from .mappers.disciplinas_mapper import DisciplinaConteudoMapper, DisciplinaMapper
from .mappers.escolas_legacy_mapper import EscolaLegacyMapper
from .mappers.feed_mapper import FeedPostMapper, LembreteMapper
from .mappers.licencas_mapper import LicencaMapper
from .mappers.matriculas_mapper import MatriculaMapper
from .mappers.mensagens_mapper import ConversaMapper, ConversaMembroMapper, MensagemMapper
from .mappers.notas_mapper import NotaMapper, compute_historico
from .mappers.pagamentos_mapper import OfflinePaymentMapper, PagamentoMapper, PagseguroMapper
from .mappers.pedidos_livros_mapper import PedidoLivroItemMapper, PedidoLivroMapper
from .mappers.perfis_mapper import PerfilMapper, ensure_defaults
from .mappers.polos_mapper import PoloMapper
from .mappers.presencas_mapper import PresencaMapper
from .mappers.professores_mapper import ProfessorMapper
from .mappers.turmas_mapper import CalendarioOficialMapper, TurmaMapper
from .mappers.usuarios_mapper import UsuarioMapper

logger = logging.getLogger(__name__)

# Ordem de dependencia (pai -> filho). NUNCA alterar sem revisar as FKs.
FULL_LOAD_ORDER = [
    PerfilMapper,       # roles + perfis padrao
    PoloMapper,         # users.polo distinto
    EscolaLegacyMapper, # escolas via query complexa MySQL (role 3 -> role 4)
    UsuarioMapper,      # users -> usuarios
    ProfessorMapper,    # users instrutor -> professores
    AlunoMapper,        # users aluno -> alunos
    CursoMapper,        # pacotes -> cursos
    DisciplinaMapper,   # section -> disciplinas
    DisciplinaConteudoMapper,  # lesson -> disciplina_conteudos
    CalendarioOficialMapper,   # section datas -> calendarios_oficiais
    TurmaMapper,        # no-op (sem origem legado)
    MatriculaMapper,    # enrol -> matriculas_ead
    NotaMapper,         # quiz -> notas
    PresencaMapper,     # presenca -> presencas
    LicencaMapper,      # licences -> licencas_atribuidas
    PedidoLivroMapper,  # p_livros -> pedidos_livros
    PedidoLivroItemMapper,  # p_livros -> pedidos_livros_itens
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
POST_STEPS = [("historico_unificado (maior nota)", compute_historico)]


def link_polo_coordenadores(target) -> None:
    """Vincula cada polo ao usuario legado role 2 com o mesmo CPF.

    O passo roda depois de `UsuarioMapper`, quando o id legado do coordenador
    já foi convertido para UUID no destino. O UPDATE é idempotente.
    """
    target.execute(
        """
        UPDATE polos AS p
        SET coordenador_usuario_id = u.id,
            atualizado_em = now()
        FROM usuarios AS u
        JOIN perfis AS perfil ON perfil.id = u.perfil_id
        WHERE p.responsavel_cpf IS NOT NULL
          AND u.cpf = p.responsavel_cpf
          AND perfil.legacy_table = 'role'
          AND perfil.legacy_id = 2
        """
    )
    target.commit()


POST_STEPS.insert(0, ("vinculo polo/coordenador por CPF", link_polo_coordenadores))


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
    updates = 0
    for u3 in source.stream("users", cols, where=where):
        u3_id = int(u3["id"])
        polo_id = polo_map.get(u3_id)
        if not polo_id:
            continue
        escolas_csv = u3.get("escolas", "")
        escola_ids = [
            int(e) for e in escolas_csv.replace("[", "").replace("]", "").replace('"', "").split(",")
            if e.strip().isdigit()
        ]
        if not escola_ids:
            continue
        # 3. Atualiza escolas em batch
        placeholders = ",".join(["%s"] * len(escola_ids))
        sql = f"""
            UPDATE escolas
            SET polo_id = %s, atualizado_em = NOW()
            WHERE legacy_id IN ({placeholders})
        """
        with target.conn.cursor() as cur:
            cur.execute(sql, (polo_id, *escola_ids))
            updates += cur.rowcount
    target.commit()
    logger.info("polo_id atualizado em %d escolas", updates)


def run_full_load(source, target, registry, run_log, runner, only: str | None = None) -> None:
    ensure_defaults(target)

    mappers = [m for m in FULL_LOAD_ORDER if not only or m.__name__.lower() == only.lower()]
    if not mappers:
        raise SystemExit(f"Nenhum mapper encontrado para --only={only}")

    for cls in mappers:
        mapper = cls(registry=registry)
        runner.run(mapper)

    for nome, step in POST_STEPS:
        logger.info("Passo pos-migracao: %s", nome)
        step(target)

    # Passo extra: atualiza polo_id das escolas (precisa do source MySQL)
    if not only or "EscolaLegacyMapper".lower() == only.lower():
        update_escolas_polo_id(source, target)


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
    ("pedidos_livros", ["p_livros"]),
    ("pedidos_livros_itens", ["p_livros"]),
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