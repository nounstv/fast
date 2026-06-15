#!/usr/bin/env python3
"""
EXTRAIR XTREAM - Extrator de listas IPTV via Xtream Codes API
Conecta a um provedor IPTV privado usando credenciais Xtream Codes
e exporta os canais em formato M3U e JSON.
"""
import urllib.request
import json
import os
import sys
import time
import ssl

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
BASE = os.path.dirname(os.path.abspath(__file__))

headers = {
    "User-Agent": "FastPlay-XtreamExtractor/1.0"
}

# Desabilita verificação SSL para servidores IPTV que usam certificados inválidos
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# ==============================================================================
# HELPERS
# ==============================================================================
def fetch_json(url):
    """Faz request e retorna JSON parseado."""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60, context=ssl_ctx) as response:
            raw = response.read().decode('utf-8', errors='replace')
            return json.loads(raw)
    except Exception as e:
        print(f"  ✗ Erro ao acessar URL: {e}")
        return None

def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"  ✗ Erro ao salvar {filepath}: {e}")
        return False

def save_m3u(items, filepath, is_radio=False):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for item in items:
                name = item.get("name", "Sem Nome")
                url = item.get("url", "")
                if not url:
                    continue
                
                category = item.get("category", "Geral")
                logo = item.get("logo", "")
                
                safe_name = name.replace('"', "'")
                logo_attr = f' tvg-logo="{logo}"' if logo else ""
                media_type = 'radio="true"' if is_radio else 'tvg-type="tv"'
                
                f.write(f'#EXTINF:-1 {media_type} tvg-name="{safe_name}"{logo_attr} group-title="{category}",{safe_name}\n')
                f.write(f'{url}\n')
        return True
    except Exception as e:
        print(f"  ✗ Erro ao salvar M3U: {e}")
        return False

def progress_bar(current, total, width=30):
    pct = current / total if total > 0 else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{total} ({pct*100:.0f}%)"

def clean_url(server):
    """Normaliza a URL do servidor."""
    server = server.strip().rstrip("/")
    if not server.startswith("http"):
        server = "http://" + server
    return server


# ==============================================================================
# XTREAM CODES API
# ==============================================================================
def get_server_info(server, username, password):
    """Obtém informações do servidor e valida as credenciais."""
    url = f"{server}/player_api.php?username={username}&password={password}"
    print(f"\n  Conectando ao servidor...")
    data = fetch_json(url)
    
    if not data:
        return None
    
    if "user_info" not in data:
        print("  ✗ Credenciais inválidas ou servidor incompatível")
        return None
    
    user = data["user_info"]
    server_info = data.get("server_info", {})
    
    print(f"  ✓ Conectado com sucesso!")
    print(f"    Usuário:       {user.get('username', 'N/A')}")
    print(f"    Status:        {user.get('status', 'N/A')}")
    print(f"    Max conexões:  {user.get('max_connections', 'N/A')}")
    
    exp = user.get("exp_date")
    if exp:
        try:
            from datetime import datetime
            exp_date = datetime.fromtimestamp(int(exp))
            print(f"    Expira em:     {exp_date.strftime('%d/%m/%Y %H:%M')}")
        except:
            print(f"    Expira em:     {exp}")
    
    created = user.get("created_at")
    if created:
        try:
            from datetime import datetime
            created_date = datetime.fromtimestamp(int(created))
            print(f"    Criado em:     {created_date.strftime('%d/%m/%Y %H:%M')}")
        except:
            pass
    
    print(f"    Servidor:      {server_info.get('url', 'N/A')}:{server_info.get('port', 'N/A')}")
    print(f"    Timezone:      {server_info.get('timezone', 'N/A')}")
    
    return data


def get_live_categories(server, username, password):
    """Obtém todas as categorias de canais ao vivo."""
    url = f"{server}/player_api.php?username={username}&password={password}&action=get_live_categories"
    print("\n  Baixando categorias de TV ao vivo...")
    data = fetch_json(url)
    if data:
        print(f"  ✓ {len(data)} categorias encontradas")
    return data or []


