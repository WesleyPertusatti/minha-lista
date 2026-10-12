#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_lista.py - Cria a SUA propria lista M3U a partir de uma ou mais listas.

Uso:
    python gerar_lista.py              Gera a lista filtrada (usa o config.json)
    python gerar_lista.py --listar     Mostra TODOS os canais disponiveis nas fontes
    python gerar_lista.py --tudo       Gera a lista com TODOS os canais (sem filtrar)

Como funciona o filtro:
    O arquivo canais.txt tem um termo por linha. Um canal entra na lista final se
    o termo aparecer no NOME do canal ou no GRUPO (group-title) dele.
    - A busca ignora maiuscula/minuscula e acentos. "globosat" acha "Globo SAT".
    - Linhas comecando com # sao comentarios e sao ignoradas.
    - Se o canais.txt estiver VAZIO (so comentarios), a lista sai completa.
    - Use "=Nome Exato" (com o sinal de igual) para exigir nome identico.
    - Voce tambem pode colar a URL completa de um canal para pegar so ele.

Tudo que voce adicionar em extras.m3u entra no final da lista final, sem filtro.
"""

import argparse
import concurrent.futures
import gzip
import io
import json
import os
import re
import ssl
import sys
import unicodedata
import urllib.error
import urllib.request
import zlib

BASE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(BASE)  # pasta "Projeto Padrao" (1 acima de codigo)
VERSAO = "1.1"


# --------------------------------------------------------------------------
# Utilidades de texto
# --------------------------------------------------------------------------
def az(txt: str) -> str:
    """Remove acentos e deixa tudo minusculo, para comparar de forma tolerante."""
    if not txt:
        return ""
    nfkd = unicodedata.normalize("NFD", txt)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").lower()


def limpar(texto: str) -> str:
    return texto.replace("\ufeff", "").strip()


# --------------------------------------------------------------------------
# Leitura das fontes (link da internet ou arquivo local)
# --------------------------------------------------------------------------
def baixar(origem: str, timeout: int = 45, ignorar_ssl: bool = False) -> str:
    """Le uma fonte que pode ser uma URL http(s) ou um caminho de arquivo local."""
    if re.match(r"^https?://", origem, re.I):
        ctx = ssl._create_unverified_context() if ignorar_ssl else None
        req = urllib.request.Request(
            origem,
            headers={
                "User-Agent": "VLC/3.0.20 LibVLC/3.0.20 MinhaLista/" + VERSAO,
                "Accept": "*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            bruto = resp.read()
            encoding = (resp.headers.get("Content-Encoding") or "").lower()
            if "gzip" in encoding:
                bruto = gzip.decompress(bruto)
            elif "deflate" in encoding:
                try:
                    bruto = zlib.decompress(bruto)
                except zlib.error:
                    bruto = zlib.decompress(bruto, -zlib.MAX_WBITS)
            # Se o servidor mentir no Content-Encoding, tenta detectar pelo magic number
            if bruto[:2] == b"\x1f\x8b":
                bruto = gzip.decompress(bruto)
    else:
        caminho = origem if os.path.isabs(origem) else os.path.join(RAIZ, origem)
        with open(caminho, "rb") as f:
            bruto = f.read()

    for cod in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return bruto.decode(cod)
        except UnicodeDecodeError:
            continue
    return bruto.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------
# Parser de M3U
# --------------------------------------------------------------------------
ATTR_RE = re.compile(r'([a-zA-Z0-9_-]+)\s*=\s*"([^"]*)"')
# Pega o codigo do pais dentro do tvg-id, no padrao do iptv-org: "Band.br@SD" -> "br"
PAIS_RE = re.compile(r"\.([a-z]{2})(?:@|$)", re.I)


def dividir_extinf(corpo: str):
    """Separa atributos e nome do canal (corte = 1a virgula FORA das aspas)."""
    dentro_aspas = False
    corte = None
    for i, ch in enumerate(corpo):
        if ch == '"':
            dentro_aspas = not dentro_aspas
        elif ch == "," and not dentro_aspas:
            corte = i
            break

    if corte is None:
        return dict(ATTR_RE.findall(corpo)), ""

    esquerda = corpo[:corte]
    direita = limpar(corpo[corte + 1:])
    return dict(ATTR_RE.findall(esquerda)), direita


def parse_m3u(texto: str):
    """Transforma o texto do M3U numa lista de canais."""
    canais = []
    info_linhas = []

    for linha_bruta in texto.splitlines():
        linha = limpar(linha_bruta)
        if not linha:
            continue

        if linha.upper().startswith("#EXTINF"):
            info_linhas = [linha]
            continue

        if linha.startswith("#"):
            # Guarda comentarios que fazem parte da entrada (ex: #EXTGRP)
            if info_linhas:
                info_linhas.append(linha)
            continue

        # Qualquer linha que nao e comentario e a URL do canal
        atributos, nome = {}, ""
        if info_linhas:
            corpo = re.sub(r"^#EXTINF\s*:?\s*", "", info_linhas[0], flags=re.I)
            atributos, nome = dividir_extinf(corpo)
        else:
            nome = linha.rstrip("/").split("/")[-1] or linha

        canais.append(
            {
                "info": info_linhas,
                "url": linha,
                "nome": nome or atributos.get("tvg-name", "") or "(sem nome)",
                "grupo": atributos.get("group-title", ""),
                "tvg_name": atributos.get("tvg-name", ""),
                "tvg_id": atributos.get("tvg-id", ""),
            }
        )
        info_linhas = []

    return canais


# --------------------------------------------------------------------------
# Filtro
# --------------------------------------------------------------------------
def ler_termos(caminho: str):
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r", encoding="utf-8-sig", errors="replace") as f:
        termos = []
        for linha in f:
            t = limpar(linha)
            if not t or t.startswith("#"):
                continue
            termos.append(t)
        return termos


def casa(canal, termo):
    """Diz se um termo bate com o canal (nome, grupo, tvg-name ou URL exata)."""
    exato = termo.startswith("=")
    alvo = az(termo[1:] if exato else termo)
    if not alvo:
        return False

    # URL igualzinha
    if az(canal["url"]) == az(termo):
        return True

    for a in (az(canal["nome"]), az(canal["grupo"]), az(canal["tvg_name"])):
        if (a == alvo) if exato else (alvo in a):
            return True
    return False


def separar_termos(termos):
    """Separa o que entra do que sai. Linha com ! na frente = excluir."""
    incluir, excluir = [], []
    for t in termos:
        if t.startswith("!"):
            limpo = t[1:].strip()
            if limpo:
                excluir.append(limpo)
        else:
            incluir.append(t)
    return incluir, excluir


# --------------------------------------------------------------------------
# Escrita do M3U
# --------------------------------------------------------------------------
def montar_m3u(canais, usar_bom: bool):
    linhas = ["#EXTM3U"]
    for c in canais:
        if c["info"]:
            linhas.extend(c["info"])
        else:
            linhas.append('#EXTINF:-1,{}'.format(c["nome"]))
        linhas.append(c["url"])
    conteudo = "\n".join(linhas) + "\n"
    return conteudo.encode("utf-8-sig" if usar_bom else "utf-8")


def salvar(caminho, dados: bytes):
    caminho_completo = caminho if os.path.isabs(caminho) else os.path.join(BASE, caminho)
    with open(caminho_completo, "wb") as f:
        f.write(dados)
    return caminho_completo


# --------------------------------------------------------------------------
# Principal
# --------------------------------------------------------------------------
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Cria a sua propria lista M3U.")
    ap.add_argument("--listar", action="store_true", help="Apenas mostra todos os canais das fontes")
    ap.add_argument("--resumo", action="store_true", help="Mostra um resumo das fontes (quantidade por grupo e por pais)")
    ap.add_argument("--tudo", action="store_true", help="Gera a lista com todos os canais, sem filtrar")
    ap.add_argument("--verificar", action="store_true", help="Testa quais canais estao no ar agora")
    ap.add_argument("--timeout", type=int, default=8, help="Segundos de espera por canal na verificacao (padrao 8)")
    args = ap.parse_args()

    cfg_path = os.path.join(RAIZ, "config.json")
    if not os.path.exists(cfg_path):
        print("ERRO: nao encontrei o config.json nesta pasta.")
        return 1

    with open(cfg_path, "r", encoding="utf-8-sig") as f:
        cfg = json.load(f)

    fontes = [x for x in cfg.get("fontes", []) if limpar(x) and not limpar(x).startswith("COLE")]
    if not fontes:
        print("Sem fontes em config.json (campo \"fontes\" vazio).")
        print("A lista vai ter so os seus canais do extras.m3u.\n")

    ignorar_ssl = bool(cfg.get("ignorar_ssl", False))
    usar_bom = bool(cfg.get("bom", False))
    saida = cfg.get("saida", "minha-lista.m3u")
    arquivo_termos = cfg.get("arquivo_canais", "canais.txt")
    remover_duplicados = bool(cfg.get("remover_duplicados", True))

    # Seus canais (adicionados a mao) - existem em qualquer modo
    extras_path = os.path.join(RAIZ, cfg.get("arquivo_extras", "extras.m3u"))
    extras = []
    if os.path.exists(extras_path):
        with open(extras_path, "r", encoding="utf-8-sig", errors="replace") as f:
            extras = parse_m3u(f.read())

    todos = []
    resumos = []
    if fontes:
        for fonte in fontes:
            nome_fonte = fonte if not re.match(r"^https?://", fonte, re.I) else fonte[:70] + ("..." if len(fonte) > 70 else "")
            print("Lendo fonte: {}".format(nome_fonte))
            try:
                texto = baixar(fonte, ignorar_ssl=ignorar_ssl)
            except urllib.error.HTTPError as e:
                print("  -> FALHOU (HTTP {}). Link expirado ou bloqueado?".format(e.code))
                resumos.append((nome_fonte, None))
                continue
            except Exception as e:
                print("  -> FALHOU: {}".format(e))
                resumos.append((nome_fonte, None))
                continue
            canais = parse_m3u(texto)
            print("  -> {} canais encontrados".format(len(canais)))
            resumos.append((nome_fonte, canais))
            todos.extend(canais)

    if not todos and not extras:
        print("\nNada para montar: sem fontes em config.json e sem canais em extras.m3u.")
        return 1
    if not todos and extras:
        print("Montando so com seus canais (extras.m3u).")

    # Remove duplicados pela URL, mantendo a primeira ocorrencia
    if remover_duplicados:
        vistos = set()
        unicos = []
        for c in todos:
            if c["url"] in vistos:
                continue
            vistos.add(c["url"])
            unicos.append(c)
        if len(unicos) != len(todos):
            print("Removidos {} canais repetidos.".format(len(todos) - len(unicos)))
        todos = unicos

    # Modo --resumo
    if args.resumo:
        if not todos:
            print("\nSem fontes configuradas - nada para resumir.")
            return 0

        def contar(canais):
            grupos = {}
            paises = {}
            for c in canais:
                grupos[c["grupo"] or "SEM GRUPO"] = grupos.get(c["grupo"] or "SEM GRUPO", 0) + 1
                achou = PAIS_RE.search(c["tvg_id"] or "")
                if achou:
                    cod = achou.group(1).lower()
                    paises[cod] = paises.get(cod, 0) + 1
            return grupos, paises

        print("\n" + "=" * 60)
        print("RESUMO DAS FONTES")
        print("=" * 60)

        # Cada canal guarda o tvg-id, de onde tiramos o codigo do pais (ex: "Band.br@SD" -> br)
        for nome_fonte, canais in resumos:
            if canais is None:
                print("\n[{}]\n   >>> FALHOU ao baixar <<<".format(nome_fonte))
                continue
            print("\n[{}]".format(nome_fonte))
            print("   Total: {} canais".format(len(canais)))
            grupos, paises = contar(canais)
            print("   Grupos principais:")
            for g, q in sorted(grupos.items(), key=lambda x: -x[1])[:15]:
                print("      {:>5}  {}".format(q, g))
            if len(grupos) > 15:
                print("      ... e mais {} grupos".format(len(grupos) - 15))
            if paises:
                brasileiros = paises.get("br", 0)
                print("   Paises (pelo tvg-id):")
                for p, q in sorted(paises.items(), key=lambda x: -x[1])[:10]:
                    marca = "  <-- BRASIL" if p == "br" else ""
                    print("      {:>5}  {}{}".format(q, p, marca))
                print("   >>> Canais brasileiros (tvg-id .br): {}".format(brasileiros))

        print("\n" + "=" * 60)
        print("TOTAL GERAL: {} canais (somando todas as fontes, sem duplicados)".format(len(todos)))
        print("=" * 60)
        return 0

    # Modo --listar
    if args.listar:
        if not todos:
            print("\nSem fontes configuradas - nada para listar.")
            return 0

        grupos = {}
        for c in todos:
            grupos.setdefault(c["grupo"] or "SEM GRUPO", []).append(c["nome"])
        LIMITE = 400
        print("\n=== TODOS OS CANAIS DISPONIVEIS ({}) ===".format(len(todos)))
        if len(todos) > LIMITE:
            print("\nMuitos canais para mostrar na tela (limite {}). Mostrando so os grupos.".format(LIMITE))
            for grupo in sorted(grupos, key=az):
                print("   {:>5}  {}".format(len(grupos[grupo]), grupo))
        else:
            for grupo in sorted(grupos, key=az):
                print("\n[{}]  ({} canais)".format(grupo, len(grupos[grupo])))
                for nome in grupos[grupo]:
                    print("   " + nome)
        salvar("todos-os-canais.txt", ("Canais disponiveis nas fontes\n\n" + "\n".join(
            "[{}] {}".format(c["grupo"] or "SEM GRUPO", c["nome"]) for c in todos)).encode("utf-8"))
        salvar("todos-os-canais.m3u", montar_m3u(todos, usar_bom))
        print("\nSalvei tambem: todos-os-canais.txt e todos-os-canais.m3u")
        return 0

    # Filtro
    incluir, excluir = [], []
    if args.tudo:
        escolhidos = list(todos)
        termos = []
        print("\n--tudo: mantendo todos os canais.")
    else:
        termos = ler_termos(os.path.join(RAIZ, arquivo_termos) if not os.path.isabs(arquivo_termos) else arquivo_termos)
        incluir, excluir = separar_termos(termos)
        if fontes and not termos:
            print("\nAVISO: {} esta vazio -> da fonte entram TODOS os canais.".format(arquivo_termos))
            print("Dica: rode 'python gerar_lista.py --listar' para ver os nomes dos canais.")

        escolhidos = []
        for c in todos:
            if excluir and any(casa(c, t) for t in excluir):
                continue
            if incluir and not any(casa(c, t) for t in incluir):
                continue
            escolhidos.append(c)

        if excluir:
            cortados = sum(1 for c in todos if any(casa(c, t) for t in excluir))
            print("Termos com '!' excluiram {} canal(is).".format(cortados))

    # Seus canais (extras) ja foram lidos no inicio; entram no final
    if extras:
        print("Seus canais (extras.m3u): {} canal(is) no final da lista.".format(len(extras)))

    final = escolhidos + extras
    caminho_final = salvar(os.path.join(RAIZ, saida) if not os.path.isabs(saida) else saida, montar_m3u(final, usar_bom))

    # Verificacao opcional: quais canais estao no ar agora
    if args.verificar and final:
        print("\nVerificando {} canais (aguarde, pode levar um minuto)...".format(len(final)))
        ctx = ssl._create_unverified_context() if ignorar_ssl else None

        def checar(canal):
            req = urllib.request.Request(
                canal["url"],
                headers={
                    "User-Agent": "VLC/3.0.20 LibVLC/3.0.20",
                    "Range": "bytes=0-2047",
                    "Connection": "close",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=args.timeout, context=ctx) as r:
                    return canal, ("OK" if r.read(2048) else "VAZIO")
            except urllib.error.HTTPError as e:
                return canal, "HTTP {}".format(e.code)
            except Exception:
                return canal, "SEM RESPOSTA"

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            resultados = list(ex.map(checar, final))

        bons = [c for c, st in resultados if st == "OK"]
        ruins = [(c, st) for c, st in resultados if st != "OK"]

        print("\n" + "=" * 62)
        print("VERIFICACAO: {} de {} canais responderam agora".format(len(bons), len(resultados)))
        print("=" * 62)

        relatorio = ["Verificacao da lista - {} canais no ar de {}".format(len(bons), len(resultados)), ""]
        if bons:
            relatorio.append("=== FUNCIONANDO ===")
            for c, st in resultados:
                if st == "OK":
                    relatorio.append("[OK] {}  ({})".format(c["nome"], c["url"]))
        if ruins:
            relatorio.append("")
            relatorio.append("=== SEM RESPOSTA AGORA ===")
            for c, st in ruins:
                relatorio.append("[{}] {}  ({})".format(st, c["nome"], c["url"]))

        salvar("verificacao.txt", "\n".join(relatorio).encode("utf-8"))
        salvar("funcionando.txt", ("\n".join(c["nome"] for c, st in resultados if st == "OK") + "\n").encode("utf-8"))

        print("\nCanais no ar agora:")
        for c, st in resultados:
            if st == "OK":
                print("   [OK] " + c["nome"])
        if ruins:
            print("\nNao responderam agora: {} canais".format(len(ruins)))
            print("(403 normalmente e geo-bloqueio ou exigencia de cabecalho de navegador;")
            print(" podem funcionar no app da TV mesmo assim)")
        print("\nSalvei o relatorio completo em verificacao.txt")
        print("e a lista limpa dos nomes que funcionam em funcionando.txt")
        print("(e so copiar o conteudo de funcionando.txt para dentro do canais.txt)")

    # Relatorio
    print("\n" + "=" * 52)
    print("Lista final: {} canal(is) -> {}".format(len(final), caminho_final))
    print("=" * 52)

    if termos and todos:
        sem_resultado = [t for t in termos if az(t.lstrip("=!")) and not any(casa(c, t) for c in todos)]
        if sem_resultado:
            print("\nEstes termos do {} NAO encontraram nenhum canal:".format(arquivo_termos))
            for t in sem_resultado:
                print("   - {}".format(t))
            print("Confira a escrita (rode --listar para ver os nomes exatos).")

    print("\nPronto! Abra no VLC por: Midia > Abrir Arquivo (Ctrl+O), ou arraste o arquivo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
