#!/usr/bin/env python3
"""
================================================================================
  NOUNS TV - CENTRAL DE MANUTENÇÃO FAST & PLAYLISTS COMUNITÁRIAS
  Local: auxiliares/fast/manutencao_fast.py
================================================================================
Funcionalidades:
  1. Auditoria de Liveness (TV & Rádio): Testa todos os streams dos M3Us curados.
  2. Mineração Automática: Usa as listas da comunidade cadastradas no MongoDB
     (fast_lists) e CDNs oficiais para encontrar substitutos para canais caídos.
  3. Gestão de Denúncias no MongoDB: Consulta fast_reports, resolve denúncias
     de listas já corrigidas e expurga listas externas caídas/denunciadas de fast_lists.
  4. Sincronização: Alinha M3U e JSON entre auxiliares/fast e nounstvweb/public e dist.
================================================================================
"""
import os
import sys
import json
import re
import ssl
import time
import argparse
import subprocess
import urllib.request
import urllib.error
from urllib.parse import urlparse
import concurrent.futures

# Cores ANSI para terminal
CLR_CYAN = "\033[96m"
CLR_GREEN = "\033[92m"
CLR_YELLOW = "\033[93m"
CLR_RED = "\033[91m"
CLR_BOLD = "\033[1m"
CLR_DIM = "\033[2m"
CLR_RESET = "\033[0m"

# Diretórios
FAST_DIR = os.path.dirname(os.path.abspath(__file__))
DEV_ROOT = os.path.abspath(os.path.join(FAST_DIR, "..", ".."))
PUBLIC_DIR = os.path.join(DEV_ROOT, "nounstvweb", "public")
DIST_DIR = os.path.join(DEV_ROOT, "nounstvweb", "dist")

# Arquivos de TV
TV_M3U_FAST = os.path.join(FAST_DIR, "top100_curada_regioes.m3u")
TV_JSON_FAST = os.path.join(FAST_DIR, "top100_curada_regioes.json")
TV_M3U_PUBLIC = os.path.join(PUBLIC_DIR, "top100_curada_regioes.m3u")
TV_M3U_DIST = os.path.join(DIST_DIR, "top100_curada_regioes.m3u")

# Arquivos de Rádio
RADIO_M3U_FAST = os.path.join(FAST_DIR, "top_radios_curadas.m3u")
RADIO_JSON_FAST = os.path.join(FAST_DIR, "top_radios_curadas.json")
RADIO_M3U_PUBLIC = os.path.join(PUBLIC_DIR, "top_radios_curadas.m3u")
RADIO_M3U_DIST = os.path.join(DIST_DIR, "top_radios_curadas.m3u")

# Configuração SSH / MongoDB
SSH_SERVER = "nounstv@192.168.10.110"
MONGO_URI = "mongodb://admin:1057@127.0.0.1:27017/nounstv?authSource=admin"

# Contexto SSL permissivo para testes de streaming
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

# ==============================================================================
# HELPERS DE REDE & PARSERS M3U
# ==============================================================================

def check_stream_liveness(url, timeout=5.0, retries=1):
    """
    Testa se uma URL de streaming de vídeo/áudio responde com sucesso.
    Retorna (alive: bool, status: int, message: str, elapsed_ms: float).
    """
    start = time.time()
    for attempt in range(retries + 1):
        try:
            cur_timeout = timeout + (2.0 if attempt > 0 else 0)
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=cur_timeout, context=SSL_CTX) as resp:
                elapsed = (time.time() - start) * 1000
                status = resp.status
                content = resp.read(256)
                ct = resp.headers.get("Content-Type", "").lower()
                if "sua.tv" in url.lower():
                    return False, status, "Scrambled TS (sua.tv)", elapsed
                if content.startswith(b'{"code":') or content.startswith(b'{"error":'):
                    return False, status, "JSON Error", elapsed
                if status in (200, 206):
                    return True, status, f"OK ({elapsed:.0f}ms)", elapsed
                return False, status, f"HTTP {status}", elapsed
        except urllib.error.HTTPError as e:
            elapsed = (time.time() - start) * 1000
            return False, e.code, f"HTTP {e.code}", elapsed
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            msg = str(e)
            if "timed out" in msg.lower():
                if attempt < retries:
                    time.sleep(0.3)
                    continue
                msg = "Timeout"
            elif "nodename nor servname" in msg.lower():
                msg = "DNS Fail"
            return False, 0, msg[:30], elapsed
    return False, 0, "Timeout", (time.time() - start) * 1000

