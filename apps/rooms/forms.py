import re

from django import forms
from django.utils.html import strip_tags

from .models import Room

# ---------------------------------------------------------------------------
# Expressões regulares usadas na sanitização das entradas.
# ---------------------------------------------------------------------------
# Caracteres de controle ASCII (exceto tab \x09, newline \x0a e carriage
# return \x0d, que podem ser legítimos em texto multilinha). Esses caracteres
# "invisíveis" não têm uso em um nome/localização e às vezes aparecem em
# tentativas de injeção ou para "quebrar" logs/exportações.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Remove blocos <script>...</script> e <style>...</style> INCLUINDO seu
# conteúdo interno. Isso é necessário porque strip_tags() apenas remove as
# tags (os delimitadores < >), mas preserva o texto entre elas — então
# "<script>evil()</script>" viraria "evil()" sem esta etapa.
_DANGEROUS_BLOCKS_RE = re.compile(
    r"<(script|style|iframe|object|embed)[^>]*>.*?</(script|style|iframe|object|embed)>",
    re.IGNORECASE | re.DOTALL,
)

# Sequências de espaços/tabs "horizontais". Servem para colapsar vários
# espaços seguidos em um único (ex.: "Sala     201" -> "Sala 201").
_INLINE_WHITESPACE_RE = re.compile(r"[ \t]+")


class RoomForm(forms.ModelForm):
    """Formulário de cadastro/edição de salas.

    Por ser um ``ModelForm``, ele:
      1. Gera os campos automaticamente a partir do model ``Room``.
      2. Aplica as validações do model (tipos, max_length, etc.).
      3. Funciona junto com a tag {% csrf_token %} do template, herdando a
         proteção CSRF nativa do Django.

    Além disso, centralizamos aqui a SANITIZAÇÃO das entradas como uma
    camada extra de defesa (defesa em profundidade) contra XSS/injeção
    (RNF03 / OWASP A03). O Django já faz auto-escape na SAÍDA dos templates;
    aqui limpamos a ENTRADA antes de gravar no banco.
    """

    class Meta:
        # 'model' e 'fields' dizem ao ModelForm quais campos do banco
        # devem virar campos do formulário.
        model = Room
        fields = [
            "name",
            "location",
            "capacity",
            "resources",
            "description",
            "is_active",
        ]
        # 'widgets' personaliza o HTML renderizado de cada campo (classes CSS,
        # limites do input, etc.). O 'maxlength' e 'min'/'max' aqui são apenas
        # auxílio no navegador — a validação real acontece no servidor (abaixo).
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "input-control", "maxlength": "255", "autocomplete": "off"}
            ),
            "location": forms.TextInput(
                attrs={"class": "input-control", "maxlength": "255", "autocomplete": "off"}
            ),
            "capacity": forms.NumberInput(
                attrs={"class": "input-control", "min": "1", "max": "10000"}
            ),
            "resources": forms.Textarea(attrs={"class": "input-control", "rows": 3}),
            "description": forms.Textarea(attrs={"class": "input-control", "rows": 4}),
            "is_active": forms.CheckboxInput(attrs={"class": "input-checkbox"}),
        }

    @staticmethod
    def _sanitize(value, *, single_line=True):
        """Função auxiliar que limpa uma string de texto.

        Passos executados, na ordem:
          1. Se o valor for vazio/None, devolve string vazia.
          2. Remove caracteres de controle: o parser HTML do Django pode ter
             comportamento indefinido com null bytes (\x00), então fazemos
             essa limpeza ANTES de chamar strip_tags.
          3. Remove blocos perigosos (script/style/iframe) COM seu conteúdo,
             pois strip_tags só retira os delimitadores < >, mantendo o texto
             interno (ex.: "<script>evil()</script>" → "evil()" sem esta etapa).
          4. ``strip_tags`` remove o markup HTML restante (tags comuns como
             <b>, <p> etc.), preservando apenas o texto.
          5. Em campos de uma única linha (nome, localização), troca quebras
             de linha por espaço — assim o usuário não consegue inserir
             múltiplas linhas onde só deveria haver uma.
          6. Colapsa espaços repetidos em um só.
          7. ``strip`` remove espaços sobrando nas pontas.
        """
        if not value:
            return ""

        # Passo 2: controle primeiro (antes do parser HTML).
        value = _CONTROL_CHARS_RE.sub("", value)
        # Passo 3: blocos perigosos com conteúdo.
        value = _DANGEROUS_BLOCKS_RE.sub("", value)
        # Passo 4: tags restantes (mantém texto entre elas).
        value = strip_tags(value)

        if single_line:
            value = value.replace("\r", " ").replace("\n", " ")

        value = _INLINE_WHITESPACE_RE.sub(" ", value)
        return value.strip()

    # -----------------------------------------------------------------------
    # Métodos clean_<campo>: o Django chama automaticamente um destes para
    # cada campo durante a validação. O valor retornado substitui o valor
    # original em form.cleaned_data. É o lugar idiomático para sanitizar
    # e validar um campo isoladamente.
    # -----------------------------------------------------------------------
    def clean_name(self):
        # Sanitiza primeiro, depois valida o tamanho do resultado já limpo.
        name = self._sanitize(self.cleaned_data.get("name"))
        if len(name) < 3:
            # ValidationError vira uma mensagem de erro exibida ao lado do campo.
            raise forms.ValidationError(
                "O nome da sala deve ter pelo menos 3 caracteres."
            )
        return name

    def clean_location(self):
        location = self._sanitize(self.cleaned_data.get("location"))
        if len(location) < 2:
            raise forms.ValidationError(
                "Informe uma localização válida para a sala."
            )
        return location

    def clean_capacity(self):
        # 'capacity' é numérico; aqui validamos limites de negócio razoáveis
        # para evitar valores absurdos ou negativos.
        capacity = self.cleaned_data.get("capacity")
        if capacity is None:
            raise forms.ValidationError("Informe a capacidade da sala.")
        if capacity < 1:
            raise forms.ValidationError("A capacidade deve ser de pelo menos 1 pessoa.")
        if capacity > 10000:
            raise forms.ValidationError("A capacidade informada é muito alta.")
        return capacity

    def clean_resources(self):
        # single_line=False preserva as quebras de linha (texto multilinha),
        # apenas removendo tags/caracteres de controle.
        return self._sanitize(self.cleaned_data.get("resources"), single_line=False)

    def clean_description(self):
        return self._sanitize(self.cleaned_data.get("description"), single_line=False)

    def clean(self):
        """Validação que envolve MAIS DE UM campo (validação cruzada).

        O ``clean()`` roda DEPOIS de todos os ``clean_<campo>``, então aqui
        já temos os valores individuais sanitizados em ``cleaned_data``.
        Usamos este ponto para garantir que não exista outra sala com o
        mesmo nome (comparação case-insensitive, RF05).
        """
        cleaned_data = super().clean()
        name = cleaned_data.get("name")

        if name:
            # Busca salas com o mesmo nome ignorando maiúsculas/minúsculas.
            duplicates = Room.objects.filter(name__iexact=name)
            # Na EDIÇÃO, self.instance.pk já existe: precisamos excluir a
            # própria sala da checagem, senão ela "conflita consigo mesma".
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                # add_error associa o erro ao campo 'name' especificamente.
                self.add_error("name", "Já existe uma sala cadastrada com esse nome.")

        return cleaned_data
