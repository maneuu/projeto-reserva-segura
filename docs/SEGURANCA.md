# Documentação de Segurança — Sistema de Reserva Segura (IFPB)

> Baseado em:
> - **OWASP Secure Coding Practices — Quick Reference Guide** (14 categorias)
> - **OWASP Top 10 — 2021** (A01–A10)

---

## Sumário

1. [Validação dos Dados de Entrada](#1-validação-dos-dados-de-entrada)
2. [Codificação de Dados de Saída](#2-codificação-de-dados-de-saída)
3. [Autenticação e Gerenciamento de Credenciais](#3-autenticação-e-gerenciamento-de-credenciais)
4. [Gerenciamento de Sessões](#4-gerenciamento-de-sessões)
5. [Controle de Acessos](#5-controle-de-acessos)
6. [Práticas de Criptografia](#6-práticas-de-criptografia)
7. [Tratamento de Erros e Log](#7-tratamento-de-erros-e-log)
8. [Proteção de Dados](#8-proteção-de-dados)
9. [Segurança nas Comunicações](#9-segurança-nas-comunicações)
10. [Configuração do Sistema](#10-configuração-do-sistema)
11. [Segurança em Banco de Dados](#11-segurança-em-banco-de-dados)
12. [Gerenciamento de Arquivos](#12-gerenciamento-de-arquivos)
13. [Gerenciamento de Memória](#13-gerenciamento-de-memória)
14. [Práticas Gerais de Codificação](#14-práticas-gerais-de-codificação)
15. [Mapeamento com o OWASP Top 10 — 2021](#15-mapeamento-com-o-owasp-top-10--2021)
16. [Lacunas e Sugestões de Melhoria](#16-lacunas-e-sugestões-de-melhoria)

---

## 1. Validação dos Dados de Entrada

> **Princípio:** toda entrada vinda do usuário é tratada como não confiável. A
> validação acontece no servidor, independentemente de qualquer verificação feita
> no navegador (cliente).

### 1.1 Sanitização de texto livre

**Arquivo:** `apps/rooms/forms.py` — método `_sanitize()`

```python
@staticmethod
def _sanitize(value, *, single_line=True):
    if not value:
        return ""
    value = _CONTROL_CHARS_RE.sub("", value)      # Remove chars de controle
    value = _DANGEROUS_BLOCKS_RE.sub("", value)   # Remove <script>, <iframe>...
    value = strip_tags(value)                      # Remove todas as tags HTML
    if single_line:
        value = value.replace("\r", " ").replace("\n", " ")
    value = _INLINE_WHITESPACE_RE.sub(" ", value)
    return value.strip()
```

A limpeza é aplicada em **três camadas**:

| Passo | O que remove | Por quê |
|---|---|---|
| Regex `_CONTROL_CHARS_RE` | `\x00–\x1f` (exceto tab/LF) | Null bytes e chars invisíveis usados em bypass de filtros e para "envenenar" logs |
| Regex `_DANGEROUS_BLOCKS_RE` | Conteúdo interno de `<script>`, `<style>`, `<iframe>`, `<object>`, `<embed>` | `strip_tags()` remove a tag mas **mantém** o texto; sem isso `<script>evil()</script>` viraria `evil()` |
| `django.utils.html.strip_tags` | Todas as demais tags HTML | Elimina marcação residual antes de gravar no banco |

O mesmo padrão é replicado em `apps/reservations/forms.py` para o campo `description` das reservas.

### 1.2 Normalização de texto de identidade (nomes e e-mail)

**Arquivo:** `apps/accounts/forms.py`

```python
def _normalize_text(value):
    value = _CONTROL_CHARS_RE.sub("", str(value))
    value = strip_tags(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()
```

- **Nomes** (`first_name`, `last_name`): obrigatório que todos os tokens sejam
  alfabéticos (`token.isalpha()`). Rejeita números, tags e caracteres especiais
  que não sejam hifens ou apóstrofes usados em nomes compostos.
- **E-mail**: normalizado para minúsculas (`lower()`) e validado pelo tipo
  `EmailField` do Django (RFC 5322).

### 1.3 Validações de negócio nos formulários

**Arquivo:** `apps/rooms/forms.py`

```python
def clean_capacity(self):
    capacity = self.cleaned_data.get("capacity")
    if capacity < 1:
        raise forms.ValidationError("A capacidade deve ser de pelo menos 1 pessoa.")
    if capacity > 10000:
        raise forms.ValidationError("A capacidade informada é muito alta.")
    return capacity
```

- Limites numéricos explícitos evitam valores absurdos ou negativos.
- Unicidade de nome de sala verificada com `iexact` (case-insensitive):

```python
if Room.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
    self.add_error("name", "Já existe uma sala cadastrada com esse nome.")
```

### 1.4 Validação cruzada de data/hora nas reservas

**Arquivo:** `apps/reservations/models.py` — método `clean()`

```python
def clean(self):
    if self.end_datetime <= self.start_datetime:
        errors["end_datetime"] = "O horário de término precisa ser depois..."
    if self.start_datetime < timezone.now():
        errors["start_datetime"] = "Esse horário já passou..."
    if not self.room.is_active:
        errors["room"] = "Esta sala está inativa..."
    if self.has_conflict(...):
        errors["__all__"] = "Este horário já está ocupado..."
```

A validação está no **model** (chamada via `full_clean()` em `save()`), garantindo
que nunca seja possível gravar um estado inválido no banco — independentemente de
qual formulário ou código chame o `save()`.

### 1.5 Validação do filtro de busca (whitelist de valores)

**Arquivo:** `apps/rooms/forms.py` — `RoomSearchForm`

```python
def clean_status(self):
    status = self.cleaned_data.get("status") or "all"
    if status not in {"all", "available", "unavailable"}:
        raise forms.ValidationError("Selecione um filtro de disponibilidade válido.")
    return status
```

O campo `status` da busca aceita apenas três valores explicitamente definidos
(whitelist). Qualquer outro valor é rejeitado com erro de validação.

---

## 2. Codificação de Dados de Saída

> **Princípio:** todo dado exibido ao usuário deve ser codificado de acordo com
> o contexto de saída, prevenindo que conteúdo malicioso seja interpretado como
> código pelo navegador (XSS).

### 2.1 Auto-escape de templates

O Django aplica **auto-escape HTML** em todos os templates por padrão. Cada
variável `{{ valor }}` é automaticamente codificada:

| Caractere | Saída codificada |
|---|---|
| `<` | `&lt;` |
| `>` | `&gt;` |
| `"` | `&quot;` |
| `'` | `&#x27;` |
| `&` | `&amp;` |

Isso significa que mesmo que um dado contendo `<script>` passe pela validação
e chegue ao banco, ele será exibido como texto puro no navegador — nunca
executado.

### 2.2 Sanitização na entrada (defesa em profundidade)

A sanitização descrita na Seção 1.1 garante que dados perigosos não cheguem
ao banco. O auto-escape garante que, mesmo que chegassem, não seriam executados.
São duas linhas de defesa independentes — qualquer uma que falhe, a outra cobre.

### 2.3 Cabeçalho `X-Content-Type-Options`

**Arquivo:** `config/settings.py`

```python
SECURE_CONTENT_TYPE_NOSNIFF = True
```

Instrui o navegador a não tentar "adivinhar" o tipo de conteúdo de uma resposta
além do `Content-Type` declarado. Previne ataques de MIME-sniffing em que um
arquivo enviado como `text/plain` poderia ser interpretado como `text/html` e
executar scripts.

### 2.4 Cabeçalho `X-Frame-Options`

```python
X_FRAME_OPTIONS = 'DENY'
```

Proíbe que qualquer página do sistema seja embutida em um `<iframe>` de outro
domínio. Previne ataques de **Clickjacking** (OWASP A05).

---

## 3. Autenticação e Gerenciamento de Credenciais

### 3.1 Modelo de usuário personalizado com e-mail como identificador

**Arquivo:** `apps/accounts/models.py`

```python
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
```

- O campo `username` foi **removido**: não há duas identidades possíveis
  (username e e-mail), eliminando o risco de bypass de autenticação por
  conflito entre os dois campos.
- E-mail é único no banco (`unique=True`) e comparado sem distinção de
  maiúsculas/minúsculas no manager (`email__iexact`).

### 3.2 Hash de senha via Django

O Django usa **PBKDF2 com SHA-256** e sal aleatório como algoritmo padrão de
hash de senhas, cumprindo as recomendações do NIST SP 800-63b. A senha nunca é
armazenada em texto puro — o campo `password` sempre contém o hash.

```python
user.set_password(password)  # Aplica o hash antes de gravar
```

### 3.3 Validadores de força de senha

**Arquivo:** `config/settings.py` + `apps/accounts/forms.py`

```python
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "...UserAttributeSimilarityValidator"},
    {"NAME": "...MinimumLengthValidator"},
    {"NAME": "...CommonPasswordValidator"},
    {"NAME": "...NumericPasswordValidator"},
]
```

E no formulário de cadastro:

```python
validate_password(password1, user=user)
```

Os validadores verificam:
- **Similaridade** com o nome/e-mail do usuário
- **Comprimento mínimo** (padrão: 8 caracteres)
- **Senhas comuns** (lista de ~20.000 senhas mais usadas)
- **Somente numérica** (senhas puramente numéricas são bloqueadas)

### 3.4 Autenticação centralizada no backend do Django

**Arquivo:** `apps/accounts/views.py`

```python
user = authenticate(request, email=email, password=password)
if user is not None:
    login(request, user)
```

- `authenticate()` delega ao backend do Django, que compara o hash correto.
- Credenciais inválidas recebem **mensagem genérica** ("Não foi possível
  entrar com as credenciais informadas"), sem revelar se o e-mail existe ou
  se foi a senha que errou — impedindo enumeração de usuários.
- Tentativas inválidas são registradas em log com o e-mail mascarado.

### 3.5 Logout via POST obrigatório

**Arquivo:** `apps/accounts/views.py`

```python
@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")
```

Logout só funciona via `POST` com token CSRF válido. Isso impede ataques de
**logout forçado** (um link malicioso em outra aba não consegue deslogar o
usuário com um simples `GET`).

### 3.6 Normalização de e-mail no manager

```python
def get_by_natural_key(self, email):
    return self.get(email__iexact=email)
```

A comparação ignora maiúsculas/minúsculas, evitando que `Admin@IFPB.edu.br`
e `admin@ifpb.edu.br` sejam tratados como contas diferentes.

---

## 4. Gerenciamento de Sessões

### 4.1 Sessões gerenciadas pelo Django

O Django gerencia sessões com um ID opaco e aleatório (128 bits de entropia)
armazenado em cookie. O sistema não expõe identificadores de sessão na URL.

### 4.2 Proteção do cookie de sessão

**Arquivo:** `config/settings.py`

```python
SESSION_COOKIE_HTTPONLY = True
```

O cookie de sessão é marcado como `HttpOnly`: o JavaScript do navegador não
consegue lê-lo via `document.cookie`. Isso mitiga o impacto de um eventual
XSS — mesmo que código malicioso execute na página, ele não consegue roubar
a sessão.

### 4.3 Renovação da sessão no login

`django.contrib.auth.login()` chama internamente `cycle_key()`, que gera um
**novo ID de sessão** após o login bem-sucedido. Isso previne ataques de
**Session Fixation** (quando um atacante força o usuário a usar um ID
de sessão que o atacante já conhece).

### 4.4 Invalidação total no logout

`django.contrib.auth.logout()` chama `session.flush()`, que **deleta** os
dados da sessão do servidor e gera um novo ID de sessão vazio. A sessão
anterior não pode ser reutilizada após o logout.

---

## 5. Controle de Acessos

### 5.1 Autenticação obrigatória para todas as rotas sensíveis

**Arquivo:** `apps/rooms/views.py`, `apps/reservations/views.py`

```python
@login_required
def room_list(request): ...

@login_required
def reservation_create(request, room_id=None): ...
```

O decorator `@login_required` redireciona usuários não autenticados para a
tela de login antes de qualquer processamento da view. A URL de destino é
preservada no parâmetro `next` para redirecionar após o login.

### 5.2 Autorização por papel (staff/superuser) para gestão de salas

**Arquivo:** `apps/rooms/views.py`

```python
def _is_room_manager(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return _is_room_manager(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied  # 403 para autenticado sem permissão
```

A lógica de autorização é **centralizada** em `_is_room_manager()`. Qualquer
mudança na regra precisa ser feita em um único lugar, eliminando o risco de
inconsistência entre views.

### 5.3 Proteção no queryset (não só no template)

```python
base_queryset = Room.objects.all() if can_manage else Room.objects.filter(is_active=True)
```

Salas inativas não são retornadas ao usuário comum **no banco de dados**. Não
depender apenas de esconder botões no template garante que chamadas diretas à
URL também sejam bloqueadas.

### 5.4 Autorização por propriedade nas reservas

**Arquivo:** `apps/reservations/views.py`

```python
def _can_manage_reservation(user, reservation):
    return user.is_staff or user.is_superuser or reservation.user_id == user.id
```

Um usuário comum só consegue ver/cancelar suas **próprias** reservas. A
verificação usa `user_id` (chave estrangeira primitiva) em vez de `user`,
evitando uma query adicional ao banco.

### 5.5 Resposta diferenciada: 401 vs 403

- Usuário **não autenticado** → redirecionamento para `/accounts/login/`
  (comportamento de `LoginRequiredMixin`).
- Usuário **autenticado sem permissão** → `PermissionDenied` → resposta
  HTTP 403, sem revelar a existência da funcionalidade restrita.

### 5.6 Proteção de redirecionamento aberto (Open Redirect)

**Arquivo:** `apps/accounts/views.py`, `apps/rooms/views.py`

```python
if next_url and url_has_allowed_host_and_scheme(
    next_url,
    allowed_hosts={request.get_host()},
    require_https=request.is_secure(),
):
    return redirect(next_url)
```

O parâmetro `next` (redirecionamento pós-login ou pós-ação) é validado antes
de ser usado. Apenas URLs do **mesmo host** são aceitas, prevenindo que um
atacante forje um link como `/accounts/login/?next=https://site-malicioso.com`
para redirecionar a vítima após o login.

---

## 6. Práticas de Criptografia

### 6.1 Hash de senha com PBKDF2 + SHA-256

O Django usa PBKDF2 com 870.000 iterações (padrão Django 5.x) e um sal
aleatório por usuário. O número de iterações é atualizado a cada nova versão
do Django e os hashes antigos são atualizados automaticamente no próximo login.

### 6.2 Geração de IDs de sessão e tokens CSRF

O Django usa o módulo `secrets` (Python) para gerar IDs de sessão e tokens
CSRF com entropia criptograficamente segura (128 bits), conforme recomendado
pelo NIST SP 800-63b.

### 6.3 SECRET_KEY

**Arquivo:** `config/settings.py`

```python
SECRET_KEY = 'django-insecure-...'
```

> ⚠️ **Lacuna identificada — ver Seção 16.1**

A `SECRET_KEY` é usada internamente pelo Django para assinar cookies de sessão,
tokens CSRF e tokens de redefinição de senha. Em produção, ela deve ser única,
secreta e carregada de variável de ambiente.

---

## 7. Tratamento de Erros e Log

### 7.1 Mensagens de erro genéricas ao usuário

Erros técnicos nunca chegam ao usuário. As views capturam exceções e exibem
mensagens genéricas:

```python
except Exception:
    logger.exception("Erro inesperado ao criar reserva: user=%s room=%s", ...)
    form.add_error(None, "Não foi possível criar a reserva no momento.")
```

O stack trace completo vai para o log (visível ao desenvolvedor/operador),
mas o usuário vê apenas uma mensagem amigável sem detalhes técnicos
(OWASP A05 — Security Misconfiguration).

### 7.2 Sistema de logs estruturado

**Arquivo:** `config/settings.py`

```python
LOGGING = {
    'formatters': {
        'simple': {
            'format': '{asctime} | {levelname} | {message}',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
        'file': {
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'application.log',
            'encoding': 'utf-8',
        },
    },
}
```

Logs vão simultaneamente para o terminal (desenvolvimento) e para
`logs/application.log` (auditoria persistente).

### 7.3 Eventos auditados

| Evento | Nível | Arquivo |
|---|---|---|
| Login bem-sucedido | INFO | `accounts/views.py` |
| Login inválido | WARNING | `accounts/views.py` |
| Logout | INFO | `accounts/views.py` |
| Cadastro de usuário | INFO | `accounts/views.py` |
| Sala criada | INFO | `rooms/views.py` |
| Sala editada | INFO | `rooms/views.py` |
| Sala ativada/desativada | INFO | `rooms/views.py` |
| Reserva criada | INFO | `reservations/views.py` |
| Reserva cancelada | INFO | `reservations/views.py` |
| Tentativa de reservar sala inativa | WARNING | `reservations/views.py` |
| Tentativa de acesso sem permissão (reserva) | WARNING | `reservations/views.py` |
| Busca de salas inválida | WARNING | `rooms/views.py` |
| Erros inesperados | ERROR + traceback | todas as views |

### 7.4 Mascaramento de PII nos logs

**Arquivo:** `apps/utils.py`

```python
def mask_email(email):
    local, _, domain = email.partition("@")
    masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"
```

E-mails são mascarados antes de qualquer registro em log:

```
admin@reservasegura.com  →  a***n@reservasegura.com
jo@email.com             →  j*@email.com
```

Isso está em conformidade com o princípio de minimização de dados da **LGPD
(Lei 13.709/2018)** e com OWASP A09 — Security Logging and Monitoring Failures.

### 7.5 `logger.exception()` para erros graves

```python
except Exception:
    logger.exception("Erro ao criar sala | usuário=%s", mask_email(...))
```

`logger.exception()` registra automaticamente o **stack trace completo** junto
com a mensagem, sem precisar capturar `exc_info=True` manualmente.

---

## 8. Proteção de Dados

### 8.1 Senhas nunca armazenadas em texto puro

Conforme descrito na Seção 3.2, todas as senhas passam por `set_password()`,
que aplica hash antes de qualquer persistência.

### 8.2 Dados pessoais mínimos coletados

O sistema coleta apenas: nome, sobrenome, e-mail e senha. Não são solicitados
CPF, endereço, telefone ou quaisquer dados sensíveis desnecessários ao
funcionamento do sistema (princípio da **minimização de dados** — LGPD Art. 6º).

### 8.3 E-mails mascarados nos logs

Tratado na Seção 7.4. O domínio é preservado (útil para auditoria) mas a
parte local é truncada, reduzindo a exposição de PII em logs.

### 8.4 Isolamento de reservas por usuário

Usuários comuns só visualizam **suas próprias reservas**. O filtro é aplicado
no queryset (banco de dados), não apenas na camada de apresentação:

```python
reservations = Reservation.objects.filter(user=request.user)
```

### 8.5 `*.log` no `.gitignore`

O arquivo `.gitignore` contém `*.log`, garantindo que logs de aplicação
(que podem conter dados de auditoria) nunca sejam acidentalmente versionados
e expostos em repositórios públicos.

---

## 9. Segurança nas Comunicações

### 9.1 `SECURE_REFERRER_POLICY`

**Arquivo:** `config/settings.py`

```python
SECURE_REFERRER_POLICY = 'same-origin'
```

Controla o cabeçalho `Referrer-Policy`. Com `same-origin`, o navegador envia
o cabeçalho `Referer` apenas para requisições ao mesmo domínio. Para requisições
externas (links para outros sites), o cabeçalho é omitido, evitando que URLs
internas (com parâmetros potencialmente sensíveis) vazem para terceiros.

### 9.2 Recomendações para produção

> ⚠️ As configurações abaixo são necessárias quando o sistema rodar com HTTPS.
> Ver Seção 16 para detalhes.

```python
SECURE_SSL_REDIRECT = True           # Força HTTPS
SESSION_COOKIE_SECURE = True         # Cookie de sessão só via HTTPS
CSRF_COOKIE_SECURE = True            # Cookie CSRF só via HTTPS
SECURE_HSTS_SECONDS = 31536000       # HTTP Strict Transport Security (1 ano)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

---

## 10. Configuração do Sistema

### 10.1 Middleware de segurança

**Arquivo:** `config/settings.py`

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',  # Cabeçalhos HTTP de segurança
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',      # Proteção CSRF global
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Anti-Clickjacking
]
```

`SecurityMiddleware` é o responsável por aplicar automaticamente os cabeçalhos
`X-Content-Type-Options`, `Referrer-Policy` e redirecionamento HTTPS quando
configurado.

### 10.2 Proteção CSRF global

`CsrfViewMiddleware` verifica um token anti-CSRF em **todo** formulário que usa
método `POST`, `PUT`, `PATCH` ou `DELETE`. O token é único por sessão, rotacionado
a cada login e não está disponível para JavaScript via `HttpOnly`.

### 10.3 Pasta de logs criada automaticamente

**Arquivo:** `config/settings.py`

```python
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)
```

A pasta `logs/` é criada na inicialização da aplicação. Isso garante que o
servidor nunca falhe ao tentar escrever logs em uma pasta inexistente — um
erro silencioso que poderia deixar o sistema sem auditoria.

### 10.4 Painel administrativo personalizado e nomeado

**Arquivo:** `config/urls.py`

```python
admin.site.site_header = "IFPB · Reserva Segura"
admin.site.site_title  = "Administração | Reserva Segura IFPB"
admin.site.index_title = "Painel administrativo"
```

O painel administrativo do Django está disponível em `/admin/` e protegido
pelo próprio sistema de autenticação do Django (requer `is_staff=True`).

> ⚠️ **Lacuna identificada — ver Seção 16.5:** em produção, o endereço do
> painel deve ser alterado para algo diferente de `/admin/`.

### 10.5 `DEBUG = True` apenas em desenvolvimento

> ⚠️ **Lacuna crítica — ver Seção 16.1:** `DEBUG = True` expõe stack traces
> completos ao usuário em caso de erro. Deve ser `False` em produção.

### 10.6 Segurança no formulário de salas — usado também no admin

**Arquivo:** `apps/rooms/admin.py`

```python
class RoomAdmin(admin.ModelAdmin):
    form = RoomForm  # reutiliza o mesmo formulário sanitizado das views
```

O formulário com sanitização e validação das views é **reutilizado** no painel
administrativo. Administradores também passam pelas mesmas validações,
garantindo consistência (RNF03 / OWASP A03).

---

## 11. Segurança em Banco de Dados

### 11.1 ORM do Django — prevenção de SQL Injection

Todo acesso ao banco de dados usa o ORM do Django, que **parametriza
automaticamente** todas as queries. Nenhuma string SQL é construída por
concatenação manual.

```python
# CORRETO — o ORM parametriza o valor de 'name':
Room.objects.filter(name__iexact=name)

# ERRADO — nunca usado no projeto:
cursor.execute(f"SELECT * FROM rooms WHERE name = '{name}'")
```

### 11.2 Transação atômica na criação de reservas

**Arquivo:** `apps/reservations/services.py`

```python
def create_reservation(*, user, room, ...):
    with transaction.atomic():
        locked_room = Room.objects.select_for_update().get(pk=room.pk)
        if Reservation.has_conflict(room=locked_room, ..., lock=True):
            raise ValidationError("Conflito de horário para esta sala.")
        return Reservation.objects.create(...)
```

- `transaction.atomic()` garante que a verificação de conflito e a criação da
  reserva aconteçam como **uma operação indivisível** no banco.
- `select_for_update()` adquire um **lock de linha** na sala durante a
  transação, evitando a condição de corrida onde dois usuários criam reservas
  simultâneas para o mesmo horário.

### 11.3 Transação atômica no cancelamento

**Arquivo:** `apps/reservations/views.py`

```python
with transaction.atomic():
    reservation = get_object_or_404(
        Reservation.objects.select_for_update()...,
        pk=reservation_id,
    )
    if reservation.cancel(): ...
```

O cancelamento também usa `select_for_update()`, garantindo que o status seja
lido e alterado de forma segura em ambiente com múltiplos acessos simultâneos.

### 11.4 `full_clean()` chamado no `save()` do modelo

**Arquivo:** `apps/reservations/models.py`

```python
def save(self, *args, **kwargs):
    self.full_clean()
    return super().save(*args, **kwargs)
```

`full_clean()` executa todos os validadores do model antes de gravar, incluindo
as verificações de conflito de horário e sala ativa. Isso garante que nenhum
dado inválido chegue ao banco — mesmo que alguém chame `save()` diretamente,
sem passar pelo formulário.

### 11.5 `update_fields` para atualizações parciais seguras

**Arquivo:** `apps/rooms/views.py`

```python
room.save(update_fields=["is_active", "updated_at"])
```

Ao ativar/desativar uma sala, apenas os campos necessários são atualizados. Isso
evita sobrescrever acidentalmente outros campos com valores desatualizados do
objeto em memória.

---

## 12. Gerenciamento de Arquivos

### 12.1 Sem upload de arquivos

O sistema **não implementa upload de arquivos de usuário**. Formulários de salas
e reservas aceitam apenas texto. Isso elimina toda uma classe de vulnerabilidades:
upload de arquivos executáveis, path traversal, armazenamento de malware, etc.

### 12.2 Configuração de media e static

```python
MEDIA_URL  = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

`STATIC_ROOT` e `MEDIA_ROOT` são diretórios no sistema de arquivos do servidor,
fora da raiz web. Em produção, arquivos estáticos devem ser servidos por um
servidor HTTP (nginx/Apache), não pelo Django.

### 12.3 Logs fora do controle de versão

`logs/application.log` é criado em `BASE_DIR / 'logs'`, que está no
`.gitignore`. O conteúdo dos logs nunca é versionado nem enviado ao repositório.

---

## 13. Gerenciamento de Memória

### 13.1 Gerenciamento automático pelo Python/Django

Python usa coleta de lixo automática com contagem de referências. O Django
gerencia o ciclo de vida de objetos de requisição, querysets e conexões de banco
de dados automaticamente, sem necessidade de alocação/desalocação manual.

### 13.2 Prevenção de N+1 queries com `select_related`

**Arquivo:** `apps/reservations/views.py`

```python
Reservation.objects.select_related("room", "user").order_by("-start_datetime")
```

`select_related` faz JOIN no banco de dados em vez de executar uma query por
objeto acessado, evitando o padrão N+1 que pode causar consumo excessivo de
memória e degradação de desempenho sob carga.

### 13.3 Paginação para limitar o volume de dados em memória

**Arquivo:** `apps/rooms/views.py`

```python
paginator = Paginator(rooms, 10)
page_obj = paginator.get_page(request.GET.get("page"))
```

A listagem de salas é paginada em grupos de 10. O Django avalia o queryset
de forma lazy (preguiçosa) e só carrega a página atual em memória, independente
do total de registros.

### 13.4 Limite no histórico exibido de reservas

```python
room_schedule = Reservation.objects.filter(...).order_by("start_datetime")[:10]
```

Ao criar uma reserva, o sistema exibe no máximo 10 reservas existentes da sala.
O corte (`:10`) é aplicado na query SQL (`LIMIT 10`), não após carregar todos os
registros.

---

## 14. Práticas Gerais de Codificação

### 14.1 Princípio do menor privilégio

- Usuários comuns: podem listar salas e gerenciar apenas suas próprias reservas.
- Staff: gerencia salas (criar, editar, ativar/desativar).
- Superuser: acesso total, incluindo painel administrativo.
- Nenhum usuário tem mais permissões do que o necessário para sua função.

### 14.2 Validação no servidor como fonte única de verdade

Atributos `min`, `max` e `maxlength` nos widgets HTML são apenas auxílios de
UX no navegador. A validação real acontece nos formulários e models do Django
(servidor), que não podem ser contornados pelo usuário.

### 14.3 Separação de responsabilidades

| Camada | Responsabilidade |
|---|---|
| `forms.py` | Sanitização e validação da entrada do usuário |
| `models.py` | Regras de negócio e integridade dos dados |
| `services.py` | Operações transacionais complexas (criação de reserva com lock) |
| `views.py` | Autenticação, autorização e orquestração |
| `utils.py` | Funções auxiliares compartilhadas (ex.: `mask_email`) |
| `templates/` | Apresentação — sem lógica de negócio |

### 14.4 Lógica de autorização centralizada

Regras de acesso estão em funções/mixins únicos, não duplicadas por view:

```python
def _is_room_manager(user): ...         # salas
def _can_manage_reservation(user, r):  # reservas
class StaffRequiredMixin(...): ...      # CBVs de salas
```

### 14.5 Sem dependências externas de segurança

O sistema usa apenas módulos nativos do Python (`logging`, `re`, `hashlib`) e
os recursos de segurança integrados do Django, reduzindo a superfície de ataque
por vulnerabilidades em dependências de terceiros.

### 14.6 Expiração automática de reservas

**Arquivo:** `apps/reservations/models.py`

```python
@classmethod
def expire_overdue(cls):
    return cls.objects.filter(
        status=ReservationStatus.ACTIVE,
        end_datetime__lt=timezone.now(),
    ).update(status=ReservationStatus.EXPIRED, updated_at=timezone.now())
```

Reservas passadas são marcadas como `EXPIRED` automaticamente. Isso garante
integridade dos dados e evita que o sistema mostre estados incorretos, o que
poderia ser explorado para reservar salas "fantasma" ainda marcadas como ativas.

---

## 15. Mapeamento com o OWASP Top 10 — 2021

| # | Risco | Status | Onde implementado |
|---|---|---|---|
| **A01** | Broken Access Control | ✅ Mitigado | `@login_required`, `StaffRequiredMixin`, `_can_manage_reservation`, filtros no queryset |
| **A02** | Cryptographic Failures | ✅ Mitigado / ⚠️ Parcial | PBKDF2+SHA-256 para senhas; faltam flags HTTPS em produção (ver 16.2) |
| **A03** | Injection | ✅ Mitigado | ORM parametrizado; sanitização multicamada (`_sanitize`, `strip_tags`, regex) |
| **A04** | Insecure Design | ✅ Mitigado | Transações atômicas com `select_for_update`, validação no model, separação de camadas |
| **A05** | Security Misconfiguration | ✅ Mitigado / ⚠️ Parcial | Cabeçalhos HTTP configurados; faltam configs de produção (`DEBUG=False`, HSTS) |
| **A06** | Vulnerable & Outdated Components | ⚠️ Sem controle formal | Sem `pip-audit` ou Dependabot automatizado (ver 16.3) |
| **A07** | Identification & Authentication Failures | ✅ Mitigado | Modelo de usuário por e-mail, hash PBKDF2, sem enumeração, logout via POST |
| **A08** | Software & Data Integrity Failures | ✅ Mitigado | CSRF em todas as ações de mutação, logout e cancelamento via POST |
| **A09** | Security Logging & Monitoring Failures | ✅ Mitigado | Logs estruturados com nível, timestamp, usuário (mascarado) e operação |
| **A10** | Server-Side Request Forgery (SSRF) | ✅ N/A | O sistema não faz requisições HTTP a URLs controladas pelo usuário |

---

## 16. Lacunas e Sugestões de Melhoria

As seções abaixo listam o que **ainda não está implementado** e o que é
**necessário antes de ir para produção**.

---

### 16.1 `DEBUG=False` e `SECRET_KEY` por variável de ambiente (CRÍTICO)

**Risco:** OWASP A05 — Security Misconfiguration

Com `DEBUG=True` em produção, qualquer erro HTTP 500 exibe um stack trace
completo ao usuário, incluindo variáveis locais, configurações e caminhos do
servidor.

**O que fazer:**

Criar um arquivo `.env` (já no `.gitignore`) e carregar as variáveis sensíveis:

```python
# config/settings.py
import os

DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
```

```bash
# .env (nunca commitar)
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<chave-aleatoria-de-50+-caracteres>
DJANGO_ALLOWED_HOSTS=reservasegura.ifpb.edu.br
```

---

### 16.2 Flags de segurança para produção com HTTPS (CRÍTICO)

**Risco:** OWASP A02 — Cryptographic Failures

Sem essas flags, cookies de sessão e CSRF podem viajar em texto claro mesmo
que o servidor suporte HTTPS.

**O que fazer:**

```python
# config/settings.py — ativar apenas quando HTTPS estiver configurado
if not DEBUG:
    SECURE_SSL_REDIRECT          = True   # Redireciona HTTP → HTTPS
    SESSION_COOKIE_SECURE        = True   # Cookie de sessão só em HTTPS
    CSRF_COOKIE_SECURE           = True   # Cookie CSRF só em HTTPS
    SECURE_HSTS_SECONDS          = 31536000  # HSTS por 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD          = True
```

---

### 16.3 Auditoria de dependências (pip-audit / Safety)

**Risco:** OWASP A06 — Vulnerable & Outdated Components

O `requirements.txt` atual não fixa versões de forma precisa e não há
verificação automática de CVEs em dependências.

**O que fazer:**

```bash
# Instalar e executar o auditor
pip install pip-audit
pip-audit

# Gerar requirements com versões fixas (pinning)
pip freeze > requirements.txt
```

Adicionalmente, configurar o **GitHub Dependabot** no repositório para
receber alertas automáticos de vulnerabilidades em dependências.

---

### 16.4 Proteção contra força bruta no login

**Risco:** OWASP A07 — Identification & Authentication Failures

Atualmente não há limite de tentativas de login. Um atacante pode tentar
senhas indefinidamente sem ser bloqueado.

**O que fazer (opção simples, sem biblioteca externa):**

```python
# apps/accounts/views.py
from django.core.cache import cache

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutos

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "")
        cache_key = f"login_attempts:{email}"
        attempts = cache.get(cache_key, 0)

        if attempts >= MAX_ATTEMPTS:
            return render(request, "accounts/login.html", {
                "form": form,
                "locked": True,
            })

        user = authenticate(...)
        if user is None:
            cache.set(cache_key, attempts + 1, LOCKOUT_SECONDS)
        else:
            cache.delete(cache_key)
            login(request, user)
```

**Opção com biblioteca:** instalar `django-axes` (bem mantida, integração
nativa com Django).

---

### 16.5 Mover o painel administrativo de `/admin/`

**Risco:** OWASP A05 — Security Misconfiguration

O endereço padrão `/admin/` é amplamente conhecido e é alvo de scanners
automatizados e ataques de força bruta.

**O que fazer:**

```python
# config/urls.py
urlpatterns = [
    path('painel-ifpb-reservas/', admin.site.urls),  # URL não óbvia
    ...
]
```

---

### 16.6 Política de senhas com prazo de expiração

**Risco:** OWASP A07 — Identification & Authentication Failures

O sistema valida a força da senha no cadastro, mas não há mecanismo para
forçar a troca periódica de senha nem para invalidar senhas comprometidas.

**O que fazer:**

Adicionar um campo `password_changed_at` ao modelo `User` e criar um
middleware que redirecione o usuário para a tela de troca de senha quando
o prazo expirar (ex.: 90 dias para contas de staff).

---

### 16.7 Cabeçalho `Content-Security-Policy (CSP)`

**Risco:** OWASP A03 — XSS residual mesmo com auto-escape

O CSP instrui o navegador a só carregar recursos (scripts, estilos, fontes)
de origens explicitamente autorizadas, adicionando uma camada extra contra XSS.

**O que fazer:**

```python
# config/settings.py — usando django-csp
INSTALLED_APPS += ["csp"]
MIDDLEWARE.insert(1, "csp.middleware.CSPMiddleware")

CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC  = ("'self'", "cdn.jsdelivr.net")
CSP_STYLE_SRC   = ("'self'", "fonts.googleapis.com", "cdnjs.cloudflare.com", "cdn.jsdelivr.net")
CSP_FONT_SRC    = ("'self'", "fonts.gstatic.com", "cdnjs.cloudflare.com")
CSP_IMG_SRC     = ("'self'", "data:")
```

---

### 16.8 Testes automatizados de segurança

**Risco:** regressões de segurança podem ser introduzidas silenciosamente.

**O que fazer:**

Adicionar testes que cubram explicitamente os controles de segurança:

```python
# apps/reservations/tests.py
def test_usuario_nao_cancela_reserva_alheia(self):
    """Garante que o controle de acesso da view de cancelamento funciona."""
    self.client.login(email=self.outro_usuario.email, password="senha123")
    resp = self.client.post(f"/reservations/{self.reserva.id}/cancel/")
    self.assertEqual(resp.status_code, 302)  # Redireciona, não cancela
    self.reserva.refresh_from_db()
    self.assertEqual(self.reserva.status, "ACTIVE")  # Permanece ativa

def test_acesso_sala_inativa_retorna_404_para_usuario_comum(self):
    self.sala.is_active = False
    self.sala.save()
    resp = self.client.get(f"/rooms/{self.sala.id}/")
    self.assertEqual(resp.status_code, 404)
```

---

*Documento gerado em 2026-06-29 — Sistema de Reserva Segura — IFPB · Sistemas para Internet*
