# Sistema de Reserva Segura
## Documentação Técnica do Projeto

**Instituto Federal de Educação, Ciência e Tecnologia da Paraíba (IFPB)**
Curso: Tecnologia em Sistemas para Internet

---

| | |
|---|---|
| **Projeto** | Sistema de Reserva Segura — reserva de salas |
| **Tecnologia** | Django 6 · Python 3.13 |
| **Banco de dados** | SQLite (desenvolvimento) |
| **Foco** | Programação segura (OWASP) e conformidade com a LGPD |
| **Data** | Junho de 2026 |

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Objetivos e Requisitos](#2-objetivos-e-requisitos)
3. [Arquitetura e Tecnologias](#3-arquitetura-e-tecnologias)
4. [Estrutura do Projeto](#4-estrutura-do-projeto)
5. [Modelagem de Dados](#5-modelagem-de-dados)
6. [Módulos e Funcionalidades](#6-módulos-e-funcionalidades)
7. [Fluxos de Uso](#7-fluxos-de-uso)
8. [Segurança da Aplicação](#8-segurança-da-aplicação)
9. [Sistema de Logs e Auditoria](#9-sistema-de-logs-e-auditoria)
10. [Instalação e Execução](#10-instalação-e-execução)
11. [Comandos de Gestão](#11-comandos-de-gestão)
12. [Considerações Finais](#12-considerações-finais)

---

## 1. Visão Geral

O **Sistema de Reserva Segura** é uma aplicação web desenvolvida em Django que
permite o gerenciamento e a reserva de salas do IFPB. O sistema foi concebido
com a **segurança da informação como princípio norteador**: cada funcionalidade
foi implementada seguindo as práticas de programação segura recomendadas pela
**OWASP (Open Worldwide Application Security Project)** e os princípios de
proteção de dados pessoais previstos na **LGPD (Lei nº 13.709/2018)**.

A plataforma atende a três perfis de usuário:

- **Usuário comum:** consulta salas disponíveis e gerencia suas próprias reservas.
- **Equipe (staff):** além das funções do usuário comum, cadastra, edita e
  ativa/desativa salas.
- **Administrador (superuser):** acesso total, incluindo o painel administrativo.

O diferencial do projeto está na **defesa em profundidade** — a segurança não é
concentrada em um único ponto, mas distribuída por todas as camadas da aplicação:
da validação da entrada do usuário até a gravação no banco de dados.

---

## 2. Objetivos e Requisitos

### 2.1 Objetivo Geral

Desenvolver um sistema web seguro para reserva de salas, aplicando na prática os
conceitos de programação segura, controle de acesso e proteção de dados.

### 2.2 Requisitos Funcionais

| Código | Requisito | Status |
|--------|-----------|:------:|
| RF01 | Cadastro de usuários com e-mail e senha | ✅ |
| RF02 | Autenticação (login/logout) | ✅ |
| RF03 | Listagem de salas com busca e paginação | ✅ |
| RF04 | Visualização de detalhes da sala | ✅ |
| RF05 | Cadastro de salas (restrito à equipe) | ✅ |
| RF06 | Edição de salas (restrito à equipe) | ✅ |
| RF07 | Ativação/desativação de salas (restrito à equipe) | ✅ |
| RF08 | Criação de reservas com seleção de data/hora | ✅ |
| RF09 | Prevenção de conflito de horários | ✅ |
| RF10 | Cancelamento de reservas | ✅ |
| RF11 | Expiração automática de reservas vencidas | ✅ |
| RF12 | Painel administrativo personalizado | ✅ |

### 2.3 Requisitos Não Funcionais

| Código | Requisito | Status |
|--------|-----------|:------:|
| RNF01 | Validação de todos os dados no servidor | ✅ |
| RNF02 | Senhas armazenadas com hash criptográfico | ✅ |
| RNF03 | Sanitização de entradas contra XSS/injeção | ✅ |
| RNF04 | Registro de eventos (logs de auditoria) | ✅ |
| RNF05 | Proteção de dados pessoais nos logs (LGPD) | ✅ |
| RNF06 | Controle de acesso baseado em papéis | ✅ |
| RNF07 | Interface padronizada com identidade visual IFPB | ✅ |
| RNF08 | Proteção contra condições de corrida (race conditions) | ✅ |

---

## 3. Arquitetura e Tecnologias

### 3.1 Padrão Arquitetural

O projeto segue o padrão **MTV (Model-Template-View)** do Django, uma variação
do clássico MVC, complementado por uma **camada de serviços** (`services.py`)
para isolar operações transacionais complexas.

```
┌─────────────────────────────────────────────────────────┐
│                      NAVEGADOR                            │
│         (HTML + CSS · auto-escape do Django)             │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP (CSRF + cabeçalhos de segurança)
┌───────────────────────────▼─────────────────────────────┐
│                       VIEWS                              │
│   Autenticação · Autorização · Orquestração de fluxo    │
└───────────────────────────┬─────────────────────────────┘
                            │
┌──────────────┬────────────▼───────────┬─────────────────┐
│    FORMS     │       SERVICES         │     MODELS       │
│ Sanitização  │  Transações atômicas   │ Regras negócio  │
│  Validação   │  + travas de linha     │  full_clean()   │
└──────────────┴────────────┬───────────┴─────────────────┘
                            │ ORM (queries parametrizadas)
┌───────────────────────────▼─────────────────────────────┐
│                  BANCO DE DADOS (SQLite)                 │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Tecnologias Utilizadas

| Camada | Tecnologia | Função |
|--------|-----------|--------|
| Backend | **Django 6.0.6** | Framework web full-stack |
| Linguagem | **Python 3.13** | Linguagem de programação |
| Banco de dados | **SQLite** | Persistência (desenvolvimento) |
| Frontend | **HTML5 + CSS3** | Interface do usuário |
| Calendário | **flatpickr** | Seletor visual de data e hora |
| Ícones | **Font Awesome 6** | Iconografia |
| Fontes | **Google Fonts** (Sora, Inter) | Tipografia |
| Logs | **logging** (nativo Python) | Auditoria de eventos |

A escolha de manter **dependências mínimas** (apenas o Django) é, por si só, uma
decisão de segurança: reduz a superfície de ataque por vulnerabilidades em
bibliotecas de terceiros (OWASP A06 — *Vulnerable and Outdated Components*).

---

## 4. Estrutura do Projeto

O projeto é organizado em **três aplicações Django** (`apps/`), cada uma com
responsabilidade única, mais um pacote de configuração (`config/`).

```
projeto-reserva-segura/
├── config/                      # Configuração global do projeto
│   ├── settings.py              # Configurações (segurança, logs, apps)
│   ├── urls.py                  # Roteamento principal + branding do admin
│   ├── views.py                 # View da página inicial
│   ├── wsgi.py / asgi.py        # Servidores de aplicação
│
├── apps/
│   ├── accounts/                # Autenticação e usuários
│   │   ├── models.py            # Modelo User (login por e-mail)
│   │   ├── forms.py             # LoginForm, RegisterForm (validação)
│   │   ├── views.py             # login, register, logout
│   │   └── urls.py
│   │
│   ├── rooms/                   # Gestão de salas
│   │   ├── models.py            # Modelo Room
│   │   ├── forms.py             # RoomForm (sanitização), RoomSearchForm
│   │   ├── views.py             # CRUD + autorização (StaffRequiredMixin)
│   │   ├── admin.py             # Registro no painel admin
│   │   └── urls.py
│   │
│   ├── reservations/            # Reservas
│   │   ├── models.py            # Modelo Reservation + lógica de status
│   │   ├── forms.py             # ReservationForm (validação cruzada)
│   │   ├── services.py          # create_reservation (transação + lock)
│   │   ├── views.py             # listar, criar, detalhar, cancelar
│   │   ├── management/commands/
│   │   │   └── expire_reservations.py   # Comando de expiração (cron)
│   │   └── urls.py
│   │
│   └── utils.py                 # mask_email (proteção de PII)
│
├── templates/                   # Templates HTML (herança de base.html)
│   ├── base.html                # Layout mestre
│   ├── 403.html                 # Página de acesso negado
│   ├── accounts/ · rooms/ · reservations/ · home/ · admin/
│
├── static/                      # CSS, JS e imagens
│   ├── css/ifpb-theme.css       # Design system institucional
│   └── admin/css/ifpb-admin.css # Personalização do painel admin
│
├── docs/                        # Documentação
│   ├── DOCUMENTACAO.md          # Este documento
│   └── SEGURANCA.md             # Documentação detalhada de segurança
│
├── logs/                        # Logs de auditoria (gerado em runtime)
├── requirements.txt             # Dependências (Django==6.0.6)
└── manage.py                    # Utilitário de linha de comando do Django
```

---

## 5. Modelagem de Dados

O sistema possui **três entidades principais**, relacionadas conforme o diagrama
abaixo.

```
┌──────────────────┐         ┌──────────────────┐
│      User        │         │      Room        │
├──────────────────┤         ├──────────────────┤
│ id (PK)          │         │ id (PK)          │
│ email (unique)   │         │ name             │
│ password (hash)  │         │ location         │
│ first_name       │         │ capacity         │
│ last_name        │         │ resources        │
│ is_staff         │         │ description      │
│ is_superuser     │         │ is_active        │
│ is_active        │         │ created_at       │
└────────┬─────────┘         │ updated_at       │
        │                   └────────┬─────────┘
        │                            │
        │      ┌──────────────────┐  │
        │      │   Reservation    │  │
        │      ├──────────────────┤  │
        └─────<│ user (FK)        │  │
              │ room (FK)        │>─┘
              │ start_datetime   │
              │ end_datetime     │
              │ description      │
              │ status           │  ACTIVE / EXPIRED / CANCELED
              │ created_at       │
              │ updated_at       │
              └──────────────────┘
```

### 5.1 Entidade `User` (Usuário)

Modelo de usuário **personalizado**, que usa o **e-mail como identificador**
(o campo `username` padrão do Django foi removido). Herda de `AbstractUser`,
aproveitando todo o sistema de hash de senha e permissões do Django.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `email` | EmailField (único) | Identificador de login |
| `password` | CharField | Senha armazenada como **hash PBKDF2** |
| `first_name`, `last_name` | CharField | Nome do usuário |
| `is_staff` | Boolean | Define acesso às funções de equipe |
| `is_superuser` | Boolean | Define acesso total |

### 5.2 Entidade `Room` (Sala)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `name` | CharField(255) | Nome da sala (único, case-insensitive) |
| `location` | CharField(255) | Localização física |
| `capacity` | PositiveIntegerField | Capacidade (1 a 10.000) |
| `resources` | TextField | Recursos disponíveis |
| `description` | TextField | Descrição livre |
| `is_active` | Boolean | Sala disponível para reserva (*soft delete*) |

> A desativação de salas usa o campo `is_active` em vez de exclusão física
> (*soft delete*), preservando o histórico de reservas associadas.

### 5.3 Entidade `Reservation` (Reserva)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `user` | ForeignKey(User) | Quem reservou |
| `room` | ForeignKey(Room) | Sala reservada |
| `start_datetime` | DateTimeField | Início da reserva |
| `end_datetime` | DateTimeField | Término da reserva |
| `status` | CharField (choices) | `ACTIVE`, `EXPIRED` ou `CANCELED` |
| `description` | TextField | Observações (opcional) |

A entidade `Reservation` concentra a **lógica de negócio mais crítica** do
sistema, descrita na seção 6.3.

---

## 6. Módulos e Funcionalidades

### 6.1 Módulo de Contas (`accounts`)

Responsável pela identidade dos usuários.

**Funcionalidades:**
- **Cadastro:** valida nome (apenas letras), e-mail (formato e unicidade) e
  senha (força mínima, senhas comuns bloqueadas).
- **Login:** autenticação por e-mail com mensagens genéricas (não revela se o
  erro foi no e-mail ou na senha, prevenindo enumeração de usuários).
- **Logout:** executado apenas via `POST` com token CSRF, impedindo logout
  forçado por links maliciosos.

**Destaque de segurança:** o redirecionamento após o login valida a URL de
destino com `url_has_allowed_host_and_scheme()`, prevenindo ataques de
*open redirect*.

### 6.2 Módulo de Salas (`rooms`)

Responsável pelo catálogo de salas.

**Funcionalidades:**
- **Listagem:** com busca por nome, filtro por disponibilidade e paginação
  (10 salas por página). Usuários comuns veem apenas salas ativas.
- **Cadastro/Edição/Desativação:** restritos à equipe via `StaffRequiredMixin`.

**Destaque de segurança:** a filtragem de salas inativas é feita **no banco de
dados** (queryset), não apenas escondendo botões no template. Isso garante que
um usuário comum não consiga acessar uma sala inativa nem digitando a URL
diretamente.

### 6.3 Módulo de Reservas (`reservations`)

O coração do sistema, com a lógica de negócio mais sensível.

**Funcionalidades:**
- **Criação de reserva:** com calendário visual (flatpickr), validação de
  data/hora e prevenção de conflitos.
- **Detecção de conflito:** impede que duas reservas ativas ocupem a mesma sala
  em horários sobrepostos.
- **Cancelamento:** idempotente (cancelar uma reserva já cancelada não causa erro).
- **Expiração automática:** reservas cujo término já passou são marcadas como
  `EXPIRED` automaticamente ao listar/abrir reservas, ou via comando agendado.

**Destaque de segurança — prevenção de condição de corrida:**
A criação de reservas usa **transação atômica com trava de linha**
(`select_for_update()`). Sem isso, dois usuários poderiam reservar a mesma sala
no mesmo horário simultaneamente. A trava serializa as escritas, garantindo que
a verificação de conflito e a criação aconteçam como uma operação indivisível.

```python
def create_reservation(*, user, room, start_datetime, end_datetime, description=""):
    with transaction.atomic():
        # Trava a linha da sala: serializa escritas concorrentes.
        locked_room = Room.objects.select_for_update().get(pk=room.pk)
        if not locked_room.is_active:
            raise ValidationError("Não é permitido reservar sala inativa.")
        if Reservation.has_conflict(room=locked_room, ..., lock=True):
            raise ValidationError("Conflito de horário para esta sala.")
        return Reservation.objects.create(...)
```

---

## 7. Fluxos de Uso

### 7.1 Fluxo de Reserva de Sala

```
1. Usuário faz login
2. Acessa a lista de salas → vê apenas salas ativas
3. Seleciona uma sala disponível
4. Preenche data/hora de início e término (calendário visual)
5. Sistema valida:
   ├─ término depois do início?
   ├─ data no futuro?
   ├─ sala está ativa?
   └─ não há conflito de horário?  ← com trava de linha no banco
6. Reserva criada com status ACTIVE
7. Após o término, status muda automaticamente para EXPIRED
```

### 7.2 Fluxo de Controle de Acesso

```
Requisição a rota protegida
        │
        ▼
  Está autenticado?
   ├─ NÃO → redireciona para /accounts/login/
   └─ SIM
        │
        ▼
  Tem permissão (papel)?
   ├─ NÃO → HTTP 403 (Acesso Negado)
   └─ SIM → executa a ação
```

---

## 8. Segurança da Aplicação

A segurança é o pilar central deste projeto. Esta seção resume os controles
implementados; o detalhamento técnico completo, com trechos de código e
mapeamento linha a linha, está no documento **`docs/SEGURANCA.md`**.

### 8.1 Mapeamento OWASP Top 10 (2021)

| Risco OWASP | Status | Principais controles |
|-------------|:------:|----------------------|
| **A01** Broken Access Control | ✅ | `@login_required`, mixins de papel, filtro no queryset, proteção *open redirect* |
| **A02** Cryptographic Failures | ✅* | Hash PBKDF2+SHA-256; *flags HTTPS recomendadas para produção* |
| **A03** Injection | ✅ | ORM parametrizado, sanitização em 3 camadas, auto-escape |
| **A04** Insecure Design | ✅ | Transações atômicas, validação no model, separação de camadas |
| **A05** Security Misconfiguration | ✅* | Cabeçalhos HTTP de segurança; *endurecimento p/ produção* |
| **A06** Vulnerable Components | ✅* | Dependências mínimas (apenas Django) |
| **A07** Authentication Failures | ✅ | Login por e-mail, hash forte, sem enumeração |
| **A08** Data Integrity Failures | ✅ | CSRF global, cookies HttpOnly |
| **A09** Logging Failures | ✅ | Logs estruturados com PII mascarada |
| **A10** SSRF | ✅ | Não aplicável (sem requisições a URLs externas) |

> \* Mitigado no código; itens marcados possuem recomendações adicionais para o
> ambiente de produção (detalhadas em `SEGURANCA.md`, seção 16).

### 8.2 Principais Controles Implementados

**Validação e Sanitização de Entrada (A03)**
Toda entrada de texto passa por sanitização em múltiplas camadas: remoção de
caracteres de controle, remoção de blocos perigosos (`<script>`, `<iframe>`) e
`strip_tags()`. A validação ocorre **no servidor**, nunca confiando apenas no
navegador.

**Controle de Acesso (A01)**
A autorização é centralizada em funções e mixins reutilizáveis
(`_is_room_manager`, `_can_manage_reservation`, `StaffRequiredMixin`), evitando
inconsistências. Usuários só acessam seus próprios recursos.

**Autenticação Segura (A07)**
Senhas com hash PBKDF2 (870.000 iterações + sal aleatório), validadores de força
e proteção contra enumeração de usuários por mensagens genéricas.

**Proteção contra SQL Injection (A03)**
100% do acesso ao banco usa o **ORM do Django**, que parametriza todas as
queries automaticamente. Nenhuma query SQL é construída por concatenação.

**Proteção CSRF (A08)**
Todas as ações de mutação (criar, editar, cancelar, ativar) exigem token CSRF.
Cookies de sessão e CSRF são marcados como `HttpOnly`.

**Cabeçalhos de Segurança HTTP (A05)**
```python
SECURE_CONTENT_TYPE_NOSNIFF = True      # Anti MIME-sniffing
X_FRAME_OPTIONS = 'DENY'                # Anti-clickjacking
SESSION_COOKIE_HTTPONLY = True          # Cookie de sessão protegido
CSRF_COOKIE_HTTPONLY = True             # Token CSRF protegido
SECURE_REFERRER_POLICY = 'same-origin'  # Controle de Referer
```

---

## 9. Sistema de Logs e Auditoria

O sistema registra eventos relevantes para auditoria, usando o módulo `logging`
nativo do Python. Os logs são gravados simultaneamente no **terminal** e no
arquivo **`logs/application.log`**.

### 9.1 Formato dos Registros

```
2026-06-28 14:32:10 | INFO | Login realizado com sucesso: a***n@reservasegura.com
```

Cada registro contém: data/hora, nível (INFO/WARNING/ERROR) e mensagem.

### 9.2 Eventos Auditados

| Evento | Nível |
|--------|-------|
| Login bem-sucedido / inválido | INFO / WARNING |
| Logout | INFO |
| Cadastro de usuário | INFO |
| Criação / edição / ativação de sala | INFO |
| Criação / cancelamento de reserva | INFO |
| Tentativa de reservar sala inativa | WARNING |
| Tentativa de acesso sem permissão | WARNING |
| Erros inesperados | ERROR (com *stack trace*) |

### 9.3 Proteção de Dados Pessoais (LGPD)

Em conformidade com a LGPD, **endereços de e-mail são mascarados** antes de
serem registrados, através da função `mask_email()`:

```
admin@reservasegura.com  →  a***n@reservasegura.com
jo@email.com             →  j*@email.com
```

O domínio é preservado (útil para auditoria), mas a parte que identifica a
pessoa é ocultada, reduzindo a exposição de dados pessoais nos arquivos de log
(OWASP A09 — *Security Logging Failures*).

---

## 10. Instalação e Execução

### 10.1 Pré-requisitos
- Python 3.13 ou superior
- pip (gerenciador de pacotes do Python)

### 10.2 Passo a Passo

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Aplicar as migrações (cria o banco de dados)
python manage.py migrate

# 4. Criar um usuário administrador
python manage.py createsuperuser

# 5. Iniciar o servidor de desenvolvimento
python manage.py runserver
```

Após iniciar, a aplicação estará disponível em **http://127.0.0.1:8000/** e o
painel administrativo em **http://127.0.0.1:8000/admin/**.

---

## 11. Comandos de Gestão

### 11.1 Expiração de Reservas

O sistema inclui um comando customizado para marcar reservas vencidas como
expiradas. Embora a expiração também ocorra automaticamente ao visualizar as
reservas, este comando permite o agendamento via **cron** (Linux) ou
**Agendador de Tarefas** (Windows), sem depender de filas externas.

```bash
python manage.py expire_reservations
# Saída: "3 reserva(s) expirada(s)."
```

### 11.2 Verificação de Integridade

```bash
python manage.py check          # Verifica problemas no projeto
python manage.py makemigrations # Gera migrações após mudar models
python manage.py migrate        # Aplica migrações ao banco
```

---

## 12. Considerações Finais

O **Sistema de Reserva Segura** demonstra a aplicação prática dos conceitos de
**programação segura** em um projeto Django real. Mais do que entregar as
funcionalidades de reserva de salas, o projeto prioriza **como** essas
funcionalidades são implementadas:

- **8 dos 10 riscos** do OWASP Top 10 são mitigados diretamente no código.
- As **14 categorias** de práticas seguras da OWASP foram consideradas e
  documentadas.
- A **defesa em profundidade** garante que a falha de uma camada seja contida
  pelas demais.
- A **proteção de dados pessoais** atende aos princípios da LGPD.

O projeto também documenta, de forma transparente, as **melhorias recomendadas
para um ambiente de produção** (configuração de HTTPS/HSTS, rate limiting,
Content-Security-Policy, e auditoria de dependências), demonstrando consciência
de que a segurança é um processo contínuo, não um estado final.

### Documentos Complementares

- **`docs/SEGURANCA.md`** — Documentação técnica detalhada de segurança, com
  mapeamento completo das 14 categorias OWASP e do Top 10, trechos de código e
  sugestões de melhoria.
- **`docs/Reserva-Segura-Apresentacao.pptx`** — Apresentação de slides do projeto.

---

*Documento elaborado para fins acadêmicos — IFPB · Tecnologia em Sistemas para Internet · Junho de 2026.*
