"""Serviço de envio de e-mails do NEXUS 2.0."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import List, NamedTuple

from app.core.config import settings

logger = logging.getLogger(__name__)


class SentEmail(NamedTuple):
    to: str
    subject: str
    body: str


# Fila em memória para testes e auditoria local
sent_emails_history: List[SentEmail] = []


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Envia um e-mail em texto puro via SMTP se configurado, ou registra em log/memória."""
    sent_emails_history.append(SentEmail(to=to_email, subject=subject, body=body))

    if not settings.SMTP_HOST or settings.ENVIRONMENT == "test":
        logger.info("[E-MAIL MOCK] Para: %s | Assunto: %s\nCorpo:\n%s", to_email, subject, body)
        return True

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_PORT == 587:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:
        logger.error("Erro ao enviar e-mail para %s: %s", to_email, exc)
        return False


def send_password_reset_email(to_email: str, nome: str, reset_token: str) -> bool:
    """Envia o e-mail de recuperação de senha em português (PT-BR)."""
    nome_exibicao = nome.strip() if nome else "Usuário"
    subject = "NEXUS 2.0 - Recuperação de Senha"
    body = (
        f"Olá, {nome_exibicao}!\n\n"
        "Recebemos uma solicitação para redefinir a sua senha no NEXUS 2.0.\n"
        "Para prosseguir com a redefinição da sua senha, utilize o código de validação (token) abaixo:\n\n"
        f"Token: {reset_token}\n\n"
        f"Este token é válido por {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutos. "
        "Se você não solicitou a alteração de senha, ignore esta mensagem e sua senha permanecerá inalterada.\n\n"
        "Atenciosamente,\n"
        "Equipe NEXUS 2.0"
    )
    return send_email(to_email, subject, body)