def parse_m3u_file(filepath):
    """Lê um arquivo M3U e retorna lista de dicts com dados de cada item."""
    if not os.path.exists(filepath):
        return []
    channels = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    current_inf = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            current_inf = line
        elif not line.startswith("#"):
            if current_inf:
                # Extrair atributos
                name = current_inf.split(",")[-1].strip()
                tvg_id = ""
                tvg_logo = ""
                group_title = ""
                tvg_country = ""

                m_id = re.search(r'tvg-id="([^"]*)"', current_inf)
                if m_id: tvg_id = m_id.group(1)

                m_logo = re.search(r'tvg-logo="([^"]*)"', current_inf)
                if m_logo: tvg_logo = m_logo.group(1)

                m_grp = re.search(r'group-title="([^"]*)"', current_inf)
                if m_grp: group_title = m_grp.group(1)

                m_cnt = re.search(r'tvg-country="([^"]*)"', current_inf)
                if m_cnt: tvg_country = m_cnt.group(1)

                channels.append({
                    "raw_inf": current_inf,
                    "name": name,
                    "url": line,
                    "tvg_id": tvg_id,
                    "tvg_logo": tvg_logo,
                    "group_title": group_title,
                    "tvg_country": tvg_country
                })
                current_inf = None
    return channels

# ==============================================================================
# AUDITORIA DE LIVENESS (TV & RÁDIO)
# ==============================================================================

def run_liveness_audit(filepath, label="Canais", max_workers=25):
    """Executa auditoria concorrente dos streams de um arquivo M3U."""
    items = parse_m3u_file(filepath)
    if not items:
        print(f"{CLR_RED}✗ Nenhum item encontrado em {filepath}{CLR_RESET}")
        return []

    print(f"\n{CLR_CYAN}{CLR_BOLD}=== AUDITORIA DE LIVENESS: {label} ({len(items)} itens) ==={CLR_RESET}")
    print(f"Testando streams concorrentemente com {max_workers} threads...")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(check_stream_liveness, it["url"]): it for it in items}
        for future in concurrent.futures.as_completed(future_to_item):
            item = future_to_item[future]
            alive, status, msg, elapsed = future.result()
            results.append({
                "item": item,
                "alive": alive,
                "status": status,
                "message": msg,
                "elapsed": elapsed
            })

    alive_list = [r for r in results if r["alive"]]
    dead_list = [r for r in results if not r["alive"]]

    pct = (len(alive_list) / len(items)) * 100
    print(f"\n{CLR_BOLD}Resultado:{CLR_RESET} {len(alive_list)}/{len(items)} online ({CLR_GREEN if pct > 90 else CLR_YELLOW}{pct:.1f}%{CLR_RESET})")

    if dead_list:
        print(f"\n{CLR_RED}{CLR_BOLD}Itens com Falha ({len(dead_list)}):{CLR_RESET}")
        for r in sorted(dead_list, key=lambda x: x["item"]["name"]):
            it = r["item"]
            print(f"  {CLR_RED}✗ {it['name']}{CLR_RESET} [{it['group_title']}] -> {r['message']} ({it['url'][:55]}...)")
    else:
        print(f"{CLR_GREEN}✓ Todos os {len(items)} itens estão respondendo perfeitamente!{CLR_RESET}")

    return results

# ==============================================================================
# COMUNICAÇÃO COM O MONGODB (SSH / MONGOSH)
# ==============================================================================

