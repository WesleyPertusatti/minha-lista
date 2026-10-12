#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meus_canais.py - Gerenciador da SUA lista particular de canais (extras.m3u).

Use para adicionar, listar e remover canais que voce achou em qualquer lista
(testando no VLC, por exemplo). Tudo o que estiver aqui entra no FINAL da
sua lista final quando voce rodar o gerar_lista.py.

Rode pelo atalho meus-canais.cmd ou com:  python meus_canais.py
"""

import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.join(BASE, "extras.m3u")
CABECALHO = (
    "#EXTM3U\n"
    "# ---------------------------------------------------------------\n"
    "#  SEUS CANAIS (adicionados a mao)\n"
    "#  Gerenciado pelo meus_canais.py - voce tambem pode editar aqui.\n"
    "#  Formato: uma linha #EXTINF e, logo abaixo, a URL do canal.\n"
    "# ---------------------------------------------------------------\n"
)

ATTR_RE = re.compile(r'([a-zA-Z0-9_-]+)\s*=\s*"([^"]*)"')


# --------------------------------------------------------------------------
def carregar():
    """Le os canais do extras.m3u."""
    if not os.path.exists(ARQ):
        return []
    canais = []
    extinf = None
    with open(ARQ, "r", encoding="utf-8-sig", errors="replace") as f:
        for linha in f:
            t = linha.strip()
            if not t:
                continue
            if t.startswith("#EXTINF"):
                extinf = t
            elif t.startswith("#"):
                continue
            else:
                canais.append({"info": extinf or ("#EXTINF:-1," + t), "url": t})
                extinf = None
    return canais


def nome_de(info: str) -> str:
    """Nome do canal = parte depois da 1a virgula fora das aspas."""
    dentro = False
    for i, ch in enumerate(info):
        if ch == '"':
            dentro = not dentro
        elif ch == "," and not dentro:
            return info[i + 1:].strip()
    return info


def grupo_de(info: str) -> str:
    m = ATTR_RE.search(info)
    for chave, valor in ATTR_RE.findall(info):
        if chave == "group-title":
            return valor
    return ""


def salvar(canais):
    linhas = [CABECALHO.rstrip("\n")]
    for c in canais:
        linhas.append(c["info"])
        linhas.append(c["url"])
    with open(ARQ, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


# --------------------------------------------------------------------------
def adicionar():
    print("\n  ---------- ADICIONAR CANAL ----------")
    print("  Dica: no VLC, com o canal tocando, aperte Ctrl+J e copie o campo")
    print("        'Localizacao'. E esse endereco que vai aqui.\n")

    nome = input("  Nome do canal: ").strip()
    if not nome:
        print("\n  Cancelado (nome vazio).")
        return

    url = input("  Endereco (URL) do canal: ").strip()
    if not url:
        print("\n  Cancelado (endereco vazio).")
        return
    if "://" not in url:
        print("\n  Isso nao parece um endereco valido (precisa ter http:// ou https://).")
        print("  Nada foi salvo.")
        return

    grupo = input("  Categoria (Enter para 'Meus Canais'): ").strip() or "Meus Canais"

    canais = carregar()
    if any(c["url"] == url for c in canais):
        print("\n  Esse endereco ja esta na sua lista. Nada foi feito.")
        return

    canais.append({"info": '#EXTINF:-1 group-title="{}",{}'.format(grupo, nome), "url": url})
    salvar(canais)

    print("\n  OK! '{}' foi adicionado a sua lista particular.".format(nome))
    print("  Agora rode o gerar_lista.py (ou o gerar-lista.cmd) para ele entrar")
    print("  no arquivo minha-lista.m3u.")


def listar():
    canais = carregar()
    if not canais:
        print("\n  Voce ainda nao adicionou nenhum canal.")
        return
    print("\n  ---------- SEUS CANAIS ({}) ----------".format(len(canais)))
    for i, c in enumerate(canais, 1):
        print("  {:>2}. {:45} [{}]".format(i, nome_de(c["info"])[:45], grupo_de(c["info"]) or "sem categoria"))
        print("      {}".format(c["url"]))


def remover():
    canais = carregar()
    if not canais:
        print("\n  Voce ainda nao adicionou nenhum canal.")
        return

    print("\n  ---------- REMOVER CANAL ----------")
    for i, c in enumerate(canais, 1):
        print("  {:>2}. {}  [{}]".format(i, nome_de(c["info"]), grupo_de(c["info"]) or "sem categoria"))

    escolha = input("\n  Numero do canal a remover (0 cancela): ").strip()
    if not escolha.isdigit():
        print("\n  Opcao invalida. Nada foi feito.")
        return
    n = int(escolha)
    if n == 0:
        print("\n  Cancelado.")
        return
    if n < 1 or n > len(canais):
        print("\n  Numero fora da lista. Nada foi feito.")
        return

    removido = canais.pop(n - 1)
    salvar(canais)
    print("\n  Removido: {}".format(nome_de(removido["info"])))
    print("  Rode o gerar_lista.py de novo para atualizar a minha-lista.m3u.")


# --------------------------------------------------------------------------
def menu():
    print()
    print("=" * 52)
    print("   MEUS CANAIS  -  arquivo extras.m3u")
    print("=" * 52)
    print("  1 - Adicionar um canal")
    print("  2 - Listar os meus canais")
    print("  3 - Remover um canal")
    print("  0 - Sair")

    while True:
        try:
            op = input("\n  Escolha uma opcao: ").strip()
        except EOFError:
            break

        if op == "0" or op == "":
            break
        elif op == "1":
            adicionar()
        elif op == "2":
            listar()
        elif op == "3":
            remover()
        else:
            print("  Opcao invalida. Use 1, 2, 3 ou 0.")

    print("\n  Ate logo!")
    return 0


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        return menu()
    except KeyboardInterrupt:
        print("\n  Cancelado.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
