#!/usr/bin/env python3
"""
BAIXAR TUDO - Famelack TV + Rádio
Baixa todos os canais de TV e estações de rádio do repositório Famelack,
organizados por categoria e por país, em formato JSON e M3U.
"""
import urllib.request
import json
import os
import sys
import time

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
RAW_BASE = "https://raw.githubusercontent.com/famelack/famelack-data/main"
BASE = os.path.dirname(os.path.abspath(__file__))

TV_CATEGORIES = [
    "animation", "auto", "business", "classic", "comedy", "cooking", "culture",
    "documentary", "education", "entertainment", "family", "general", "kids",
    "legislative", "lifestyle", "movies", "music", "news", "outdoor", "public",
    "relax", "religious", "science", "series", "shop", "show", "sports",
    "top-news", "travel", "weather"
]

RADIO_CATEGORIES = [
    "70s", "80s", "90s", "blues", "chill", "christmas", "classical", "country",
    "easy-listening", "electronic", "folk", "hip-hop", "hits", "indie", "jazz",
    "latin", "metal", "news", "oldies", "politics", "pop", "reggae", "religious",
    "rock", "schlager", "soul", "sports", "talk"
]

headers = {
    "User-Agent": "FastPlay-Downloader/2.0"
}

# ==============================================================================
# HELPERS
# ==============================================================================
def fetch_json(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return None

def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"    ✗ Erro ao salvar {filepath}: {e}")
        return False

def save_m3u(items, filepath, is_radio=False):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for item in items:
                name = item.get("name", "Sem Nome")
                streams = item.get("stream_urls", [])
                url = item.get("url", "")
                
                if not streams and not url:
                    continue
                
                stream = url if url else streams[0]
                category = item.get("category", "Geral")
                country = item.get("country", "??")
                
                media_type = 'radio="true"' if is_radio else 'tvg-type="tv"'
                f.write(f'#EXTINF:-1 {media_type} tvg-name="{name}" group-title="{category}" tvg-country="{country}",{name}\n')
                f.write(f'{stream}\n')
        return True
    except Exception as e:
        print(f"    ✗ Erro ao salvar M3U: {e}")
        return False

def progress_bar(current, total, width=30):
    pct = current / total if total > 0 else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{total} ({pct*100:.0f}%)"


# ==============================================================================
# TV DOWNLOADER
# ==============================================================================
def download_tv():
    print("\n" + "=" * 60)
    print("  📺 BAIXANDO CANAIS DE TV (Famelack)")
    print("=" * 60)
    
    # 1. Baixar all.json (todos os canais)
    print("\n  Baixando base completa de TV...")
    all_url = f"{RAW_BASE}/tv/raw/categories/all.json"
    all_tv = fetch_json(all_url)
    
    if not all_tv:
        print("  ✗ Falha ao baixar all.json de TV")
        return 0
    
    print(f"  ✓ {len(all_tv)} canais de TV encontrados na base geral")
    
    # 2. Mapear categorias
    print(f"\n  Mapeando {len(TV_CATEGORIES)} categorias de TV...")
    id_to_category = {}
    
    for i, cat in enumerate(TV_CATEGORIES, 1):
        sys.stdout.write(f"\r  {progress_bar(i, len(TV_CATEGORIES))} {cat:20s}")
        sys.stdout.flush()
        
        cat_url = f"{RAW_BASE}/tv/raw/categories/{cat}.json"
        cat_data = fetch_json(cat_url)
        if cat_data:
            for item in cat_data:
                nanoid = item.get("nanoid")
                if nanoid:
                    id_to_category[nanoid] = cat.replace("-", " ").capitalize()
        
        time.sleep(0.1)
    
    print(f"\n  ✓ {len(id_to_category)} canais categorizados")
    
    # 3. Baixar países metadata
    print("\n  Baixando metadados de países...")
    countries_meta = fetch_json(f"{RAW_BASE}/tv/raw/countries_metadata.json")
    
    country_names = {}
    if countries_meta and isinstance(countries_meta, dict):
        for code, info in countries_meta.items():
            name = info.get("country", code) if isinstance(info, dict) else code
            if code:
                country_names[code.lower()] = name
        print(f"  ✓ {len(country_names)} países mapeados")
    
    # 4. Formatar e salvar
    formatted_tv = []
    for ch in all_tv:
        streams = ch.get("stream_urls", [])
        if not streams:
            continue
        
        nanoid = ch.get("nanoid", "")
        country_code = (ch.get("country", "??") or "??").upper()
        languages = ch.get("languages", [])
        
        formatted_tv.append({
            "id": nanoid,
            "name": ch.get("name", "Sem Nome"),
            "url": streams[0],
            "category": id_to_category.get(nanoid, "Geral"),
            "country": country_code,
            "countryName": country_names.get(country_code.lower(), country_code),
            "languages": languages,
            "description": f"Canal de TV de {country_names.get(country_code.lower(), country_code)}. Idioma: {', '.join(languages) if languages else 'N/A'}.",
            "logoText": ch.get("name", "TV")[:3].upper(),
            "streamCount": len(streams),
            "allStreams": streams
        })
    
    # Salvar JSON global
    json_path = os.path.join(BASE, "downloads", "tv_famelack", "tv_todos.json")
    save_json(formatted_tv, json_path)
    print(f"\n  ✓ JSON global salvo: {json_path} ({len(formatted_tv)} canais)")
    
    # Salvar M3U global
    m3u_path = os.path.join(BASE, "downloads", "tv_famelack", "tv_todos.m3u")
    save_m3u(formatted_tv, m3u_path, is_radio=False)
    print(f"  ✓ M3U global salvo: {m3u_path}")
    
    # Salvar por categoria
    cat_count = {}
    for ch in formatted_tv:
        cat = ch["category"]
        if cat not in cat_count:
            cat_count[cat] = []
        cat_count[cat].append(ch)
    
    for cat, channels in cat_count.items():
        safe_cat = cat.lower().replace(" ", "_").replace("/", "_")
        save_json(channels, os.path.join(BASE, "downloads", "tv_famelack", "categorias", f"{safe_cat}.json"))
    
    print(f"  ✓ {len(cat_count)} categorias salvas em downloads/tv_famelack/categorias/")
    
    # Salvar por país
    country_count = {}
    for ch in formatted_tv:
        cc = ch["country"]
        if cc not in country_count:
            country_count[cc] = []
        country_count[cc].append(ch)
    
    for cc, channels in country_count.items():
        save_json(channels, os.path.join(BASE, "downloads", "tv_famelack", "paises", f"{cc}.json"))
    
    # Índice de países
    country_index = [{"code": cc, "name": channels[0].get("countryName", cc), "stations": len(channels)} 
                     for cc, channels in sorted(country_count.items(), key=lambda x: len(x[1]), reverse=True)]
    save_json(country_index, os.path.join(BASE, "downloads", "tv_famelack", "paises", "index.json"))
    
    print(f"  ✓ {len(country_count)} países salvos em downloads/tv_famelack/paises/")
    
    # Resumo
    print(f"\n  {'─'*50}")
    print(f"  RESUMO TV:")
    print(f"  Total de canais:     {len(formatted_tv)}")
    print(f"  Categorias:          {len(cat_count)}")
    print(f"  Países:              {len(country_count)}")
    print(f"  Top categorias:")
    for cat, chs in sorted(cat_count.items(), key=lambda x: len(x[1]), reverse=True)[:8]:
        print(f"    {cat:20s} → {len(chs)} canais")
    
    return len(formatted_tv)