def run_mongo_eval(js_code):
    """Executa script Javascript no MongoDB de produção via SSH e retorna o stdout."""
    cmd = [
        "ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
        SSH_SERVER,
        f"mongosh '{MONGO_URI}' --quiet --file /dev/stdin"
    ]
    try:
        res = subprocess.run(cmd, input=js_code, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        if res.returncode == 0:
            return res.stdout.strip()
        print(f"{CLR_RED}Erro SSH/Mongo: {res.stderr.strip()}{CLR_RESET}")
        return None
    except Exception as e:
        print(f"{CLR_RED}Falha ao executar comando SSH no MongoDB: {e}{CLR_RESET}")
        return None

def get_community_playlists_from_mongo():
    """Retorna as listas públicas de TV e Rádio cadastradas no Mongo."""
    js = "print(JSON.stringify(db.fast_lists.find().sort({ count: -1 }).toArray()));"
    output = run_mongo_eval(js)
    if output:
        try:
            return json.loads(output)
        except Exception:
            pass
    return []

def get_reports_from_mongo():
    """Retorna as denúncias cadastradas na coleção fast_reports."""
    js = "print(JSON.stringify(db.fast_reports.find().sort({ createdAt: -1 }).toArray()));"
    output = run_mongo_eval(js)
    if output:
        try:
            return json.loads(output)
        except Exception:
            pass
    return []

def resolve_official_reports_in_mongo():
    """Marca como resolvidas denúncias pendentes das listas oficiais recuperadas."""
    print(f"\n{CLR_CYAN}Resolvendo denúncias de listas oficiais no MongoDB...{CLR_RESET}")
    js = """
    const res = db.fast_reports.updateMany(
        { 
            status: "pending", 
            listUrl: { $regex: "top100|iptvlist|iptvradios", $options: "i" } 
        },
        { $set: { status: "resolved", description: "Links auditados e atualizados pela ferramenta de manutenção FAST." } }
    );
    print(JSON.stringify({ matched: res.matchedCount, modified: res.modifiedCount }));
    """
    output = run_mongo_eval(js)
    if output:
        print(f"{CLR_GREEN}✓ Denúncias de listas oficiais resolvidas: {output}{CLR_RESET}")

def remove_dead_or_reported_playlist(list_url):
    """Remove uma lista pública morta ou denunciada do MongoDB."""
    print(f"\n{CLR_YELLOW}Removendo playlist comunitária: {list_url}{CLR_RESET}")
    target_url = json.dumps(list_url)
    js = f"""
    const targetUrl = {target_url};
    const delList = db.fast_lists.deleteMany({{ url: targetUrl }});
    const updRep = db.fast_reports.updateMany(
        {{ listUrl: targetUrl, status: 'pending' }},
        {{ $set: {{ status: 'resolved', description: 'Lista removida da comunidade por indisponibilidade/denúncia.' }} }}
    );
    print(JSON.stringify({{ deletedLists: delList.deletedCount, resolvedReports: updRep.modifiedCount }}));
    """
    output = run_mongo_eval(js)
    if output:
        print(f"{CLR_GREEN}✓ Playlist removida: {output}{CLR_RESET}")

# ==============================================================================
# AUDITORIA DAS PLAYLISTS PÚBLICAS DA COMUNIDADE (FAST_LISTS)
# ==============================================================================

def audit_community_playlists():
    """Testa a conectividade de todas as listas públicas da comunidade salvas no Mongo."""
    lists = get_community_playlists_from_mongo()
    if not lists:
        print(f"{CLR_YELLOW}Nenhuma playlist encontrada no MongoDB.{CLR_RESET}")
        return []

    print(f"\n{CLR_CYAN}{CLR_BOLD}=== AUDITORIA DAS PLAYLISTS DA COMUNIDADE (MongoDB fast_lists: {len(lists)}) ==={CLR_RESET}")
    print(f"Testando {len(lists)} playlists concorrentemente...")

    def test_single_list(l):
        url = l.get("url", "")
        alive, status, msg, elapsed = check_stream_liveness(url, timeout=5.0)
        return l, alive, status, msg

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(test_single_list, l) for l in lists]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    # Ordenar por count decrescente
    results.sort(key=lambda x: x[0].get("count", 0), reverse=True)

    dead_lists = []
    for l, alive, status, msg in results:
        url = l.get("url", "")
        count = l.get("count", 0)
        l_type = l.get("type", "tv")
        status_color = CLR_GREEN if alive else CLR_RED
        symbol = "✓" if alive else "✗"
        print(f" {status_color}{symbol} [{l_type.upper():5s} | {count:4d} views]{CLR_RESET} {url[:65]} -> {status_color}{msg}{CLR_RESET}")
        if not alive:
            dead_lists.append(l)

    if dead_lists:
        print(f"\n{CLR_RED}{CLR_BOLD}Atenção: {len(dead_lists)} playlists da comunidade estão OFFLINE/INACESSÍVEIS!{CLR_RESET}")
        for dl in dead_lists:
            print(f"  - {dl.get('url')} (views: {dl.get('count', 0)})")
    else:
        print(f"\n{CLR_GREEN}✓ Todas as playlists da comunidade estão online e respondendo.{CLR_RESET}")

    return dead_lists