def get_live_streams(server, username, password, category_id=None):
    """Obtém canais ao vivo. Se category_id informado, filtra por categoria."""
    url = f"{server}/player_api.php?username={username}&password={password}&action=get_live_streams"
    if category_id:
        url += f"&category_id={category_id}"
    return fetch_json(url) or []


def get_vod_categories(server, username, password):
    """Obtém categorias de VOD (filmes)."""
    url = f"{server}/player_api.php?username={username}&password={password}&action=get_vod_categories"
    print("\n  Baixando categorias de VOD (filmes)...")
    data = fetch_json(url)
    if data:
        print(f"  ✓ {len(data)} categorias de VOD encontradas")
    return data or []


def get_vod_streams(server, username, password, category_id=None):
    """Obtém streams de VOD."""
    url = f"{server}/player_api.php?username={username}&password={password}&action=get_vod_streams"
    if category_id:
        url += f"&category_id={category_id}"
    return fetch_json(url) or []


def get_series_categories(server, username, password):
    """Obtém categorias de séries."""
    url = f"{server}/player_api.php?username={username}&password={password}&action=get_series_categories"
    print("\n  Baixando categorias de séries...")
    data = fetch_json(url)
    if data:
        print(f"  ✓ {len(data)} categorias de séries encontradas")
    return data or []


def get_series(server, username, password, category_id=None):
    """Obtém lista de séries."""
    url = f"{server}/player_api.php?username={username}&password={password}&action=get_series"
    if category_id:
        url += f"&category_id={category_id}"
    return fetch_json(url) or []


def build_stream_url(server, username, password, stream_id, extension="ts"):
    """Constrói a URL de streaming para um canal ao vivo."""
    return f"{server}/{username}/{password}/{stream_id}.{extension}"


def build_vod_url(server, username, password, stream_id, extension="mp4"):
    """Constrói a URL de streaming para um VOD."""
    return f"{server}/movie/{username}/{password}/{stream_id}.{extension}"


def build_series_url(server, username, password, stream_id, extension="mp4"):
    """Constrói a URL de streaming para um episódio de série."""
    return f"{server}/series/{username}/{password}/{stream_id}.{extension}"