# ==============================================================================
# RADIO DOWNLOADER (Famelack)
# ==============================================================================
def download_radio_famelack():
    print("\n" + "=" * 60)
    print("  📻 BAIXANDO ESTAÇÕES DE RÁDIO (Famelack)")
    print("=" * 60)
    
    # 1. Baixar all.json
    print("\n  Baixando base completa de rádio...")
    all_url = f"{RAW_BASE}/radio/raw/categories/all.json"
    all_radio = fetch_json(all_url)
    
    if not all_radio:
        print("  ✗ Falha ao baixar all.json de rádio")
        return 0
    
    print(f"  ✓ {len(all_radio)} estações de rádio encontradas")
    
    # 2. Mapear categorias
    print(f"\n  Mapeando {len(RADIO_CATEGORIES)} categorias de rádio...")
    id_to_category = {}
    
    for i, cat in enumerate(RADIO_CATEGORIES, 1):
        sys.stdout.write(f"\r  {progress_bar(i, len(RADIO_CATEGORIES))} {cat:20s}")
        sys.stdout.flush()
        
        cat_url = f"{RAW_BASE}/radio/raw/categories/{cat}.json"
        cat_data = fetch_json(cat_url)
        if cat_data:
            for item in cat_data:
                nanoid = item.get("nanoid")
                if nanoid:
                    id_to_category[nanoid] = cat.replace("-", " ").capitalize()
        
        time.sleep(0.1)
    
    print(f"\n  ✓ {len(id_to_category)} estações categorizadas")
    
    # 3. Metadados de países
    print("\n  Baixando metadados de países...")
    countries_meta = fetch_json(f"{RAW_BASE}/radio/raw/countries_metadata.json")
    
    country_names = {}
    if countries_meta and isinstance(countries_meta, dict):
        for code, info in countries_meta.items():
            name = info.get("country", code) if isinstance(info, dict) else code
            if code:
                country_names[code.lower()] = name
        print(f"  ✓ {len(country_names)} países mapeados")
    
    # 4. Formatar
    formatted_radio = []
    for st in all_radio:
        streams = st.get("stream_urls", [])
        if not streams:
            continue
        
        nanoid = st.get("nanoid", "")
        country_code = (st.get("country", "??") or "??").upper()
        languages = st.get("languages", [])

        favicon_url = st.get("favicon") or st.get("logo") or st.get("image") or ""
        if not favicon_url:
            # Fallback dinâmico: tenta extrair favicon usando o domínio do stream
            try:
                from urllib.parse import urlparse
                parsed_uri = urlparse(streams[0])
                netloc = parsed_uri.netloc.split(':')[0] # Remove porta se houver
                # Tenta simplificar subdomínios de streaming comuns para achar o site principal
                parts = netloc.split('.')
                if len(parts) > 2:
                    # Se for ex: 27273.live.streamtheworld.com ou icecast.omnimedia.it
                    # Remove subdomínios de stream comuns
                    stream_subdomains = {'live', 'stream', 'streamtheworld', 'shoutcast', 'icecast', 'cast', 'audio', 'radio'}
                    filtered_parts = [p for p in parts if p.lower() not in stream_subdomains]
                    # Se sobrou pelo menos o domínio e TLD (ex: google.com), reconstrói
                    if len(filtered_parts) >= 2:
                        netloc = '.'.join(filtered_parts[-2:])
                favicon_url = f"https://www.google.com/s2/favicons?sz=128&domain={netloc}"
            except Exception:
                favicon_url = ""

        formatted_radio.append({
            "id": nanoid,
            "name": st.get("name", "Sem Nome"),
            "url": streams[0],
            "favicon": favicon_url,
            "category": id_to_category.get(nanoid, "Geral"),
            "codec": "MP3",
            "bitrate": 0,
            "votes": 0,
            "country": country_code,
            "countryName": country_names.get(country_code.lower(), country_code),
            "state": "",
            "tags": id_to_category.get(nanoid, "").lower(),
            "language": ", ".join(languages) if languages else "",
            "homepage": ""
        })
    
    # Salvar JSON global
    json_path = os.path.join(BASE, "downloads", "radio_famelack", "radio_todos.json")
    save_json(formatted_radio, json_path)
    print(f"\n  ✓ JSON global salvo: {json_path} ({len(formatted_radio)} estações)")
    
    # Salvar M3U global
    m3u_path = os.path.join(BASE, "downloads", "radio_famelack", "radio_todos.m3u")
    save_m3u(formatted_radio, m3u_path, is_radio=True)
    print(f"  ✓ M3U global salvo: {m3u_path}")
    
    # Por categoria
    cat_count = {}
    for st in formatted_radio:
        cat = st["category"]
        if cat not in cat_count:
            cat_count[cat] = []
        cat_count[cat].append(st)
    
    for cat, stations in cat_count.items():
        safe_cat = cat.lower().replace(" ", "_").replace("/", "_")
        save_json(stations, os.path.join(BASE, "downloads", "radio_famelack", "categorias", f"{safe_cat}.json"))
    
    print(f"  ✓ {len(cat_count)} categorias salvas em downloads/radio_famelack/categorias/")
    
    # Por país
    country_count = {}
    for st in formatted_radio:
        cc = st["country"]
        if cc not in country_count:
            country_count[cc] = []
        country_count[cc].append(st)
    
    for cc, stations in country_count.items():
        save_json(stations, os.path.join(BASE, "downloads", "radio_famelack", "paises", f"{cc}.json"))
    
    # Índice
    country_index = [{"code": cc, "name": stations[0].get("countryName", cc), "stations": len(stations)} 
                     for cc, stations in sorted(country_count.items(), key=lambda x: len(x[1]), reverse=True)]
    save_json(country_index, os.path.join(BASE, "downloads", "radio_famelack", "paises", "index.json"))
    
    print(f"  ✓ {len(country_count)} países salvos em downloads/radio_famelack/paises/")
    
    # Resumo
    print(f"\n  {'─'*50}")
    print(f"  RESUMO RÁDIO FAMELACK:")
    print(f"  Total de estações:   {len(formatted_radio)}")
    print(f"  Categorias:          {len(cat_count)}")
    print(f"  Países:              {len(country_count)}")
    print(f"  Top categorias:")
    for cat, sts in sorted(cat_count.items(), key=lambda x: len(x[1]), reverse=True)[:8]:
        print(f"    {cat:20s} → {len(sts)} estações")
    
    return len(formatted_radio)


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print("\n" + "█" * 60)
    print("  ⚡ FASTPLAY - BAIXAR TUDO (Famelack TV + Rádio)")
    print("█" * 60)
    
    start_time = time.time()
    
    total_tv = download_tv()
    total_radio = download_radio_famelack()
    
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    
    print("\n" + "█" * 60)
    print("  ✅ DOWNLOAD COMPLETO!")
    print("█" * 60)
    print(f"\n  📺 TV:      {total_tv} canais")
    print(f"  📻 Rádio:   {total_radio} estações")
    print(f"  ⏱️  Tempo:   {minutes}m {seconds}s")
    print(f"\n  📁 Estrutura de arquivos:")
    print(f"     downloads/")
    print(f"     ├── tv/")
    print(f"     │   ├── tv_todos.json       (todos os canais)")
    print(f"     │   ├── tv_todos.m3u")
    print(f"     │   ├── categorias/          (JSON por categoria)")
    print(f"     │   └── paises/              (JSON por país + index.json)")
    print(f"     └── radio_famelack/")
    print(f"         ├── radio_todos.json     (todas as estações)")
    print(f"         ├── radio_todos.m3u")
    print(f"         ├── categorias/          (JSON por categoria)")
    print(f"         └── paises/              (JSON por país + index.json)")
    print()

if __name__ == "__main__":
    main()
