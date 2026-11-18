"""Regras de negócio do Chat Interno Moderado."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.modules.auth.roles import perfil_canonico, perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.chat import anexos as anexos_mod
from app.modules.chat import regras
from app.modules.chat.repository import PostgresChatRepository, uuid_valido
from app.modules.chat.schemas import (
    AlterarMembrosIn,
    ConversaAdminOut,
    ConversaDetalheOut,
    ConversaOut,
    ConversasAdminPage,
    CriarGrupoIn,
    EnviarMensagemIn,
    MembroOut,
    MensagemOut,
    RotacaoOut,
    UsuarioResumo,
)
from app.modules.notificacoes import notificar

logger = logging.getLogger(__name__)

_PERFIS_STAFF_TURMA = ("admin", "polo")


def _preview(row: Dict[str, Any]) -> Optional[str]:
    tipo = row.get("ultima_tipo")
    if not tipo:
        return None
    if tipo == "anexo":
        legenda = (row.get("ultima_texto") or "").strip()
        return f"📎 {legenda or row.get('ultima_anexo_nome') or 'Anexo'}"
    return (row.get("ultima_texto") or "")[:160]


class ChatService:
    def __init__(self, repo: PostgresChatRepository) -> None:
        self.repo = repo

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------
    def _conversa_out(self, row: Dict[str, Any]) -> ConversaOut:
        outro = row.get("outro")
        titulo = row.get("titulo") or (outro or {}).get("nome") or "Conversa"
        if row.get("tipo") == "individual" and outro:
            titulo = outro.get("nome") or titulo
        return ConversaOut(
            id=row["id"], tipo=row["tipo"], titulo=titulo, turma_id=row.get("turma_id"), status=row["status"],
            papel=row.get("papel"), nao_lidas=int(row.get("nao_lidas") or 0),
            total_membros=int(row.get("total_membros") or 0),
            outro=UsuarioResumo(**{k: str(v) if k == "id" else v for k, v in outro.items()}) if outro else None,
            ultima_mensagem_em=row.get("ultima_mensagem_em"), ultima_mensagem=_preview(row),
            ultima_remetente_id=row.get("ultima_remetente_id"), criado_em=row.get("criado_em"),
        )

    def _carregar(self, conversa_id: str, user: UserResponse) -> tuple:
        """Retorna (conversa, membro). Não-membro só acessa se for Admin (moderação)."""
        conversa = self.repo.get_conversa(conversa_id)
        if not conversa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada")
        membro = self.repo.get_membro(conversa_id, user.id)
        if membro is None and perfil_do_usuario(user) != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Você não participa desta conversa")
        return conversa, membro

    def _exigir_membro(self, conversa_id: str, user: UserResponse) -> tuple:
        conversa, membro = self._carregar(conversa_id, user)
        if membro is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Você não participa desta conversa")
        return conversa, membro

    def _pode_encerrar(self, conversa: Dict[str, Any], membro: Optional[Dict[str, Any]], user: UserResponse) -> bool:
        return regras.pode_encerrar(perfil=perfil_do_usuario(user), tipo=conversa["tipo"],
                                    papel=(membro or {}).get("papel"), criado_por=conversa.get("criado_por"),
                                    usuario_id=user.id)

    def _pode_gerenciar(self, conversa: Dict[str, Any], membro: Optional[Dict[str, Any]], user: UserResponse) -> bool:
        if conversa["tipo"] != "grupo":
            return False
        if perfil_do_usuario(user) == "admin":
            return True
        return bool(membro) and (membro.get("papel") == "moderador" or str(conversa.get("criado_por")) == str(user.id))

    def _usuarios_validos(self, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        ids = list(dict.fromkeys(str(i) for i in ids if uuid_valido(i)))
        usuarios = self.repo.get_usuarios(ids)
        invalidos = [i for i in ids if i not in usuarios or usuarios[i].get("status") != "ativo"
                     or perfil_canonico(usuarios[i].get("perfil")) not in regras.PERFIS_CHAT]
        if invalidos or not ids:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Há participantes inválidos ou inativos.")
        return usuarios

    def _mensagem_sistema(self, conversa_id: str, user: UserResponse, texto: str) -> None:
        self.repo.inserir_mensagem({
            "conversa_id": conversa_id, "remetente_id": user.id, "tipo": "sistema", "texto": texto,
            "anexo_url": None, "anexo_storage_key": None, "anexo_nome": None, "anexo_mime": None,
            "anexo_tamanho": None,
        })

    def _auditar(self, user: UserResponse, acao: str, conversa_id: str, dados: Optional[Dict[str, Any]],
                 ip: Optional[str]) -> None:
        try:
            self.repo.auditar(usuario_id=user.id, acao=acao, entidade_id=conversa_id, dados=dados, ip=ip)
        except Exception:  # noqa: BLE001 — auditoria não derruba a operação
            logger.exception("Falha ao auditar %s da conversa %s", acao, conversa_id)

    @staticmethod
    def _nome(user: UserResponse) -> str:
        return f"{user.nome} {user.sobrenome or ''}".strip()

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def contatos(self, user: UserResponse, busca: Optional[str], limite: int) -> List[Dict[str, Any]]:
        perfil = perfil_do_usuario(user)
        perfis = [p for p in regras.PERFIS_CHAT if regras.pode_conversar(perfil, p)]
        # Nomes do banco podem estar na forma longa (coordenador_polo / secretario_escola).
        nomes = set(perfis)
        if "polo" in nomes:
            nomes.add("coordenador_polo")
        if "escola" in nomes:
            nomes.add("secretario_escola")
        return self.repo.buscar_contatos(busca=(busca or "").strip() or None, perfis=sorted(nomes),
                                         excluir_id=user.id, limite=limite)

    def turmas(self, user: UserResponse, busca: Optional[str], limite: int) -> List[Dict[str, Any]]:
        return self.repo.turmas_disponiveis(perfil=perfil_do_usuario(user), usuario_id=user.id,
                                            polo_id=user.polo_id, escola_id=user.escola_id,
                                            busca=(busca or "").strip() or None, limite=limite)

    def listar(self, user: UserResponse, tipo: Optional[str], limite: int, offset: int) -> List[ConversaOut]:
        rows = self.repo.listar_conversas_usuario(user.id, tipo=tipo, limite=limite, offset=offset)
        return [self._conversa_out(r) for r in rows]

    def resumo(self, user: UserResponse) -> int:
        return self.repo.contar_nao_lidas(user.id)

    def detalhe(self, conversa_id: str, user: UserResponse) -> ConversaDetalheOut:
        conversa, membro = self._carregar(conversa_id, user)
        row = self.repo.conversa_do_usuario(conversa_id, user.id) if membro else None
        base = self._conversa_out(row) if row else self._conversa_admin_out(conversa)
        membros = [MembroOut(id=m["usuario_id"], nome=m.get("nome") or "", perfil=m.get("perfil"),
                             foto_url=m.get("foto_url"), papel=m["papel"], ultima_leitura_em=m.get("ultima_leitura_em"))
                   for m in self.repo.listar_membros(conversa_id)]
        if not row and conversa["tipo"] == "individual":
            base.titulo = " ↔ ".join(m.nome for m in membros) or base.titulo
        return ConversaDetalheOut(**base.model_dump(), membros=membros,
                                  pode_encerrar=self._pode_encerrar(conversa, membro, user),
                                  pode_gerenciar_membros=self._pode_gerenciar(conversa, membro, user))

    def _conversa_admin_out(self, conversa: Dict[str, Any]) -> ConversaOut:
        return ConversaOut(id=conversa["id"], tipo=conversa["tipo"], titulo=conversa.get("titulo") or "Conversa",
                           turma_id=conversa.get("turma_id"), status=conversa["status"],
                           ultima_mensagem_em=conversa.get("ultima_mensagem_em"), criado_em=conversa.get("criado_em"))

    def mensagens(self, conversa_id: str, user: UserResponse, *, antes: Optional[datetime],
                  depois: Optional[datetime], limite: int) -> List[MensagemOut]:
        self._carregar(conversa_id, user)
        rows = self.repo.listar_mensagens(conversa_id, antes=antes, depois=depois, limite=limite)
        return [MensagemOut(**r) for r in rows]

    # ------------------------------------------------------------------
    # Criação
    # ------------------------------------------------------------------
    def iniciar_individual(self, user: UserResponse, outro_id: str, ip: Optional[str]) -> ConversaDetalheOut:
        if str(outro_id) == str(user.id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Escolha outra pessoa para conversar.")
        outro = self._usuarios_validos([outro_id])[str(outro_id)]
        perfil = perfil_do_usuario(user)
        if not regras.pode_conversar(perfil, outro.get("perfil")):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail="Conversas entre alunos só são permitidas nos grupos das turmas.")

        chave = regras.chave_individual(user.id, outro_id)
        conversa = self.repo.get_conversa_por_chave(chave)
        if conversa is None:
            novo_id = regras.id_da_chave(chave)
            criada = self.repo.criar_conversa(
                {"id": novo_id, "chave": chave, "tipo": "individual", "titulo": None, "turma_id": None,
                 "criado_por": user.id},
                [(user.id, "membro"), (str(outro_id), "membro")],
            )
            conversa = self.repo.get_conversa_por_chave(chave)
            if criada:
                self._auditar(user, "chat_criar_individual", conversa["id"], {"com": outro_id}, ip)
                notificar(titulo=f"Nova conversa de {self._nome(user)}", link=f"/chat?c={conversa['id']}",
                          destino_usuario_id=str(outro_id))
        else:
            # Mesma chave: reaproveita a conversa e todo o histórico.
            self.repo.adicionar_membros(conversa["id"], [(user.id, "membro"), (str(outro_id), "membro")])
            self.repo.reexibir(conversa["id"], user.id)
            if conversa["status"] == "encerrada" and not regras.eh_aluno(perfil):
                self.repo.set_status(conversa["id"], "ativa", user.id)
                self._mensagem_sistema(conversa["id"], user, f"Conversa reaberta por {self._nome(user)}")
                self._auditar(user, "chat_reabrir", conversa["id"], None, ip)
        return self.detalhe(conversa["id"], user)

    def criar_grupo(self, user: UserResponse, dados: CriarGrupoIn, ip: Optional[str]) -> ConversaDetalheOut:
        perfil = perfil_do_usuario(user)
        if regras.eh_aluno(perfil):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Alunos não podem criar grupos.")
        ids = [i for i in dados.membros if str(i) != str(user.id)]
        usuarios = self._usuarios_validos(ids)
        if not regras.grupo_livre_valido([perfil, *(u.get("perfil") for u in usuarios.values())]):
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                detail="Grupos livres aceitam no máximo um aluno. Alunos conversam entre si "
                                       "apenas nos grupos das turmas.")
        chave = regras.chave_grupo_livre()
        conversa_id = regras.id_da_chave(chave)
        self.repo.criar_conversa(
            {"id": conversa_id, "chave": chave, "tipo": "grupo", "titulo": dados.titulo.strip(), "turma_id": None,
             "criado_por": user.id},
            [(user.id, "moderador"), *((uid, "membro") for uid in usuarios)],
        )
        self._mensagem_sistema(conversa_id, user, f"{self._nome(user)} criou o grupo")
        self._auditar(user, "chat_criar_grupo", conversa_id, {"titulo": dados.titulo, "membros": list(usuarios)}, ip)
        for uid in usuarios:
            notificar(titulo=f"Você foi adicionado ao grupo {dados.titulo.strip()}", link=f"/chat?c={conversa_id}",
                      destino_usuario_id=uid)
        return self.detalhe(conversa_id, user)

    def abrir_grupo_turma(self, user: UserResponse, turma_id: str, ip: Optional[str]) -> ConversaDetalheOut:
        turma = self.repo.get_turma(turma_id)
        if not turma:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")
        perfil = perfil_do_usuario(user)
        part = self.repo.participantes_turma(turma)
        todos = set(part["alunos"]) | set(part["professores"]) | set(part["secretaria"])

        autorizado = (
            perfil == "admin"
            or (perfil == "polo" and user.polo_id and str(user.polo_id) == str(turma.get("polo_id")))
            or (perfil == "escola" and user.escola_id and str(user.escola_id) == str(turma.get("escola_id")))
            or str(user.id) in todos
        )
        if not autorizado:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Você não participa desta turma.")

        esperados = [(uid, "moderador") for uid in part["professores"] + part["secretaria"]]
        staff = set(part["professores"]) | set(part["secretaria"])
        esperados += [(uid, "membro") for uid in part["alunos"] if uid not in staff]
        if str(user.id) not in todos:
            esperados.append((str(user.id), "moderador"))  # gestão que abriu o grupo

        chave = regras.chave_turma(turma["id"])
        conversa = self.repo.get_conversa_por_chave(chave)
        if conversa is None:
            conversa_id = regras.id_da_chave(chave)
            if self.repo.criar_conversa(
                {"id": conversa_id, "chave": chave, "tipo": "grupo", "titulo": f"Turma {turma['nome']}",
                 "turma_id": turma["id"], "criado_por": user.id},
                esperados,
            ):
                self._mensagem_sistema(conversa_id, user, "Grupo da turma criado")
                self._auditar(user, "chat_criar_grupo_turma", conversa_id, {"turma_id": turma["id"]}, ip)
            conversa = self.repo.get_conversa_por_chave(chave)
        else:
            self.repo.adicionar_membros(conversa["id"], esperados)
            # Remove quem saiu da turma (alunos sem matrícula ativa, professores sem vínculo ativo).
            sairam = [m["usuario_id"] for m in self.repo.listar_membros(conversa["id"])
                      if (regras.eh_aluno(m.get("perfil")) and m["usuario_id"] not in part["alunos"])
                      or (perfil_canonico(m.get("perfil")) == "professor" and m["usuario_id"] not in part["professores"])]
            self.repo.remover_membros(conversa["id"], sairam)
            self.repo.reexibir(conversa["id"], user.id)
        return self.detalhe(conversa["id"], user)

    def alterar_membros(self, user: UserResponse, conversa_id: str, dados: AlterarMembrosIn,
                        ip: Optional[str]) -> ConversaDetalheOut:
        conversa, membro = self._carregar(conversa_id, user)
        if not self._pode_gerenciar(conversa, membro, user):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Apenas moderadores alteram os participantes.")
        adicionar = [i for i in dados.adicionar if str(i) not in {str(r) for r in dados.remover}]
        usuarios = self._usuarios_validos(adicionar) if adicionar else {}
        if conversa.get("turma_id") and any(regras.eh_aluno(u.get("perfil")) for u in usuarios.values()):
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                detail="Os alunos do grupo da turma vêm das matrículas ativas.")
        if not conversa.get("turma_id"):
            atuais = {m["usuario_id"]: m.get("perfil") for m in self.repo.listar_membros(conversa_id)}
            for rid in dados.remover:
                atuais.pop(str(rid), None)
            atuais.update({uid: u.get("perfil") for uid, u in usuarios.items()})
            if not regras.grupo_livre_valido(atuais.values()):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Grupos livres aceitam no máximo um aluno.")
        novos = self.repo.adicionar_membros(conversa_id, [(uid, "membro") for uid in usuarios])
        removidos = self.repo.remover_membros(conversa_id, dados.remover)
        if novos or removidos:
            self._mensagem_sistema(conversa_id, user, f"{self._nome(user)} alterou os participantes")
            self._auditar(user, "chat_alterar_membros", conversa_id,
                          {"adicionados": novos, "removidos": dados.remover}, ip)
        for uid in novos:
            notificar(titulo=f"Você foi adicionado ao grupo {conversa.get('titulo') or ''}".strip(),
                      link=f"/chat?c={conversa_id}", destino_usuario_id=uid)
        return self.detalhe(conversa_id, user)

    # ------------------------------------------------------------------
    # Mensagens e estado
    # ------------------------------------------------------------------
    def enviar(self, user: UserResponse, conversa_id: str, dados: EnviarMensagemIn) -> MensagemOut:
        conversa, _ = self._exigir_membro(conversa_id, user)
        if conversa["status"] != "ativa":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Esta conversa foi encerrada.")
        anexo = None
        if dados.anexo:
            anexo = anexos_mod.validar_anexo(url=dados.anexo.url, pathname=dados.anexo.pathname,
                                             nome=dados.anexo.nome, mime=dados.anexo.mime,
                                             tamanho=dados.anexo.tamanho)
        msg = self.repo.inserir_mensagem({
            "conversa_id": conversa_id, "remetente_id": user.id, "tipo": "anexo" if anexo else "texto",
            "texto": (dados.texto or "").strip() or None,
            "anexo_url": anexo.url if anexo else None, "anexo_storage_key": anexo.storage_key if anexo else None,
            "anexo_nome": anexo.nome if anexo else None, "anexo_mime": anexo.mime if anexo else None,
            "anexo_tamanho": anexo.tamanho if anexo else None,
        })
        return MensagemOut(**msg, remetente_nome=self._nome(user))

    def marcar_lida(self, user: UserResponse, conversa_id: str) -> None:
        self._exigir_membro(conversa_id, user)
        self.repo.marcar_lida(conversa_id, user.id)

    def encerrar(self, user: UserResponse, conversa_id: str, ip: Optional[str]) -> ConversaDetalheOut:
        conversa, membro = self._carregar(conversa_id, user)
        if not self._pode_encerrar(conversa, membro, user):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Você não pode encerrar esta conversa.")
        if conversa["status"] != "encerrada":
            self._mensagem_sistema(conversa_id, user, f"Conversa encerrada por {self._nome(user)}")
            self.repo.set_status(conversa_id, "encerrada", user.id)
            self._auditar(user, "chat_encerrar", conversa_id, None, ip)
        return self.detalhe(conversa_id, user)

    def reabrir(self, user: UserResponse, conversa_id: str, ip: Optional[str]) -> ConversaDetalheOut:
        conversa, membro = self._carregar(conversa_id, user)
        if not self._pode_encerrar(conversa, membro, user):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Você não pode reabrir esta conversa.")
        if conversa["status"] != "ativa":
            self.repo.set_status(conversa_id, "ativa", user.id)
            self._mensagem_sistema(conversa_id, user, f"Conversa reaberta por {self._nome(user)}")
            self._auditar(user, "chat_reabrir", conversa_id, None, ip)
        return self.detalhe(conversa_id, user)

    def ocultar(self, user: UserResponse, conversa_id: str) -> None:
        self._exigir_membro(conversa_id, user)
        self.repo.ocultar(conversa_id, user.id)

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------
    def admin_listar(self, *, usuario_id: Optional[str], tipo: Optional[str], busca: Optional[str],
                     limite: int, offset: int) -> ConversasAdminPage:
        total, rows = self.repo.listar_todas(usuario_id=usuario_id, tipo=tipo, busca=busca, limite=limite,
                                             offset=offset)
        itens = []
        for r in rows:
            membros = [UsuarioResumo(id=str(m["id"]), nome=m.get("nome") or "", perfil=m.get("perfil"))
                       for m in (r.get("membros") or [])]
            titulo = r.get("titulo") or " ↔ ".join(m.nome for m in membros) or "Conversa"
            itens.append(ConversaAdminOut(id=r["id"], tipo=r["tipo"], titulo=titulo, status=r["status"],
                                          turma_id=r.get("turma_id"), membros=membros,
                                          total_mensagens=int(r.get("total_mensagens") or 0),
                                          ultima_mensagem_em=r.get("ultima_mensagem_em"),
                                          criado_em=r.get("criado_em")))
        return ConversasAdminPage(total=total, itens=itens)

    async def excluir(self, user: UserResponse, conversa_id: str, ip: Optional[str]) -> None:
        conversa = self.repo.get_conversa(conversa_id)
        if not conversa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada")
        membros = [m["usuario_id"] for m in self.repo.listar_membros(conversa_id)]
        refs = self.repo.excluir_conversa(conversa_id)
        self._auditar(user, "chat_excluir", conversa_id,
                      {"chave": conversa["chave"], "titulo": conversa.get("titulo"), "membros": membros,
                       "anexos": len(refs)}, ip)
        await anexos_mod.excluir_anexos(refs)

    def exportar_pdf(self, user: UserResponse, conversa_id: str, ip: Optional[str]) -> tuple:
        from app.modules.chat.pdf import gerar_pdf_conversa

        detalhe = self.detalhe(conversa_id, user)
        mensagens = self.repo.todas_mensagens(conversa_id)
        self._auditar(user, "chat_exportar", conversa_id, {"mensagens": len(mensagens)}, ip)
        return gerar_pdf_conversa(detalhe, mensagens), detalhe

    async def rotacionar(self) -> RotacaoOut:
        resultado = self.repo.rotacionar()
        await anexos_mod.excluir_anexos(resultado["anexos"])
        return RotacaoOut(movidas_para_historico=resultado["movidas_para_historico"],
                          removidas_do_historico=resultado["removidas_do_historico"],
                          anexos_removidos=len(resultado["anexos"]))
