"""Ficha cadastral do usuário: edição por seção, inativação, exclusão só sem histórico e histórico."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.modules.carga_horaria.schemas import FrequenciaAluno, FrequenciaResponse
from app.modules.carga_horaria.service import CargaHorariaService
from app.modules.transferencias.repository import InMemoryTransferenciasRepository, set_transferencias_repository
POLO_A = "b0000000-0000-0000-0000-00000000000a"
POLO_B = "b0000000-0000-0000-0000-00000000000b"
ESC_B = "c0000000-0000-0000-0000-00000000000b"

from test_admin import _get_admin_token, _seed_aluno_com_dados, client, repos_setup  # noqa: F401


def _h() -> dict:
    return {"Authorization": f"Bearer {_get_admin_token()}"}


def _logs(admin_repo, acao: str) -> list:
    return [l for l in admin_repo.logs_auditoria if l.get("acao") == acao]


# ---------- Ficha ----------

@pytest.mark.asyncio
async def test_ficha_traz_dados_cadastrais_e_unidade_do_aluno(client, repos_setup):
    _, repo = repos_setup
    _seed_aluno_com_dados(repo)
    repo.usuarios["aluno-1"].update({"cep": "01001000", "cidade": "São Paulo", "rg": "123"})

    ficha = (await client.get("/admin/usuarios/aluno-1/ficha", headers=_h())).json()

    assert ficha["dados"]["cep"] == "01001000"
    assert ficha["dados"]["rg"] == "123"
    # Sem nascimento em usuarios: a ficha mostra o do cadastro de aluno.
    assert ficha["dados"]["data_nascimento"] == "2000-05-20"
    assert ficha["aluno"]["polo_nome"] == "Polo Centro"
    assert ficha["aluno"]["escola_nome"] == "Escola Modelo"
    assert ficha["aluno"]["transferencia_pendente"] is None


@pytest.mark.asyncio
async def test_ficha_professor_usa_vinculos_das_turmas(client, repos_setup):
    _, repo = repos_setup
    repo.professores["pr-1"] = {"id": "pr-1", "usuario_id": "prof-1", "status": "ativo", "chave_pix": "pix@x"}
    repo._tab("professor_disciplinas").extend([
        {"professor_id": "pr-1", "professor_disciplina_id": "pd-1", "turma_id": "t1", "turma_nome": "Turma A",
         "disciplina_id": "d1", "disciplina_nome": "Eclesiologia", "carga_horaria": 40, "aulas_previstas": 2,
         "aulas_ministradas": 1, "horas_ministradas": 20},
        {"professor_id": "pr-1", "professor_disciplina_id": "pd-2", "turma_id": "t1", "turma_nome": "Turma A",
         "disciplina_id": "d2", "disciplina_nome": "Homilética", "carga_horaria": 40, "aulas_previstas": 2,
         "aulas_ministradas": 0, "horas_ministradas": 0},
    ])

    ficha = (await client.get("/admin/usuarios/prof-1/ficha", headers=_h())).json()
    assert [v["disciplina_nome"] for v in ficha["professor"]["vinculos"]] == ["Eclesiologia", "Homilética"]
    assert ficha["professor"]["chave_pix"] == "pix@x"

    resumo = (await client.get("/admin/usuarios/prof-1/resumo", headers=_h())).json()["professor"]
    assert resumo["turmas_total"] == 1
    assert resumo["disciplinas_total"] == 2
    assert resumo["horas_previstas"] == 80
    assert resumo["horas_ministradas"] == 20
    assert resumo["aulas_registradas"] == 1


@pytest.mark.asyncio
async def test_resumo_aluno_usa_frequencia_rn07(client, repos_setup, monkeypatch):
    _, repo = repos_setup
    _seed_aluno_com_dados(repo)
    repo._tab("turma_alunos").append({"aluno_id": "al-1", "turma_id": "t1", "turma_nome": "Turma A"})

    def _frequencia(self, user, turma_id):
        return FrequenciaResponse(
            turma_id=turma_id, base="aulas", minimo_pct=75, alunos_em_risco=1,
            alunos=[FrequenciaAluno(aluno_id="al-1", nome="Maria", frequencia_pct=50.0, em_risco=True)],
        )

    monkeypatch.setattr(CargaHorariaService, "frequencia", _frequencia)
    aluno = (await client.get("/admin/usuarios/aluno-1/resumo", headers=_h())).json()["aluno"]

    assert aluno["turmas_total"] == 1
    assert aluno["frequencia_pct"] == 50.0
    assert aluno["frequencia_minima_pct"] == 75
    assert aluno["frequencia_em_risco"] is True


# ---------- Seções ----------

@pytest.mark.asyncio
async def test_secao_identificacao_valida_unicidade_e_audita_so_o_que_mudou(client, repos_setup):
    _, repo = repos_setup
    corpo = {"nome": "Professor", "sobrenome": "Silva", "email": "admin@nexus.com.br",
             "cpf": "22222222222", "telefone": None, "celular": None}
    dup = await client.put("/admin/usuarios/prof-1/identificacao", json=corpo, headers=_h())
    assert dup.status_code == 400

    corpo["email"] = "prof@nexus.com.br"
    corpo["celular"] = "(11) 98888-7777"
    res = await client.put("/admin/usuarios/prof-1/identificacao", json=corpo, headers=_h())
    assert res.status_code == 200
    assert repo.usuarios["prof-1"]["celular"] == "11988887777"
    log = _logs(repo, "usuario_identificacao_atualizada")[-1]
    assert log["dados_depois"] == {"celular": "11988887777"}

    invalido = await client.put("/admin/usuarios/prof-1/identificacao",
                                json={**corpo, "cpf": "123"}, headers=_h())
    assert invalido.status_code == 422


@pytest.mark.asyncio
async def test_secao_dados_pessoais_grava_nascimento_tambem_no_aluno(client, repos_setup):
    _, repo = repos_setup
    _seed_aluno_com_dados(repo)
    res = await client.put("/admin/usuarios/aluno-1/dados-pessoais", json={
        "data_nascimento": "1999-01-02", "rg": " 12.345 ", "rg_uf": "sp", "sexo": "feminino",
        "estado_civil": "casado", "naturalidade_cidade": "Recife", "naturalidade_uf": "PE",
        "nacionalidade": "brasileira",
    }, headers=_h())
    assert res.status_code == 200
    assert repo.usuarios["aluno-1"]["rg"] == "12.345"
    assert repo.usuarios["aluno-1"]["rg_uf"] == "SP"
    assert repo.alunos["al-1"]["data_nascimento"] == date(1999, 1, 2)

    ruim = await client.put("/admin/usuarios/aluno-1/dados-pessoais",
                            json={"rg_uf": "XX"}, headers=_h())
    assert ruim.status_code == 422
    futuro = await client.put("/admin/usuarios/aluno-1/dados-pessoais",
                              json={"data_nascimento": "2999-01-01"}, headers=_h())
    assert futuro.status_code == 422


@pytest.mark.asyncio
async def test_secoes_endereco_e_contato_emergencia(client, repos_setup):
    _, repo = repos_setup
    end = await client.put("/admin/usuarios/prof-1/endereco", json={
        "cep": "01001-000", "logradouro": "Praça da Sé", "numero": "1", "bairro": "Sé",
        "cidade": "São Paulo", "uf": "SP",
    }, headers=_h())
    assert end.status_code == 200
    assert repo.usuarios["prof-1"]["cep"] == "01001000"
    assert (await client.put("/admin/usuarios/prof-1/endereco", json={"cep": "123"}, headers=_h())).status_code == 422

    contato = await client.put("/admin/usuarios/prof-1/contato-emergencia", json={
        "contato_emergencia_nome": "João", "contato_emergencia_parentesco": "Irmão",
        "contato_emergencia_telefone": "11 3333-4444",
    }, headers=_h())
    assert contato.status_code == 200
    assert repo.usuarios["prof-1"]["contato_emergencia_telefone"] == "1133334444"


@pytest.mark.asyncio
async def test_secao_acesso_troca_perfil_e_permissoes(client, repos_setup):
    _, repo = repos_setup
    res = await client.put("/admin/usuarios/prof-1/acesso", json={
        "perfil_nome": "aluno", "polo_id": None, "escola_id": None, "permissoes": ["p_chat"],
    }, headers=_h())
    assert res.status_code == 200
    body = res.json()
    assert body["perfil_nome"] == "aluno"
    assert body["permissoes"] == ["p_chat"]
    assert body["status"] == "ativo"
    sem_perfil = await client.put("/admin/usuarios/prof-1/acesso", json={"permissoes": []}, headers=_h())
    assert sem_perfil.status_code == 422


@pytest.mark.asyncio
async def test_vinculo_aluno_matricula_unica(client, repos_setup):
    _, repo = repos_setup
    _seed_aluno_com_dados(repo)
    repo.alunos["al-2"] = {"id": "al-2", "usuario_id": "outro", "numero_matricula": "20249999"}

    dup = await client.put("/admin/usuarios/aluno-1/vinculo-aluno",
                           json={"numero_matricula": "20249999"}, headers=_h())
    assert dup.status_code == 400

    ok = await client.put("/admin/usuarios/aluno-1/vinculo-aluno",
                          json={"numero_matricula": "20240002", "data_nascimento": "2001-03-04"}, headers=_h())
    assert ok.status_code == 200
    assert repo.alunos["al-1"]["numero_matricula"] == "20240002"
    assert repo.usuarios["aluno-1"]["data_nascimento"] == date(2001, 3, 4)
    log = _logs(repo, "aluno_vinculo_atualizado")[-1]
    assert log["entidade"] == "alunos" and log["entidade_id"] == "al-1"

    sem_aluno = await client.put("/admin/usuarios/prof-1/vinculo-aluno",
                                 json={"numero_matricula": "1"}, headers=_h())
    assert sem_aluno.status_code == 404


@pytest.mark.asyncio
async def test_vinculo_professor(client, repos_setup):
    _, repo = repos_setup
    repo.professores["pr-1"] = {"id": "pr-1", "usuario_id": "prof-1", "status": "ativo", "valor_hora_aula": 50}
    res = await client.put("/admin/usuarios/prof-1/vinculo-professor", json={
        "valor_hora_aula": 85.5, "chave_pix": "pix@prof", "status": "ativo",
    }, headers=_h())
    assert res.status_code == 200
    assert repo.professores["pr-1"]["valor_hora_aula"] == 85.5
    assert repo.professores["pr-1"]["chave_pix"] == "pix@prof"
    assert (await client.put("/admin/usuarios/prof-1/vinculo-professor",
                             json={"valor_hora_aula": -1}, headers=_h())).status_code == 422


# ---------- Inativação e exclusão ----------

@pytest.mark.asyncio
async def test_inativar_e_reativar(client, repos_setup):
    _, repo = repos_setup
    repo._tab("refresh_tokens").append({"usuario_id": "prof-1", "revogado_em": None})

    proprio = await client.post("/admin/usuarios/admin-1/inativar", json={"motivo": "teste"}, headers=_h())
    assert proprio.status_code == 400
    sem_motivo = await client.post("/admin/usuarios/prof-1/inativar", json={"motivo": ""}, headers=_h())
    assert sem_motivo.status_code == 422

    res = await client.post("/admin/usuarios/prof-1/inativar",
                            json={"motivo": "Saiu do polo", "status": "bloqueado"}, headers=_h())
    assert res.status_code == 200
    assert res.json()["status"] == "bloqueado"
    assert repo.usuarios["prof-1"]["motivo_inativacao"] == "Saiu do polo"
    assert repo.usuarios["prof-1"]["inativado_por"] == "admin-1"
    assert repo._tab("refresh_tokens")[0]["revogado_em"]
    assert _logs(repo, "usuario_inativado")[-1]["dados_depois"]["sessoes_revogadas"] == 1

    ficha = (await client.get("/admin/usuarios/prof-1/ficha", headers=_h())).json()
    assert ficha["dados"]["motivo_inativacao"] == "Saiu do polo"
    assert ficha["dados"]["inativado_por_nome"] == "Super Admin"

    volta = await client.post("/admin/usuarios/prof-1/reativar", headers=_h())
    assert volta.status_code == 200 and volta.json()["status"] == "ativo"
    assert repo.usuarios["prof-1"]["motivo_inativacao"] is None
    assert (await client.post("/admin/usuarios/prof-1/reativar", headers=_h())).status_code == 409


@pytest.mark.asyncio
async def test_exclusao_so_sem_historico(client, repos_setup):
    _, repo = repos_setup
    _seed_aluno_com_dados(repo)

    com = (await client.get("/admin/usuarios/aluno-1/pode-excluir", headers=_h())).json()
    assert com["pode_excluir"] is False
    assert "notas" in com["motivos"] and "presenças" in com["motivos"]
    bloqueado = await client.delete("/admin/usuarios/aluno-1", headers=_h())
    assert bloqueado.status_code == 409
    assert "inative" in bloqueado.json()["detail"]
    assert "aluno-1" in repo.usuarios

    sem = (await client.get("/admin/usuarios/prof-1/pode-excluir", headers=_h())).json()
    assert sem == {"pode_excluir": True, "motivos": []}
    assert (await client.delete("/admin/usuarios/prof-1", headers=_h())).status_code == 200

    proprio = (await client.get("/admin/usuarios/admin-1/pode-excluir", headers=_h())).json()
    assert proprio["pode_excluir"] is False


# ---------- Histórico ----------

@pytest.mark.asyncio
async def test_historico_abas(client, repos_setup):
    _, repo = repos_setup
    _seed_aluno_com_dados(repo)
    repo.notas[0].update({"id": "n1", "disciplina_nome": "Eclesiologia", "data": datetime(2026, 3, 1)})
    repo._tab("pagamentos").append({"aluno_id": "al-1", "id": "pg1", "descricao": "Mensalidade",
                                    "valor": 100, "status": "pago", "vencimento_em": date(2026, 2, 10)})
    repo._tab("pedidos").append({"solicitante_id": "aluno-1", "id": "pe1", "numero": "P-1", "status": "entregue",
                                 "valor_total": 50, "criado_em": datetime(2026, 1, 5)})
    repo._tab("solicitacoes_transferencia").append({
        "aluno_id": "al-1", "id": "tr1", "tipo": "troca_polo", "status": "aprovada",
        "criado_em": datetime(2026, 4, 1, tzinfo=timezone.utc), "polo_origem_nome": "Polo Centro",
        "polo_destino_nome": "Polo Norte",
    })
    await client.post("/admin/usuarios/aluno-1/inativar", json={"motivo": "Pedido do aluno"}, headers=_h())

    academico = (await client.get("/admin/usuarios/aluno-1/historico/academico", headers=_h())).json()
    grupos = {i["grupo"] for i in academico["items"]}
    assert {"notas", "certificados"} <= grupos

    financeiro = (await client.get("/admin/usuarios/aluno-1/historico/financeiro", headers=_h())).json()
    assert {(i["grupo"], i["valor"]) for i in financeiro["items"]} == {("pagamentos", 100.0), ("pedidos", 50.0)}

    mov = (await client.get("/admin/usuarios/aluno-1/historico/movimentacoes", headers=_h())).json()
    titulos = [i["titulo"] for i in mov["items"]]
    assert "Troca de polo/escola" in titulos
    assert any(i["grupo"] == "status" and i["titulo"] == "usuario_inativado" for i in mov["items"])
    transf = next(i for i in mov["items"] if i["grupo"] == "transferencias")
    assert transf["detalhe"] == "Polo Centro → Polo Norte"

    audit = (await client.get("/admin/usuarios/aluno-1/historico/auditoria?limit=1", headers=_h())).json()
    assert audit["total"] >= 1 and len(audit["items"]) == 1
    assert audit["items"][0]["detalhe"] == "Super Admin"

    invalida = await client.get("/admin/usuarios/aluno-1/historico/outra", headers=_h())
    assert invalida.status_code == 422


# ---------- Transferência aberta pelo admin ----------

@pytest.mark.asyncio
async def test_admin_abre_solicitacao_de_transferencia(client, repos_setup):
    repo = InMemoryTransferenciasRepository()
    set_transferencias_repository(repo)
    try:
        repo.polos.update({
            POLO_A: {"id": POLO_A, "nome": "Polo A", "status": "ativo"},
            POLO_B: {"id": POLO_B, "nome": "Polo B", "status": "ativo"},
        })
        repo.escolas[ESC_B] = {"id": ESC_B, "nome": "Escola B", "polo_id": POLO_B, "status": "ativo"}
        aluno_id = "a0000000-0000-0000-0000-000000000001"
        repo.alunos[aluno_id] = {
            "id": aluno_id, "usuario_id": "aluno-x", "polo_id": POLO_A, "escola_id": None,
            "modalidade": "polo", "status": "ativo", "nome": "Aluno X",
        }
        res = await client.post("/transferencias", json={
            "aluno_id": aluno_id, "tipo": "troca_polo",
            "polo_destino_id": POLO_B, "escola_destino_id": ESC_B, "observacao": "Mudou de cidade",
        }, headers=_h())
        assert res.status_code == 201, res.text
        assert res.json()["status"] == "pendente"
    finally:
        set_transferencias_repository(None)
