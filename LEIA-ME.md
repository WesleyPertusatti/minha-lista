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
| `canais.txt` | Onde você escreve **os canais que quer manter** (e os `!` que quer tirar). |
| `meus-canais.cmd` | **Adicionar / listar / remover** os seus canais particulares. |
| `meus_canais.py` | O programa por trás do `meus-canais.cmd`. |
| `extras.m3u` | Onde ficam guardados os canais que você adicionou à mão. |
| `gerar-lista.cmd` | Clica 2x e monta a sua lista final. |
| `gerar_lista.py` | O programa que monta a lista (tem `--listar`, `--resumo`, `--verificar`). |
| `servidor-local.cmd` | Serve a lista na sua rede local, **sem internet** (para a TV). |
| `publicar.cmd` | Gera e envia para o GitHub (depois de configurado). |
| `minha-lista.m3u` | **A sua lista final** (é esse arquivo que vai pra TV). |
| `todos-os-canais.txt` / `.m3u` | Lista completa das fontes, só para consulta (gerada pelo `--listar`). |
| `funcionando.txt` / `verificacao.txt` | Resultado do `--verificar`: o que está no ar agora. |

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

No VLC use **Mídia ▸ Abrir Arquivo** (`Ctrl+O`) e escolha o `minha-lista.m3u`.

> ⚠️ Para **arquivo do PC**, o certo é **Abrir Arquivo**. O "Abrir reprodução de
> rede" é para **link** (`http://...`). Se usar o lugar errado, pode dar erro.

Ou simplesmente **arraste o arquivo** `minha-lista.m3u` para dentro do VLC.
Vai abrir a janela de playlist, e você navega entre os canais por ela.

---

## Adicionar e remover canais

### Adicionar um canal que você achou em outra lista

1. Abra a lista pública no VLC e **teste os canais**.
2. Quando achar um que funciona e te interessa, deixe ele tocando e aperte
   **`Ctrl+J`** (*Ferramentas ▸ Informações da mídia*).
3. Vá na aba **Código do fluxo** e copie o campo **Localização** — é o endereço
   do canal (algo como `http://servidor.com/canal/index.m3u8`).
4. Clique duas vezes em **`meus-canais.cmd`**.
5. Escolha **`1 - Adicionar um canal`** e cole o nome e o endereço.
6. Rode o **`gerar-lista.cmd`** — o canal entra no `minha-lista.m3u`.

Os canais que você adiciona ficam guardados no **`extras.m3u`** e vão sempre para
o **final** da sua lista, sem depender de nenhuma fonte externa.

### Remover um canal

- Se ele veio de uma **fonte** (a lista que você baixa): apague a linha no
  `canais.txt`, ou ponha **`!`** na frente para excluir tudo que combine.
  Exemplo: `!Pluto` tira todos os canais com "Pluto" no nome.
- Se ele está no **`extras.m3u`** (você adicionou à mão): use a opção
  **`3 - Remover um canal`** do `meus-canais.cmd`.

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

## Usar tudo local, sem internet

Se você não quer nada online (nem GitHub), tem dois caminhos:

### Opção A — Servidor local no PC (funciona em qualquer TV que aceite URL)

1. Clique duas vezes em **`servidor-local.cmd`**.
2. A janela mostra um endereço assim:
   `http://192.168.0.113:8000/minha-lista.m3u`
3. No app de IPTV da TV, onde você colou o link do GitHub, cole **esse** endereço.
4. **Deixe a janela aberta** enquanto assiste.

- Não precisa de internet — só do PC ligado e na mesma rede da TV.
- Aparecem vários endereços: use o que estiver na faixa da sua rede (ex.: `192.168.x.x`).
- Sempre que mudar a lista, rode o `gerar-lista.cmd`; a TV só precisa recarregar.

> A pasta fica acessível na sua rede local enquanto o servidor estiver ligado.
> É só na sua casa (não vai para a internet).

### Opção B — Pendrive (só em Android TV / Fire TV)

- Funciona se a sua TV for **Android TV, Google TV ou Fire Stick** e você usar o
  **VLC** ou o **OTT Navigator** — esses dois abrem o arquivo direto do pendrive.
- Em **LG (webOS)** e **Samsung (Tizen)**, os apps costumam aceitar **só URL**,
  então o pendrive geralmente não resolve — use a Opção A.

---

## Comandos do script (referência rápida)

| Comando | O que faz |
|---|---|
| `python gerar_lista.py` | Gera a `minha-lista.m3u` com os canais do `canais.txt`. |
| `python gerar_lista.py --resumo` | Mostra quantos canais cada fonte tem, por grupo e por país. |
| `python gerar_lista.py --listar` | Lista os canais e salva `todos-os-canais.txt` + `todos-os-canais.m3u`. |
| `python gerar_lista.py --tudo` | Gera a lista **completa**, sem filtrar nada. |
| `python gerar_lista.py --verificar` | Testa quais canais estão no ar **agora**. |
| `python gerar_lista.py --verificar --timeout 15` | Mesma coisa, esperando mais por canal lento. |

O `--verificar` cria dois arquivos:

- `verificacao.txt` — relatório completo (no ar / fora do ar), com as URLs;
- `funcionando.txt` — só os nomes dos canais que responderam. **Copie o conteúdo
  dele para dentro do `canais.txt`** para ficar só com o que funciona.

> ⚠️ O teste é uma foto do momento. Um canal pode estar fora agora e voltar depois.
> Erros **403** normalmente significam bloqueio por região ou exigência de cabeçalho
> de navegador — pode ser que funcionem no app da TV mesmo assim.

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