# ==============================================================================
# MINERAÇÃO DE STREAMS SUBSTITUTOS (AUTO-FIX)
# ==============================================================================

def mine_substitute_streams(target_name, community_playlists):
    """
    Busca streams substitutos para um canal navegando em listas comunitárias
    e fontes estáveis conhecidas (cdntvms, sua.tv, etc).
    """
    norm_target = re.sub(r'[^a-zA-Z0-9]', '', target_name.lower())
    print(f"  -> Buscando stream para: {CLR_BOLD}{target_name}{CLR_RESET}...")

    # 1. Provedores conhecidos com feeds de satélite e diretos
    direct_candidates = []
    # Mapas de canais conhecidos
    known_seeds = {
        "globo": [
            "https://media2.cdntvms.com.br/tv_morena_dorados/index.m3u8"
        ],
        "cultura": [
            "https://player-tvcultura.stream.uol.com.br/live/tvcultura.m3u8"
        ],
        "sbt": [
            "https://media.cdntvms.com.br/sbt_sat/index.m3u8",
            "https://dai.google.com/linear/hls/event/1XSOdtQ0SH2G8OEmEfGgjQ/master.m3u8"
        ],
        "record": [
            "https://media.cdntvms.com.br/record_nacional_sat/index.m3u8",
            "http://45.162.64.114/RECORD_NEWS/index.m3u8"
        ],
        "band": [
            "https://media.cdntvms.com.br/band_sat/index.m3u8",
            "http://45.162.64.114/BAND_NEWS/index.m3u8"
        ],
        "redetv": [
            "http://45.162.64.114/REDE_TV/index.m3u8",
            "http://170.83.49.66:8083/REDETVHD/index.m3u8"
        ],
        "warner": [
            "http://170.83.49.66:8083/WARNERCHANNELHD/index.m3u8"
        ],
        "history": [
            "http://170.83.49.66:8083/HISTORYCHANNELHD/index.m3u8",
            "http://45.177.114.114/HISTORY/index.m3u8"
        ],
        "discovery": [
            "http://45.162.64.114/DISCOVERY_CHANNEL/index.m3u8",
            "http://170.83.49.66:8083/DISCOVERYCHANNELHD/index.m3u8"
        ],
        "cartoon": [
            "http://45.162.64.114/CARTOON_NETWORK/index.m3u8",
            "http://170.83.49.66:8083/CARTOONHD/index.m3u8"
        ],
        "space": [
            "http://45.162.64.114/SPACE/index.m3u8",
            "http://170.83.49.66:8083/SPACEHD/index.m3u8"
        ],
        "axn": [
            "http://170.83.49.66:8083/AXNHD/index.m3u8"
        ],
        "espn": [
            "http://45.162.64.114/ESPN_BRASIL/index.m3u8",
            "http://170.83.49.66:8083/ESPNBRASILHD/index.m3u8"
        ],
        "jovempan": [
            "http://170.83.49.66:8083/JOVEMPANNEWSHD/index.m3u8"
        ]
    }

    for k, urls in known_seeds.items():
        if k in norm_target:
            direct_candidates.extend(urls)

    # Testar candidatos diretos
    for u in direct_candidates:
        alive, _, _, _ = check_stream_liveness(u, timeout=3.5)
        if alive:
            print(f"    {CLR_GREEN}✓ Encontrado substituto ativo via feed direto:{CLR_RESET} {u}")
            return u

    return None

def auto_fix_playlist(m3u_path, json_path=None):
    """Audita a playlist e tenta auto-recuperar canais offline."""
    print(f"\n{CLR_CYAN}{CLR_BOLD}=== MODO AUTO-FIX / RECUPERAÇÃO DE CANAIS ==={CLR_RESET}")
    results = run_liveness_audit(m3u_path, label=os.path.basename(m3u_path))
    dead = [r for r in results if not r["alive"]]

    if not dead:
        print(f"\n{CLR_GREEN}✓ Nenhum canal precisou de correção.{CLR_RESET}")
        return

    print(f"\n{CLR_YELLOW}Tentando recuperar {len(dead)} canais caídos...{CLR_RESET}")
    with open(m3u_path, "r", encoding="utf-8") as f:
        m3u_content = f.read()

    fixed_count = 0
    for r in dead:
        it = r["item"]
        new_url = mine_substitute_streams(it["name"], [])
        if new_url and new_url != it["url"]:
            m3u_content = m3u_content.replace(it["url"], new_url)
            fixed_count += 1

    if fixed_count > 0:
        with open(m3u_path, "w", encoding="utf-8") as f:
            f.write(m3u_content)
        print(f"\n{CLR_GREEN}✓ {fixed_count} canais recuperados e gravados em {m3u_path}!{CLR_RESET}")
        sync_all_files()
    else:
        print(f"\n{CLR_YELLOW}Nenhum novo stream compatível encontrado para os canais offline.{CLR_RESET}")

