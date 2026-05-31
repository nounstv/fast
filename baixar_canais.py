#!/usr/bin/env python3
import urllib.request
import json
import os
import sys

# URL base para obter os arquivos brutos do repositório oficial de dados do Famelack
RAW_URL_BASE = "https://raw.githubusercontent.com/famelack/famelack-data/main/tv/raw/categories"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Categorias conhecidas no repositório do Famelack
CATEGORIES = [
    "animation", "auto", "business", "classic", "comedy", "cooking", "culture", 
    "documentary", "education", "entertainment", "family", "general", "kids", 
    "legislative", "lifestyle", "movies", "music", "news", "outdoor", "public",
    "relax", "religious", "science", "series", "shop", "show", "sports",
    "top-news", "travel", "weather"
]

def fetch_json(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Erro ao acessar {url}: {e}")
        return None

def build_category_map():
    """Baixa as categorias para mapear o nanoid de cada canal para sua respectiva categoria."""
    print("\nMapeando categorias dos canais (isso pode levar alguns segundos)...")
    id_to_category = {}
    
    for cat in CATEGORIES:
        print(f"-> Mapeando: {cat}...", end="\r")
        sys.stdout.flush()
        url = f"{RAW_URL_BASE}/{cat}.json"
        cat_data = fetch_json(url)
        if cat_data:
            for item in cat_data:
                nanoid = item.get("nanoid")
                if nanoid:
                    # Mapeia o id para a categoria formatada
                    id_to_category[nanoid] = cat.capitalize()
    
    print("\n✓ Categorias mapeadas com sucesso!")
    return id_to_category

def save_m3u(channels, filepath, category_map):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for ch in channels:
                name = ch.get("name", "Sem Nome")
                country = ch.get("country", "??").upper()
                nanoid = ch.get("nanoid", "")
                category = category_map.get(nanoid, "Geral")
                
                # Pega o primeiro stream_url disponível
                streams = ch.get("stream_urls", [])
                if not streams:
                    continue
                    
                stream_url = streams[0]
                
                # Linha de metadados padrão M3U
                f.write(f'#EXTINF:-1 tvg-id="{nanoid}" tvg-name="{name}" group-title="{category}" tvg-country="{country}", {name} ({country})\n')
                f.write(f"{stream_url}\n")
        print(f"✓ Playlist M3U salva com sucesso em: {filepath}")
    except Exception as e:
        print(f"Erro ao salvar arquivo M3U: {e}")

def save_json(channels, filepath, category_map):
    # Formata a estrutura dos canais de maneira limpa para uso no player
    formatted = []
    for ch in channels:
        streams = ch.get("stream_urls", [])
        if not streams:
            continue
            
        nanoid = ch.get("nanoid", "")
        formatted.append({
            "id": nanoid,
            "name": ch.get("name", "Sem Nome"),
            "url": streams[0],
            "category": category_map.get(nanoid, "Geral"),
            "country": ch.get("country", "??").upper(),
            "description": f"Canal de TV originário de {ch.get('country', '??').upper()}. Idioma: {', '.join(ch.get('languages', []))}.",
            "logoText": ch.get("name", "TV")[:3].upper()
        })
        
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(formatted, f, indent=2, ensure_ascii=False)
        print(f"✓ Catálogo JSON salvo com sucesso em: {filepath}")
    except Exception as e:
        print(f"Erro ao salvar arquivo JSON: {e}")

def main():
    print("=" * 60)
    print("      BAIXADOR E CATALOGADOR DE CANAIS - FAMELACK TV")
    print("=" * 60)
    
    # 1. Filtro de País
    country_filter = input("\nFiltrar por país específico? (Ex: BR, US, ES - Deixe em BRANCO para todos): ").strip().lower()
    
    # 2. Filtro de Tipo de Stream
    only_m3u8 = input("Baixar apenas canais com streams diretos .m3u8 (HLS)? (S/N): ").strip().lower()
    only_m3u8 = only_m3u8 == 's' or only_m3u8 == 'sim' or only_m3u8 == ''
    
    # 3. Formato de saída
    print("\nFormatos de saída:")
    print("1 - Apenas Playlist M3U (para VLC, IPTV Players, etc.)")
    print("2 - Apenas arquivo JSON (para nosso player customizado)")
    print("3 - Ambos os formatos")
    format_choice = input("Escolha o formato (1, 2 ou 3): ").strip()
    
    # 4. Download da base completa
    all_url = f"{RAW_URL_BASE}/all.json"
    print("\nBaixando base de dados geral do Famelack...")
    all_channels = fetch_json(all_url)
    
    if not all_channels:
        print("Erro crítico: Não foi possível obter os dados do Famelack.")
        return
        
    print(f"Base de dados baixada com {len(all_channels)} canais no total.")
    
    # Mapeamento de categorias
    category_map = {}
    if format_choice in ["1", "2", "3"]:
        category_map = build_category_map()
        
    # Aplicando filtros
    filtered_channels = []
    for ch in all_channels:
        # Filtro de país
        if country_filter and ch.get("country", "").lower() != country_filter:
            continue
            
        streams = ch.get("stream_urls", [])
        
        # Filtro de streams vazios
        if not streams:
            continue
            
        # Filtro por formato HLS (.m3u8)
        if only_m3u8:
            has_m3u8 = any(".m3u8" in url.lower() for url in streams)
            if not has_m3u8:
                continue
                
        filtered_channels.append(ch)
        
    print(f"\nFiltros aplicados! {len(filtered_channels)} canais correspondem aos critérios.")
    
    if len(filtered_channels) == 0:
        print("Nenhum canal corresponde aos filtros selecionados. Processo encerrado.")
        return
        
    # Salvando os arquivos
    os.makedirs("downloads", exist_ok=True)
    
    suffix = f"_{country_filter.upper()}" if country_filter else "_TODOS"
    
    if format_choice in ["1", "3"]:
        m3u_path = f"downloads/famelack_canais{suffix}.m3u"
        save_m3u(filtered_channels, m3u_path, category_map)
        
    if format_choice in ["2", "3"]:
        json_path = f"downloads/famelack_canais{suffix}.json"
        save_json(filtered_channels, json_path, category_map)
        
    print("\n" + "=" * 60)
    print(f" Sucesso! Arquivos salvos na pasta 'downloads/'.")
    print("=" * 60)

if __name__ == "__main__":
    main()
