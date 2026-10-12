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
        caminho = origem if os.path.isabs(origem) else os.path.join(BASE, origem)
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


def combina(canal, termos):
    if not termos:
        return True
    alvos = [az(canal["nome"]), az(canal["grupo"]), az(canal["tvg_name"])]
    for termo in termos:
        exato = termo.startswith("=")
        alvo = az(termo[1:] if exato else termo)
        if not alvo:
            continue
        if az(canal["url"]) == az(termo):
            return True
        for a in alvos:
            if (a == alvo) if exato else (alvo in a):
                return True
    return False


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
    ap.add_argument("--tudo", action="store_true", help="Gera a lista com todos os canais, sem filtrar")
    args = ap.parse_args()

    cfg_path = os.path.join(BASE, "config.json")
    if not os.path.exists(cfg_path):
        print("ERRO: nao encontrei o config.json nesta pasta.")
        return 1

    with open(cfg_path, "r", encoding="utf-8-sig") as f:
        cfg = json.load(f)

    fontes = [x for x in cfg.get("fontes", []) if limpar(x) and not limpar(x).startswith("COLE")]
    if not fontes:
        print("ERRO: coloque o link da lista original em config.json (campo \"fontes\").")
        return 1

    ignorar_ssl = bool(cfg.get("ignorar_ssl", False))
    usar_bom = bool(cfg.get("bom", False))
    saida = cfg.get("saida", "minha-lista.m3u")
    arquivo_termos = cfg.get("arquivo_canais", "canais.txt")
    remover_duplicados = bool(cfg.get("remover_duplicados", True))

    todos = []
    for fonte in fontes:
        print("Lendo fonte: {}".format(fonte if not re.match(r"^https?://", fonte, re.I) else fonte[:70] + ("..." if len(fonte) > 70 else "")))
        try:
            texto = baixar(fonte, ignorar_ssl=ignorar_ssl)
        except urllib.error.HTTPError as e:
            print("  -> FALHOU (HTTP {}). Link expirado ou bloqueado?".format(e.code))
            continue
        except Exception as e:
            print("  -> FALHOU: {}".format(e))
            continue
        canais = parse_m3u(texto)
        print("  -> {} canais encontrados".format(len(canais)))
        todos.extend(canais)

    if not todos:
        print("\nNenhum canal foi lido. Confira o link em config.json.")
        return 1

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

    # Modo --listar
    if args.listar:
        grupos = {}
        for c in todos:
            grupos.setdefault(c["grupo"] or "SEM GRUPO", []).append(c["nome"])
        print("\n=== TODOS OS CANAIS DISPONIVEIS ({}) ===".format(len(todos)))
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
    if args.tudo:
        escolhidos = list(todos)
        termos = []
        print("\n--tudo: mantendo todos os canais.")
    else:
        termos = ler_termos(os.path.join(BASE, arquivo_termos) if not os.path.isabs(arquivo_termos) else arquivo_termos)
        if not termos:
            print("\nAVISO: {} esta vazio -> a lista saira COMPLETA.".format(arquivo_termos))
            print("Dica: rode 'python gerar_lista.py --listar' para ver os nomes dos canais.")
        escolhidos = [c for c in todos if combina(c, termos)]

    # Canais extras (adicionados a mao) entram no final
    extras_path = os.path.join(BASE, cfg.get("arquivo_extras", "extras.m3u"))
    extras = []
    if os.path.exists(extras_path):
        with open(extras_path, "r", encoding="utf-8-sig", errors="replace") as f:
            extras = parse_m3u(f.read())
        if extras:
            print("Adicionando {} canal(is) de extras.m3u".format(len(extras)))

    final = escolhidos + extras
    caminho_final = salvar(saida, montar_m3u(final, usar_bom))

    # Relatorio
    print("\n" + "=" * 52)
    print("Lista final: {} canal(is) -> {}".format(len(final), caminho_final))
    print("=" * 52)

    if termos:
        sem_resultado = []
        for termo in termos:
            if termo.startswith("="):
                alvo = az(termo[1:])
            else:
                alvo = az(termo)
            if not alvo:
                continue
            achou = any(
                (az(c["url"]) == az(termo)) or alvo in az(c["nome"]) or alvo in az(c["grupo"]) or alvo in az(c["tvg_name"])
                for c in todos
            )
            if not achou:
                sem_resultado.append(termo)
        if sem_resultado:
            print("\nEstes termos do {} NAO encontraram nenhum canal:".format(arquivo_termos))
            for t in sem_resultado:
                print("   - {}".format(t))
            print("Confira a escrita (rode --listar para ver os nomes exatos).")

    print("\nPronto! Teste no VLC: Midia > Abrir reproducao de rede > cole o caminho do arquivo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