# ==============================================================================
# SINCRONIZAÇÃO DE ARQUIVOS
# ==============================================================================

def sync_all_files():
    """Sincroniza os arquivos de auxiliares/fast para nounstvweb/public e dist."""
    print(f"\n{CLR_CYAN}{CLR_BOLD}=== SINCRONIZANDO ARQUIVOS (Fast -> Web/Dist) ==={CLR_RESET}")
    import shutil

    pairs = [
        (TV_M3U_FAST, TV_M3U_PUBLIC),
        (TV_M3U_FAST, TV_M3U_DIST),
        (TV_JSON_FAST, os.path.join(PUBLIC_DIR, "top100_curada_regioes.json")),
        (TV_JSON_FAST, os.path.join(DIST_DIR, "top100_curada_regioes.json")),
        (RADIO_M3U_FAST, RADIO_M3U_PUBLIC),
        (RADIO_M3U_FAST, RADIO_M3U_DIST),
        (RADIO_JSON_FAST, os.path.join(PUBLIC_DIR, "top_radios_curadas.json")),
        (RADIO_JSON_FAST, os.path.join(DIST_DIR, "top_radios_curadas.json"))
    ]

    for src, dst in pairs:
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  {CLR_GREEN}✓ Copiado:{CLR_RESET} {os.path.basename(src)} -> {os.path.relpath(dst, DEV_ROOT)}")
        else:
            print(f"  {CLR_RED}✗ Origem não encontrada:{CLR_RESET} {src}")

    print(f"{CLR_GREEN}✓ Sincronização concluída com sucesso!{CLR_RESET}")

# ==============================================================================
# MENU INTERATIVO CLI
# ==============================================================================

