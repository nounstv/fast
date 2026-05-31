#!/usr/bin/env python3
"""
BAIXAR IPTV-ORG GLOBAL
Baixa e processa a base de dados global do IPTV-org, cruzando canais,
transmissões (streams), países e idiomas em um JSON e M3U consolidados e de alta qualidade.
"""
import urllib.request
import json
import os
import sys
import time

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
API_BASE = "https://iptv-org.github.io/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
BASE = os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
# HELPERS DE DOWNLOAD
# ==============================================================================
def fetch_json(url):
    print(f"  -> Baixando: {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"  ✗ Erro ao carregar {url}: {e}")
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

def progress_bar(current, total, width=30):
    pct = current / total if total > 0 else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{total} ({pct*100:.0f}%)"

# ==============================================================================
# PROCESSADOR PRINCIPAL
# ==============================================================================
def main():
    print("\n" + "█" * 60)
    print("  ⚡ IPTV-ORG GLOBAL DATA COMPILER")
    print("█" * 60)
    start_time = time.time()

    # 1. Download de metadados auxiliares
    print("\n[1/4] Baixando tabelas de metadados...")
    countries_data = fetch_json(f"{API_BASE}/countries.json")
    languages_data = fetch_json(f"{API_BASE}/languages.json")
    
    country_map = {}
    if countries_data:
        for c in countries_data:
            code = c.get("code", "").upper()
            if code:
                country_map[code] = c.get("name", code)
        print(f"  ✓ {len(country_map)} países carregados.")
        
    lang_map = {}
    if languages_data:
        for l in languages_data:
            code = l.get("code", "")
            if code:
                lang_map[code] = l.get("name", code)
        print(f"  ✓ {len(lang_map)} idiomas carregados.")

    # 2. Download de canais e streams
    print("\n[2/4] Baixando canais, transmissões e M3U (isso pode levar alguns instantes)...")
    channels_list = fetch_json(f"{API_BASE}/channels.json")
    streams_list = fetch_json(f"{API_BASE}/streams.json")
    
    # Baixar a playlist index.m3u para ler os logos
    print("  -> Baixando index.m3u para mapear logos...")
    logo_map = {}
    try:
        req = urllib.request.Request("https://iptv-org.github.io/iptv/index.m3u", headers=HEADERS)
        with urllib.request.urlopen(req, timeout=45) as response:
            m3u_content = response.read().decode('utf-8')
            import re
            # Regex que permite qualquer coisa entre o tvg-id e o tvg-logo na tag EXTINF
            pattern = re.compile(r'tvg-id="([^"@]*)(?:@[^"]*)?".*?tvg-logo="([^"]*)"')
            for match in pattern.finditer(m3u_content):
                tvg_id, logo_url = match.groups()
                if tvg_id and logo_url:
                    logo_map[tvg_id] = logo_url
            print(f"  ✓ {len(logo_map)} logos mapeados a partir da playlist M3U.")
    except Exception as e:
        print(f"  ✗ Erro ao mapear logos do M3U: {e}")

    if not channels_list or not streams_list:
        print("\n✗ Falha crítica: não foi possível carregar os dados essenciais do IPTV-org.")
        sys.exit(1)

    print(f"  ✓ {len(channels_list)} canais e {len(streams_list)} transmissões carregadas.")

    # 3. Cruzamento e processamento dos dados
    print("\n[3/4] Indexando e unificando dados...")
    
    # Criar mapeamento de canais pelo ID
    channels_map = {}
    for ch in channels_list:
        ch_id = ch.get("id")
        if ch_id:
            # Injeta o logo mapeado via M3U
            ch["logo"] = logo_map.get(ch_id, "")
            channels_map[ch_id] = ch

    # Agrupar streams por canal
    streams_by_channel = {}
    for s in streams_list:
        ch_id = s.get("channel")
        url = s.get("url")
        if not ch_id or not url:
            continue
        
        if ch_id not in streams_by_channel:
            streams_by_channel[ch_id] = []
            
        streams_by_channel[ch_id].append({
            "url": url,
            "http_referrer": s.get("http_referrer"),
            "user_agent": s.get("user_agent")
        })

    print(f"  ✓ {len(streams_by_channel)} canais possuem transmissões ativas.")

    # Gerar JSON global formatado
    formatted_channels = []
    
    for ch_id, streams in streams_by_channel.items():
        ch_meta = channels_map.get(ch_id, {})
        
        # Obter país e idioma
        cc = (ch_meta.get("country") or "??").upper()
        country_name = country_map.get(cc, cc)
        
        langs_codes = ch_meta.get("languages", [])
        langs_readable = [lang_map.get(l, l) for l in langs_codes if l]
        
        # Categorias
        categories = ch_meta.get("categories", [])
        primary_category = categories[0].capitalize() if categories else "General"
        
        # Logo
        logo = ch_meta.get("logo", "")
        
        # Nome do canal
        name = ch_meta.get("name", ch_id)
        
        # Descrição detalhada
        lang_str = ", ".join(langs_readable) if langs_readable else "N/A"
        desc = f"Global IPTV stream. Country: {country_name}. Language: {lang_str}."
        if ch_meta.get("website"):
            desc += f" Website: {ch_meta.get('website')}"

        formatted_channels.append({
            "id": ch_id,
            "name": name,
            "logo": logo,
            "logoText": name[:3].upper(),
            "url": streams[0]["url"],
            "httpReferrer": streams[0]["http_referrer"],
            "userAgent": streams[0]["user_agent"],
            "streams": streams,
            "category": primary_category,
            "categories": categories,
            "country": cc,
            "countryName": country_name,
            "languages": langs_readable,
            "description": desc
        })

    # Ordenar por nome do canal
    formatted_channels.sort(key=lambda x: x["name"].lower())

    # 4. Salvar os arquivos consolidados
    print("\n[4/4] Gravando arquivos...")
    
    # JSON Global
    json_path = os.path.join(BASE, "downloads", "tv", "tv_todos.json")
    save_json(formatted_channels, json_path)
    print(f"  ✓ JSON global salvo: {json_path} ({len(formatted_channels)} canais)")

    # Separar por país e salvar index de países
    country_count = {}
    for ch in formatted_channels:
        cc = ch["country"]
        if cc not in country_count:
            country_count[cc] = []
        country_count[cc].append(ch)

    for cc, channels in country_count.items():
        save_json(channels, os.path.join(BASE, "downloads", "tv", "paises", f"{cc}.json"))

    country_index = [
        {
            "code": cc,
            "name": channels[0].get("countryName", cc),
            "stations": len(channels)
        }
        for cc, channels in sorted(country_count.items(), key=lambda x: len(x[1]), reverse=True)
    ]
    save_json(country_index, os.path.join(BASE, "downloads", "tv", "paises", "index.json"))
    print(f"  ✓ {len(country_count)} arquivos de países salvos em downloads/tv/paises/")

    # Salvar M3U Global
    m3u_path = os.path.join(BASE, "downloads", "tv", "tv_todos.m3u")
    try:
        with open(m3u_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for ch in formatted_channels:
                meta_parts = [
                    f'tvg-id="{ch["id"]}"',
                    f'tvg-name="{ch["name"]}"',
                    f'group-title="{ch["category"]}"',
                    f'tvg-country="{ch["country"]}"',
                    f'tvg-logo="{ch["logo"]}"'
                ]
                # Adicionar propriedades extras para Players que suportam referer/user-agent
                opt_headers = []
                if ch["httpReferrer"]:
                    opt_headers.append(f'http-referrer="{ch["httpReferrer"]}"')
                if ch["userAgent"]:
                    opt_headers.append(f'http-user-agent="{ch["userAgent"]}"')
                
                meta_line = f'#EXTINF:-1 {" ".join(meta_parts + opt_headers)},{ch["name"]}\n'
                f.write(meta_line)
                
                # Se tiver cabeçalhos customizados, alguns players lêem como comentários logo após a linha INF
                if ch["userAgent"]:
                    f.write(f'#EXTVLCOPT:http-user-agent={ch["userAgent"]}\n')
                if ch["httpReferrer"]:
                    f.write(f'#EXTVLCOPT:http-referrer={ch["httpReferrer"]}\n')
                    
                f.write(f'{ch["url"]}\n')
        print(f"  ✓ M3U global salvo: {m3u_path}")
    except Exception as e:
        print(f"  ✗ Erro ao salvar M3U global: {e}")

    # Resumo
    elapsed = time.time() - start_time
    m, s = divmod(elapsed, 60)
    print("\n" + "█" * 60)
    print("  ✅ COMPILAÇÃO CONCLUÍDA COM SUCESSO!")
    print("█" * 60)
    print(f"  Total de canais globais: {len(formatted_channels)}")
    print(f"  Total de países:         {len(country_count)}")
    print(f"  Tempo decorrido:         {int(m)}m {int(s)}s")
    print(f"  Diretório de saída:      downloads/tv/")
    print()

if __name__ == "__main__":
    main()
