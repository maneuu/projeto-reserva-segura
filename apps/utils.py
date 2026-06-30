"""Utilitários compartilhados entre os apps do projeto."""


def mask_email(email):
    """Mascara um e-mail para registro em log, preservando a auditoria.

    Não devemos gravar e-mails em texto puro nos logs (são dados pessoais —
    LGPD / OWASP A09 "Security Logging Failures"). Esta função mantém apenas
    informação suficiente para auditoria, substituindo o miolo por asteriscos:

        admin@reservasegura.com   -> a***n@reservasegura.com
        jo@email.com              -> j*@email.com
        ""/None                   -> "desconhecido"

    Mantemos o domínio visível porque ele costuma ser útil para investigação
    e, sozinho, não identifica a pessoa. Valores sem "@" são tratados como
    desconhecidos para não vazar nada por engano.
    """
    if not email or "@" not in email:
        return "desconhecido"

    local, _, domain = email.partition("@")

    if len(local) <= 2:
        # Curto demais para mostrar começo e fim sem revelar tudo.
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]

    return f"{masked_local}@{domain}"