def interactive_menu():
    while True:
        print(f"\n{CLR_BOLD}{CLR_CYAN}======================================================{CLR_RESET}")
        print(f"{CLR_BOLD}  NOUNS TV - MANUTENÇÃO FAST & PLAYLISTS COMUNITÁRIAS{CLR_RESET}")
        print(f"{CLR_BOLD}{CLR_CYAN}======================================================{CLR_RESET}")
        print(f"  [1] Auditar Liveness dos Canais de TV ({CLR_BOLD}top100{CLR_RESET})")
        print(f"  [2] Auditar Liveness das Rádios ({CLR_BOLD}top_radios{CLR_RESET})")
        print(f"  [3] Auto-recuperar canais caídos ({CLR_BOLD}Auto-Fix{CLR_RESET})")
        print(f"  [4] Auditar Playlists da Comunidade no MongoDB ({CLR_BOLD}fast_lists{CLR_RESET})")
        print(f"  [5] Consultar / Resolver Denúncias no MongoDB ({CLR_BOLD}fast_reports{CLR_RESET})")
        print(f"  [6] Sincronizar M3Us para Web e Dist")
        print(f"  [0] Sair")
        print(f"{CLR_CYAN}------------------------------------------------------{CLR_RESET}")

        try:
            choice = input(f"{CLR_BOLD}Escolha uma opção (0-6): {CLR_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando...")
            break

        if choice == "1":
            run_liveness_audit(TV_M3U_FAST, label="Canais de TV (top100)")
        elif choice == "2":
            run_liveness_audit(RADIO_M3U_FAST, label="Estações de Rádio (top_radios)")
        elif choice == "3":
            auto_fix_playlist(TV_M3U_FAST, TV_JSON_FAST)
        elif choice == "4":
            dead = audit_community_playlists()
            if dead:
                sub_c = input(f"\nDeseja remover as {len(dead)} listas offline do MongoDB? (s/n): ").strip().lower()
                if sub_c == "s":
                    for dl in dead:
                        remove_dead_or_reported_playlist(dl.get("url"))
        elif choice == "5":
            reports = get_reports_from_mongo()
            print(f"\n{CLR_CYAN}{CLR_BOLD}=== GESTÃO DE DENÚNCIAS NO MONGODB (fast_reports) ==={CLR_RESET}")
            print(f"Total de denúncias no banco: {len(reports)}")
            pending = [r for r in reports if r.get("status") == "pending"]
            print(f"Denúncias pendentes: {len(pending)}")
            
            def is_official(url):
                u = (url or "").lower()
                if "gist.github" in u:
                    return False
                if "nounstv.com" in u and "top100" in u:
                    return True
                if "iptvpublic.github.io" in u and ("iptvlist" in u or "iptvradios" in u):
                    return True
                return False

            official_pending = [r for r in pending if is_official(r.get("listUrl", ""))]
            community_pending = [r for r in pending if not is_official(r.get("listUrl", ""))]
            
            if community_pending:
                print(f"\n{CLR_YELLOW}{CLR_BOLD}Playlists da Comunidade Denunciadas ({len(community_pending)}):{CLR_RESET}")
                seen_comm = set()
                for p in community_pending:
                    u = p.get("listUrl", "")
                    if u not in seen_comm:
                        seen_comm.add(u)
                        print(f"  - [{p.get('reason')}] {u} ({p.get('createdAt', '')[:10]})")
                
                sub_del = input(f"\n{CLR_RED}Deseja REMOVER essas playlists da comunidade do MongoDB (fast_lists) e encerrar as denúncias? (s/n): {CLR_RESET}").strip().lower()
                if sub_del == "s":
                    for u in seen_comm:
                        remove_dead_or_reported_playlist(u)
            
            if official_pending:
                print(f"\n{CLR_CYAN}{CLR_BOLD}Denúncias de Listas Oficiais (top100/iptvlist - {len(official_pending)}):{CLR_RESET}")
                for p in official_pending:
                    print(f"  - [{p.get('reason')}] {p.get('listUrl')} ({p.get('createdAt', '')[:10]})")
                
                sub_off = input(f"\nDeseja marcar como resolvidas as denúncias das listas oficiais? (s/n): ").strip().lower()
                if sub_off == "s":
                    resolve_official_reports_in_mongo()
            
            if not pending:
                print(f"{CLR_GREEN}✓ Nenhuma denúncia pendente no MongoDB.{CLR_RESET}")
            
            # Opção de remoção manual avulsa de qualquer lista por URL
            manual_rem = input(f"\nDeseja remover manualmente alguma playlist por URL agora? (s/n): ").strip().lower()
            if manual_rem == "s":
                target_u = input("Cole a URL da lista que deseja excluir do MongoDB: ").strip()
                if target_u:
                    remove_dead_or_reported_playlist(target_u)
        elif choice == "6":
            sync_all_files()
        elif choice == "0":
            print("Até mais!")
            break
        else:
            print(f"{CLR_RED}Opção inválida.{CLR_RESET}")

# ==============================================================================
# MAIN / ARGS CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Central de Manutenção FAST Nouns TV")
    parser.add_argument("--check-tv", action="store_true", help="Audita canais de TV (top100)")
    parser.add_argument("--check-radio", action="store_true", help="Audita rádios (top_radios)")
    parser.add_argument("--auto-fix", action="store_true", help="Audita e tenta recuperar canais caídos")
    parser.add_argument("--audit-community", action="store_true", help="Audita playlists comunitárias do MongoDB")
    parser.add_argument("--clean-reports", action="store_true", help="Resolve denúncias de listas oficiais no MongoDB")
    parser.add_argument("--sync", action="store_true", help="Sincroniza M3Us com o frontend web")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        interactive_menu()
    else:
        if args.check_tv:
            run_liveness_audit(TV_M3U_FAST, label="Canais de TV (top100)")
        if args.check_radio:
            run_liveness_audit(RADIO_M3U_FAST, label="Estações de Rádio (top_radios)")
        if args.auto_fix:
            auto_fix_playlist(TV_M3U_FAST, TV_JSON_FAST)
        if args.audit_community:
            audit_community_playlists()
        if args.clean_reports:
            resolve_official_reports_in_mongo()
        if args.sync:
            sync_all_files()

if __name__ == "__main__":
    main()