# ==============================================================================
# EXTRAÇÃO PRINCIPAL
# ==============================================================================
def extract_live_tv(server, username, password, output_dir):
    """Extrai todos os canais de TV ao vivo."""
    print("\n" + "=" * 60)
    print("  📺 EXTRAINDO CANAIS DE TV AO VIVO")
    print("=" * 60)
    
    # 1. Categorias
    categories = get_live_categories(server, username, password)
    cat_map = {str(c.get("category_id", "")): c.get("category_name", "Geral") for c in categories}
    
    # 2. Todos os canais
    print("\n  Baixando lista completa de canais...")
    all_streams = get_live_streams(server, username, password)
    
    if not all_streams:
        print("  ✗ Nenhum canal encontrado")
        return 0
    
    print(f"  ✓ {len(all_streams)} canais de TV encontrados")
    
    # 3. Formatar
    formatted = []
    for i, ch in enumerate(all_streams, 1):
        if i % 100 == 0:
            sys.stdout.write(f"\r  {progress_bar(i, len(all_streams))} Processando canais...")
            sys.stdout.flush()
        
        stream_id = ch.get("stream_id", "")
        cat_id = str(ch.get("category_id", ""))
        name = ch.get("name", "Sem Nome")
        logo = ch.get("stream_icon", "") or ""
        epg_id = ch.get("epg_channel_id", "") or ""
        
        # Determinar extensão: usar container_extension se disponível
        ext = ch.get("container_extension", "ts")
        stream_url = build_stream_url(server, username, password, stream_id, ext)
        
        formatted.append({
            "id": str(stream_id),
            "name": name,
            "url": stream_url,
            "logo": logo,
            "category": cat_map.get(cat_id, "Sem Categoria"),
            "categoryId": cat_id,
            "epgId": epg_id,
            "added": ch.get("added", ""),
            "type": "live"
        })
    
    print(f"\r  ✓ {len(formatted)} canais processados" + " " * 30)
    
    # 4. Salvar
    tv_dir = os.path.join(output_dir, "tv")
    
    # JSON global
    save_json(formatted, os.path.join(tv_dir, "tv_todos.json"))
    print(f"  ✓ JSON salvo: tv/tv_todos.json")
    
    # M3U global
    save_m3u(formatted, os.path.join(tv_dir, "tv_todos.m3u"))
    print(f"  ✓ M3U salvo: tv/tv_todos.m3u")
    
    # Por categoria
    by_cat = {}
    for ch in formatted:
        cat = ch["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(ch)
    
    for cat, channels in by_cat.items():
        safe_cat = cat.lower().replace(" ", "_").replace("/", "_").replace("\\", "_").replace("|", "_")
        save_json(channels, os.path.join(tv_dir, "categorias", f"{safe_cat}.json"))
        save_m3u(channels, os.path.join(tv_dir, "categorias", f"{safe_cat}.m3u"))
    
    print(f"  ✓ {len(by_cat)} categorias salvas em tv/categorias/")
    
    # Índice de categorias
    cat_index = [{"id": cat_id, "name": name, "count": len(by_cat.get(name, []))} 
                 for cat_id, name in sorted(cat_map.items())]
    save_json(cat_index, os.path.join(tv_dir, "categorias", "index.json"))
    
    # Resumo
    print(f"\n  {'─'*50}")
    print(f"  RESUMO TV AO VIVO:")
    print(f"  Total de canais:    {len(formatted)}")
    print(f"  Categorias:         {len(by_cat)}")
    print(f"  Top categorias:")
    for cat, chs in sorted(by_cat.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"    {cat:30s} → {len(chs)} canais")
    
    return len(formatted)


def extract_vod(server, username, password, output_dir):
    """Extrai todos os filmes (VOD)."""
    print("\n" + "=" * 60)
    print("  🎬 EXTRAINDO FILMES (VOD)")
    print("=" * 60)
    
    categories = get_vod_categories(server, username, password)
    cat_map = {str(c.get("category_id", "")): c.get("category_name", "Geral") for c in categories}
    
    print("\n  Baixando lista completa de filmes...")
    all_vod = get_vod_streams(server, username, password)
    
    if not all_vod:
        print("  ✗ Nenhum filme encontrado")
        return 0
    
    print(f"  ✓ {len(all_vod)} filmes encontrados")
    
    formatted = []
    for i, movie in enumerate(all_vod, 1):
        if i % 100 == 0:
            sys.stdout.write(f"\r  {progress_bar(i, len(all_vod))} Processando filmes...")
            sys.stdout.flush()
        
        stream_id = movie.get("stream_id", "")
        cat_id = str(movie.get("category_id", ""))
        name = movie.get("name", "Sem Nome")
        ext = movie.get("container_extension", "mp4")
        
        stream_url = build_vod_url(server, username, password, stream_id, ext)
        
        formatted.append({
            "id": str(stream_id),
            "name": name,
            "url": stream_url,
            "logo": movie.get("stream_icon", "") or "",
            "category": cat_map.get(cat_id, "Sem Categoria"),
            "categoryId": cat_id,
            "rating": movie.get("rating", ""),
            "added": movie.get("added", ""),
            "type": "vod"
        })
    
    print(f"\r  ✓ {len(formatted)} filmes processados" + " " * 30)
    
    vod_dir = os.path.join(output_dir, "vod")
    save_json(formatted, os.path.join(vod_dir, "vod_todos.json"))
    print(f"  ✓ JSON salvo: vod/vod_todos.json")
    
    save_m3u(formatted, os.path.join(vod_dir, "vod_todos.m3u"))
    print(f"  ✓ M3U salvo: vod/vod_todos.m3u")
    
    # Por categoria
    by_cat = {}
    for movie in formatted:
        cat = movie["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(movie)
    
    for cat, movies in by_cat.items():
        safe_cat = cat.lower().replace(" ", "_").replace("/", "_").replace("\\", "_").replace("|", "_")
        save_json(movies, os.path.join(vod_dir, "categorias", f"{safe_cat}.json"))
    
    print(f"  ✓ {len(by_cat)} categorias salvas em vod/categorias/")
    
    print(f"\n  {'─'*50}")
    print(f"  RESUMO VOD:")
    print(f"  Total de filmes:    {len(formatted)}")
    print(f"  Categorias:         {len(by_cat)}")
    
    return len(formatted)


def extract_series(server, username, password, output_dir):
    """Extrai todas as séries."""
    print("\n" + "=" * 60)
    print("  📺 EXTRAINDO SÉRIES")
    print("=" * 60)
    
    categories = get_series_categories(server, username, password)
    cat_map = {str(c.get("category_id", "")): c.get("category_name", "Geral") for c in categories}
    
    print("\n  Baixando lista completa de séries...")
    all_series = get_series(server, username, password)
    
    if not all_series:
        print("  ✗ Nenhuma série encontrada")
        return 0
    
    print(f"  ✓ {len(all_series)} séries encontradas")
    
    formatted = []
    for s in all_series:
        series_id = s.get("series_id", "")
        cat_id = str(s.get("category_id", ""))
        name = s.get("name", "Sem Nome")
        
        formatted.append({
            "id": str(series_id),
            "name": name,
            "logo": s.get("cover", "") or "",
            "category": cat_map.get(cat_id, "Sem Categoria"),
            "categoryId": cat_id,
            "plot": s.get("plot", ""),
            "cast": s.get("cast", ""),
            "director": s.get("director", ""),
            "genre": s.get("genre", ""),
            "rating": s.get("rating", ""),
            "lastModified": s.get("last_modified", ""),
            "type": "series"
        })
    
    series_dir = os.path.join(output_dir, "series")
    save_json(formatted, os.path.join(series_dir, "series_todos.json"))
    print(f"  ✓ JSON salvo: series/series_todos.json")
    
    # Por categoria
    by_cat = {}
    for s in formatted:
        cat = s["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(s)
    
    for cat, series_list in by_cat.items():
        safe_cat = cat.lower().replace(" ", "_").replace("/", "_").replace("\\", "_").replace("|", "_")
        save_json(series_list, os.path.join(series_dir, "categorias", f"{safe_cat}.json"))
    
    print(f"  ✓ {len(by_cat)} categorias salvas em series/categorias/")
    
    print(f"\n  {'─'*50}")
    print(f"  RESUMO SÉRIES:")
    print(f"  Total de séries:    {len(formatted)}")
    print(f"  Categorias:         {len(by_cat)}")
    
    return len(formatted)


def generate_full_m3u(server, username, password):
    """Gera a URL M3U direta do provedor (método mais simples)."""
    return f"{server}/get.php?username={username}&password={password}&type=m3u_plus&output=ts"


def generate_epg_url(server, username, password):
    """Gera a URL do EPG (guia de programação)."""
    return f"{server}/xmltv.php?username={username}&password={password}"


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print("\n" + "█" * 60)
    print("  ⚡ FASTPLAY - EXTRATOR XTREAM CODES")
    print("█" * 60)
    
    # Credenciais
    print("\n  Insira as credenciais do provedor Xtream Codes:\n")
    
    server = input("  SERVIDOR (URL): ").strip()
    if not server:
        server = "http://cf.business-cdn-8k.com"
        print(f"  → Usando servidor padrão: {server}")
    
    username = input("  USUÁRIO: ").strip()
    if not username:
        print("  ✗ Usuário é obrigatório!")
        return
    
    password = input("  SENHA: ").strip()
    if not password:
        print("  ✗ Senha é obrigatória!")
        return
    
    server = clean_url(server)
    
    # Verificar conexão
    info = get_server_info(server, username, password)
    if not info:
        print("\n  ✗ Não foi possível conectar ao servidor. Verifique as credenciais.")
        return
    
    # Menu de opções
    print("\n" + "─" * 60)
    print("  O que deseja extrair?\n")
    print("  1 - 🔗 Apenas gerar URL M3U direta (instantâneo)")
    print("  2 - 📺 TV ao vivo (canais)")
    print("  3 - 🎬 VOD (filmes)")
    print("  4 - 📺 Séries")
    print("  5 - ⚡ TUDO (TV + VOD + Séries)")
    print("  6 - 📋 Apenas URL M3U + EPG (copiar/colar)")
    
    choice = input("\n  Escolha (1-6): ").strip()
    
    if choice == "1" or choice == "6":
        m3u_url = generate_full_m3u(server, username, password)
        epg_url = generate_epg_url(server, username, password)
        
        print("\n" + "=" * 60)
        print("  🔗 URLS GERADAS:")
        print("=" * 60)
        print(f"\n  📺 M3U Playlist:")
        print(f"  {m3u_url}")
        print(f"\n  📋 EPG (Guia de Programação):")
        print(f"  {epg_url}")
        
        if choice == "1":
            # Salvar URL em arquivo texto para referência
            urls_path = os.path.join(BASE, "downloads", "xtream_urls.txt")
            os.makedirs(os.path.dirname(urls_path), exist_ok=True)
            with open(urls_path, "w") as f:
                f.write(f"# Xtream Codes - URLs geradas em {time.strftime('%d/%m/%Y %H:%M')}\n")
                f.write(f"# Servidor: {server}\n")
                f.write(f"# Usuário: {username}\n\n")
                f.write(f"M3U Playlist:\n{m3u_url}\n\n")
                f.write(f"EPG:\n{epg_url}\n")
            print(f"\n  ✓ URLs salvas em: downloads/xtream_urls.txt")
            
            # Também baixar e salvar o M3U
            print(f"\n  Baixando playlist M3U do servidor...")
            req = urllib.request.Request(m3u_url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=120, context=ssl_ctx) as response:
                    m3u_content = response.read().decode('utf-8', errors='replace')
                
                m3u_path = os.path.join(BASE, "downloads", "xtream_playlist.m3u")
                with open(m3u_path, "w", encoding="utf-8") as f:
                    f.write(m3u_content)
                
                # Contar canais
                channel_count = m3u_content.count("#EXTINF:")
                print(f"  ✓ Playlist M3U salva: downloads/xtream_playlist.m3u ({channel_count} canais)")
            except Exception as e:
                print(f"  ✗ Erro ao baixar M3U: {e}")
                print(f"  → Use a URL acima para baixar manualmente")
        
        return
    
    # Extrair via API
    start_time = time.time()
    
    # Criar diretório de saída
    safe_user = username[:10].replace("/", "_").replace("\\", "_")
    output_dir = os.path.join(BASE, "downloads", f"xtream_{safe_user}")
    
    total_tv = 0
    total_vod = 0
    total_series = 0
    
    if choice in ["2", "5"]:
        total_tv = extract_live_tv(server, username, password, output_dir)
    
    if choice in ["3", "5"]:
        total_vod = extract_vod(server, username, password, output_dir)
    
    if choice in ["4", "5"]:
        total_series = extract_series(server, username, password, output_dir)
    
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    
    # Gerar e salvar URLs de referência
    m3u_url = generate_full_m3u(server, username, password)
    epg_url = generate_epg_url(server, username, password)
    
    urls_path = os.path.join(output_dir, "urls_referencia.txt")
    os.makedirs(os.path.dirname(urls_path), exist_ok=True)
    with open(urls_path, "w") as f:
        f.write(f"# Xtream Codes - Referência\n")
        f.write(f"# Extraído em {time.strftime('%d/%m/%Y %H:%M')}\n")
        f.write(f"# Servidor: {server}\n")
        f.write(f"# Usuário: {username}\n\n")
        f.write(f"M3U Playlist:\n{m3u_url}\n\n")
        f.write(f"EPG:\n{epg_url}\n")
    
    # Resumo final
    print("\n" + "█" * 60)
    print("  ✅ EXTRAÇÃO COMPLETA!")
    print("█" * 60)
    
    if total_tv:
        print(f"\n  📺 TV ao vivo:   {total_tv} canais")
    if total_vod:
        print(f"  🎬 VOD:          {total_vod} filmes")
    if total_series:
        print(f"  📺 Séries:       {total_series} séries")
    
    print(f"  ⏱️  Tempo:        {minutes}m {seconds}s")
    
    print(f"\n  📁 Arquivos salvos em: downloads/xtream_{safe_user}/")
    print(f"\n  🔗 URLs diretas:")
    print(f"     M3U: {m3u_url}")
    print(f"     EPG: {epg_url}")
    print()


if __name__ == "__main__":
    main()
