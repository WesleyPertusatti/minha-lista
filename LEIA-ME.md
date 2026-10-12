# Minha Lista de IPTV

Ferramenta para você montar a **sua própria lista de canais** a partir de uma lista
maior (o link que você abre no VLC) e usar essa lista num **app de IPTV na Smart TV**.

O fluxo é simples: você diz quais canais quer → o script gera um arquivo `.m3u` só com eles →
você publica esse arquivo no GitHub → cola o link no app da TV.

---

## Arquivos desta pasta

| Arquivo | Para que serve |
|---|---|
| `config.json` | Onde você cola o **link da lista original**. |
| `canais.txt` | Onde você escreve **os canais que quer manter**. |
| `gerar_lista.py` | O script que faz o trabalho. |
| `gerar-lista.cmd` | Atalho para clicar 2x e rodar o script (Windows). |
| `extras.m3u` | Canais extras que você adiciona na mão (opcional). |
| `minha-lista.m3u` | **A sua lista final** (é esse arquivo que vai pro GitHub/TV). |
| `todos-os-canais.txt` / `.m3u` | Lista completa das fontes, só para consulta (gerada pelo `--listar`). |
| `publicar.cmd` | Atalho para enviar as mudanças para o GitHub depois de tudo configurado. |

---

## Passo 1 — Colar o link da lista original

Abra o `config.json` no Bloco de Notas e substitua o texto de exemplo:

```json
{
  "fontes": [
    "http://o-link-da-sua-lista-aqui.m3u"
  ],
  ...
}
```

> Pode colocar **mais de um link** dentro de `fontes`, separados por vírgula.
> Também vale o caminho de um arquivo baixado, ex: `"C:\\Users\\wesle\\Downloads\\lista.m3u"`.

---

## Passo 2 — Ver quais canais existem

Abra o **Prompt de Comando** nesta pasta e rode:

```
python gerar_lista.py --listar
```

Isso imprime todos os canais das fontes, agrupados por categoria, e salva o arquivo
`todos-os-canais.txt` para você consultar com calma.

---

## Passo 3 — Escolher os seus canais

Abra o `canais.txt` e escreva **um termo por linha**:

```
globo
sbt
ESPN
sportv
telecine
```

Regras:

- Busca **ignora maiúscula/minúscula e acentos**. `globosat` acha `Globo SAT`.
- O termo pode ser parte do **nome** do canal **ou** da **categoria** (`group-title`).
- `=Globo SP` (com o sinal de igual) exige o nome **exato**.
- Uma URL completa pega exatamente aquele canal.
- Linhas começando com `#` são comentários.
- **Se deixar vazio, a lista sai completa** (todos os canais das fontes).

---

## Passo 4 — Gerar a sua lista

Clique duas vezes em **`gerar-lista.cmd`** — ou rode no Prompt de Comando:

```
python gerar_lista.py
```

Pronto: foi criado o arquivo **`minha-lista.m3u`**.

O script ainda te avisa (muito útil!):

- quantos canais entraram;
- quantos duplicados foram removidos;
- **quais termos você escreveu que não bateram com nenhum canal** (erro de escrita).

Para gerar a lista completa de uma vez (sem filtro), use `python gerar_lista.py --tudo`.

---

## Passo 5 — Testar no VLC (ainda no PC)

No VLC: **Mídia ▸ Abrir reprodução de rede** e cole o caminho completo do arquivo:

```
C:\Users\wesle\Documents\Projeto Padrão\minha-lista.m3u
```

Ou simplesmente **arraste o arquivo** `minha-lista.m3u` para dentro do VLC.
Se os canais abrirem aqui, vão abrir na TV também.

---

## Passo 6 — Publicar no GitHub (link fixo para a TV)

O app da TV não lê a pasta do seu PC — ele precisa de um **link**. O GitHub dá isso de graça.

### 6.1 Criar a conta e o repositório

1. Crie uma conta em <https://github.com> (se ainda não tiver).
2. Clique em **New repository** (ou acesse <https://github.com/new>).
3. Nome sugerido: `minha-lista`
4. Marque **Public** (⚠️ precisa ser público para a TV acessar sem senha).
5. **NÃO** marque "Add a README".
6. Clique em **Create repository**.

### 6.2 Enviar os arquivos (só na primeira vez)

No Prompt de Comando, dentro desta pasta:

```
git init -b main
git add -A
git commit -m "Minha lista de canais"
git remote add origin https://github.com/SEU-USUARIO/minha-lista.git
git push -u origin main
```

> Se der erro pedindo nome/e-mail, rode antes:
> `git config --global user.name "Seu Nome"` e
> `git config --global user.email "seu@email.com"`.
> Se pedir senha, use um **Personal Access Token** (GitHub ▸ Settings ▸ Developer settings
> ▸ Personal access tokens) no lugar da senha.

### 6.3 Seu link

Ficará assim (troque `SEU-USUARIO`):

```
https://raw.githubusercontent.com/SEU-USUARIO/minha-lista/main/minha-lista.m3u
```

**Cole esse link no VLC** para conferir — se abrir a lista aí, está publicado certo. ✅

### 6.4 Atualizar depois

Sempre que mudar o `canais.txt`, rode o Passo 4 e depois clique em **`publicar.cmd`**
(ou rode `git add -A`, `git commit -m "atualiza"`, `git push`).
O link continua o mesmo — não precisa mexer na TV.

---

## Passo 7 — Configurar o app na Smart TV

1. Instale a loja de apps da sua TV e procure por um app de IPTV, por exemplo:
   - **Smart IPTV**, **SS IPTV**, **PelegTV** (LG / Samsung)
   - **IPTV Smarters**, **OTT Navigator**, **TiviMate** (Android TV / Fire Stick)
   - **Duplex Play**, **Xciptv**
2. Abra o app e escolha a opção de adicionar lista por **URL / M3U / Playlist**.
3. Cole o link do Passo 6.3 e salve.
4. Alguns apps pedem para você "registrar" o aparelho (MAC address) no site do app
   na primeira vez — é só seguir o que ele mostra na tela.

---

## Problemas comuns

| Sintoma | Causa provável / solução |
|---|---|
| `ERRO: coloque o link em config.json` | Você não trocou o texto de exemplo do `config.json`. |
| `FALHOU (HTTP 403/404)` | O link da fonte expirou ou foi bloqueado. Teste ele no VLC de novo. |
| Termo não acha nenhum canal | Escreveu diferente. Rode `--listar` e copie o nome exato. |
| TV não carrega a lista, mas o VLC carrega | Algumas TVs só aceitam links **HTTPS**. O `raw.githubusercontent.com` já é HTTPS, então normalmente resolve. |
| Canais aparecem, mas não abrem | O canal da lista original está fora do ar naquele momento — não é problema da sua lista. |
| Lista desatualizada na TV | O app costuma guardar em cache. Procure "recarregar/atualizar playlist" no app. |
| Muitos canais repetidos | Já é tratado automaticamente (`remover_duplicados`). |

---

## Observação

Use apenas fontes de conteúdo que você tem o direito de acessar. Este script só organiza
uma lista em um arquivo — ele não hospeda nem fornece nenhum canal.
