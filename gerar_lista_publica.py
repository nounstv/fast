#!/usr/bin/env python3
"""
GERAR LISTA PÚBLICA - Xtream → M3U Pública
Lê os dados extraídos do provedor Xtream Codes e gera listas M3U e JSON
no mesmo formato usado pelo Famelack (público), prontas pro Nouns TV.
"""
import json
import os
import sys
import re

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
BASE = os.path.dirname(os.path.abspath(__file__))

# Diretório de origem (dados extraídos do Xtream)
XTREAM_DIR = os.path.join(BASE, "downloads", "xtream_cf9b10a37c")

# Diretório de saída (mesmo do Famelack público)
OUTPUT_DIR = os.path.join(BASE, "downloads")

# ==============================================================================
# HELPERS
# ==============================================================================
def load_json(filepath):
    """Carrega um arquivo JSON."""
    if not os.path.exists(filepath):
        print(f"  ✗ Arquivo não encontrado: {filepath}")
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ✗ Erro ao ler {filepath}: {e}")
        return None

def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_m3u(items, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for item in items:
            name = item.get("name", "Sem Nome")
            url = item.get("url", "")
            if not url:
                continue
            
            safe_name = name.replace('"', "'")
            tvg_id = item.get("tvgId", "")
            category = item.get("category", "Geral")
            country = item.get("country", "")
            logo = item.get("logo", "")
            
            attrs = f'tvg-id="{tvg_id}" tvg-name="{safe_name}"'
            if logo:
                attrs += f' tvg-logo="{logo}"'
            attrs += f' group-title="{category}"'
            if country:
                attrs += f' tvg-country="{country}"'
            
            f.write(f'#EXTINF:-1 {attrs},{safe_name}\n')
            f.write(f'{url}\n')

def detect_country_from_name(name):
    """Tenta detectar o país do canal pelo prefixo no nome."""
    # Padrões comuns em listas IPTV: "BR: Canal", "UK| Canal", "[US] Canal"
    patterns = [
        r'^([A-Z]{2})[\s]*[:\|]\s*',      # "BR: " ou "BR| "
        r'^\[([A-Z]{2})\]\s*',             # "[BR] "
        r'^\(([A-Z]{2})\)\s*',             # "(BR) "
        r'^([A-Z]{2})\s*[-–]\s*',          # "BR - "
    ]
    for pattern in patterns:
        match = re.match(pattern, name)
        if match:
            return match.group(1).upper()
    return ""

def detect_country_from_category(category):
    """Detecta país pela categoria se ela contiver indicação."""
    cat_lower = category.lower()
    
    country_keywords = {
        "brazil": "BR", "brasil": "BR", "br ": "BR",
        "usa": "US", "united states": "US", "us ": "US",
        "uk ": "GB", "united kingdom": "GB", "england": "GB",
        "portugal": "PT", "pt ": "PT",
        "spain": "ES", "espanha": "ES", "españa": "ES",
        "france": "FR", "french": "FR", "frança": "FR",
        "germany": "DE", "german": "DE", "alemanha": "DE",
        "italy": "IT", "italian": "IT", "itália": "IT",
        "argentina": "AR", "mexico": "MX", "méxico": "MX",
        "colombia": "CO", "chile": "CL", "peru": "PE",
        "canada": "CA", "japan": "JP", "india": "IN",
        "turkey": "TR", "arab": "SA", "korea": "KR",
    }
    
    for keyword, code in country_keywords.items():
        if keyword in cat_lower:
            return code
    return ""

def clean_channel_name(name):
    """Limpa o nome do canal removendo prefixos de país/qualidade."""
    # Remove prefixos comuns: "BR: ", "UK| ", "[US] ", "VIP: ", "NOW: "
    cleaned = re.sub(r'^(VIP|NOW|NEW|HD|SD|FHD|4K|UHD)[\s]*[:\|]\s*', '', name, flags=re.IGNORECASE)
    cleaned = re.sub(r'^[A-Z]{2}[\s]*[:\|]\s*', '', cleaned)
    cleaned = re.sub(r'^\[.*?\]\s*', '', cleaned)
    cleaned = re.sub(r'^\(.*?\)\s*', '', cleaned)
    return cleaned.strip()

def make_tvg_id(name, country):
    """Gera um tvg-id no formato padrão (ex: 'Globo.br')."""
    clean = re.sub(r'[^a-zA-Z0-9]', '', name)
    if country:
        return f"{clean}.{country.lower()}"
    return clean

def normalize_category(category):
    """Normaliza categorias do Xtream para categorias padrão."""
    cat_lower = category.lower().strip()
    
    # Mapeamento de categorias comuns
    mapping = {
        # Esportes
        "sports": "Sports", "esportes": "Sports", "sport": "Sports",
        "futebol": "Sports", "football": "Sports", "soccer": "Sports",
        "fight": "Sports", "luta": "Sports", "ufc": "Sports",
        "racing": "Sports", "f1": "Sports",
        # Filmes
        "movies": "Movies", "filmes": "Movies", "cinema": "Movies",
        "movie": "Movies", "filme": "Movies",
        # Notícias
        "news": "News", "noticias": "News", "notícias": "News",
        "jornalismo": "News",
        # Entretenimento
        "entertainment": "Entertainment", "entreter": "Entertainment",
        "entretenimento": "Entertainment",
        # Infantil
        "kids": "Kids", "infantil": "Kids", "children": "Kids",
        "cartoon": "Kids", "desenho": "Kids", "animação": "Kids",
        # Música
        "music": "Music", "musica": "Music", "música": "Music",
        # Documentário
        "documentary": "Documentary", "documentário": "Documentary",
        "documentario": "Documentary", "doc": "Documentary",
        # Religiosos
        "religious": "Religious", "religioso": "Religious",
        "gospel": "Religious", "religião": "Religious",
        # Educação
        "education": "Education", "educação": "Education",
        "educacional": "Education",
        # Cultura
        "culture": "Culture", "cultura": "Culture",
        # Séries
        "series": "Series", "série": "Series", "séries": "Series",
        # Culinária
        "cooking": "Cooking", "culinária": "Cooking", "food": "Cooking",
        # Estilo de vida
        "lifestyle": "Lifestyle", "estilo": "Lifestyle",
        # Compras
        "shop": "Shop", "shopping": "Shop", "compras": "Shop",
        # Comédia
        "comedy": "Comedy", "comédia": "Comedy",
        # Ciência
        "science": "Science", "ciência": "Science",
        # Viagem
        "travel": "Travel", "viagem": "Travel",
        # Negócios
        "business": "Business", "negócios": "Business",
    }
    
    for key, value in mapping.items():
        if key in cat_lower:
            return value
    
    # Se não mapeou, capitaliza
    return category.strip().title() if category.strip() else "General"


# ==============================================================================
# PROCESSAMENTO PRINCIPAL
# ==============================================================================
def process_xtream_tv():
    """Processa os canais de TV extraídos do Xtream e gera lista pública."""
    print("\n" + "=" * 60)
    print("  📺 PROCESSANDO TV AO VIVO (Xtream → Público)")
    print("=" * 60)
    
    tv_json_path = os.path.join(XTREAM_DIR, "tv", "tv_todos.json")
    channels = load_json(tv_json_path)
    
    if not channels:
        print("  ✗ Nenhum canal de TV encontrado nos dados Xtream")
        return [], 0
    
    print(f"  ✓ {len(channels)} canais carregados do Xtream")
    
    # Processar e formatar
    formatted = []
    categories_seen = set()
    countries_seen = set()
    skipped = 0
    
    for ch in channels:
        name = ch.get("name", "").strip()
        url = ch.get("url", "")
        category = ch.get("category", "Geral")
        logo = ch.get("logo", "")
        
        if not name or not url:
            skipped += 1
            continue
        
        # Detectar país
        country = detect_country_from_name(name)
        if not country:
            country = detect_country_from_category(category)
        
        # Limpar nome
        display_name = clean_channel_name(name)
        if not display_name:
            display_name = name
        
        # Normalizar categoria
        norm_category = normalize_category(category)
        
        # Gerar tvg-id
        tvg_id = make_tvg_id(display_name, country)
        
        formatted.append({
            "tvgId": tvg_id,
            "name": display_name,
            "originalName": name,
            "url": url,
            "logo": logo,
            "category": norm_category,
            "originalCategory": category,
            "country": country,
            "type": "live"
        })
        
        categories_seen.add(norm_category)
        if country:
            countries_seen.add(country)
    
    print(f"  ✓ {len(formatted)} canais processados ({skipped} ignorados)")
    print(f"  ✓ {len(categories_seen)} categorias | {len(countries_seen)} países detectados")
    
    return formatted, len(formatted)


def process_xtream_vod():
    """Processa os VODs extraídos do Xtream."""
    print("\n" + "=" * 60)
    print("  🎬 PROCESSANDO VOD / FILMES (Xtream → Público)")
    print("=" * 60)
    
    vod_json_path = os.path.join(XTREAM_DIR, "vod", "vod_todos.json")
    movies = load_json(vod_json_path)
    
    if not movies:
        print("  ✗ Nenhum filme encontrado nos dados Xtream")
        return [], 0
    
    print(f"  ✓ {len(movies)} filmes carregados do Xtream")
    
    formatted = []
    for m in movies:
        name = m.get("name", "").strip()
        url = m.get("url", "")
        category = m.get("category", "Filmes")
        logo = m.get("logo", "")
        
        if not name or not url:
            continue
        
        country = detect_country_from_name(name)
        display_name = clean_channel_name(name)
        if not display_name:
            display_name = name
        
        formatted.append({
            "tvgId": make_tvg_id(display_name, country),
            "name": display_name,
            "originalName": name,
            "url": url,
            "logo": logo,
            "category": normalize_category(category),
            "originalCategory": category,
            "country": country,
            "type": "vod"
        })
    
    print(f"  ✓ {len(formatted)} filmes processados")
    return formatted, len(formatted)


def merge_with_famelack(xtream_channels):
    """Mescla a lista Xtream com a lista Famelack existente, removendo duplicatas."""
    print("\n" + "─" * 60)
    print("  🔀 MESCLANDO COM LISTA FAMELACK (pública)")
    print("─" * 60)
    
    famelack_path = os.path.join(BASE, "downloads", "tv_famelack", "tv_todos.json")
    famelack = load_json(famelack_path)
    
    if not famelack:
        print("  ⚠ Lista Famelack não encontrada, usando apenas Xtream")
        return xtream_channels
    
    print(f"  ✓ {len(famelack)} canais Famelack carregados")
    
    # Converter Famelack para o mesmo formato
    famelack_formatted = []
    for ch in famelack:
        famelack_formatted.append({
            "tvgId": ch.get("id", ""),
            "name": ch.get("name", ""),
            "originalName": ch.get("name", ""),
            "url": ch.get("url", ""),
            "logo": "",
            "category": ch.get("category", "General"),
            "originalCategory": ch.get("category", "General"),
            "country": ch.get("country", ""),
            "type": "live",
            "source": "famelack"
        })
    
    # Marcar Xtream
    for ch in xtream_channels:
        ch["source"] = "xtream"
    
    # Mesclar: Xtream primeiro (prioridade), depois Famelack
    # Remover duplicatas pelo nome normalizado
    seen_names = set()
    merged = []
    
    for ch in xtream_channels:
        key = ch["name"].lower().strip()
        if key not in seen_names:
            seen_names.add(key)
            merged.append(ch)
    
    famelack_added = 0
    for ch in famelack_formatted:
        key = ch["name"].lower().strip()
        if key not in seen_names:
            seen_names.add(key)
            merged.append(ch)
            famelack_added += 1
    
    print(f"  ✓ Mesclado: {len(xtream_channels)} Xtream + {famelack_added} Famelack únicos = {len(merged)} total")
    
    return merged


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print("\n" + "█" * 60)
    print("  ⚡ GERAR LISTA PÚBLICA - Xtream → Nouns TV")
    print("█" * 60)
    
    # Verificar se dados existem
    if not os.path.exists(XTREAM_DIR):
        print(f"\n  ✗ Dados Xtream não encontrados em: {XTREAM_DIR}")
        print(f"  → Execute primeiro: python3 extrair_xtream.py")
        return
    
    # Menu
    print("\n  O que deseja gerar?\n")
    print("  1 - 📺 Apenas TV ao vivo (M3U + JSON)")
    print("  2 - 🎬 Apenas VOD/Filmes (M3U + JSON)")
    print("  3 - ⚡ TV + VOD (tudo)")
    print("  4 - 🔀 TV mesclada com Famelack (pública unificada)")
    
    choice = input("\n  Escolha (1-4): ").strip()
    
    all_channels = []
    
    # TV
    if choice in ["1", "3", "4"]:
        tv_channels, tv_count = process_xtream_tv()
        
        if choice == "4":
            tv_channels = merge_with_famelack(tv_channels)
        
        all_channels.extend(tv_channels)
        
        # Salvar TV
        tv_out_dir = os.path.join(OUTPUT_DIR, "tv")
        
        save_m3u(tv_channels, os.path.join(tv_out_dir, "tv_todos.m3u"))
        print(f"\n  ✓ M3U salvo: downloads/tv/tv_todos.m3u")
        
        save_json(tv_channels, os.path.join(tv_out_dir, "tv_todos.json"))
        print(f"  ✓ JSON salvo: downloads/tv/tv_todos.json")
        
        # Por categoria
        by_cat = {}
        for ch in tv_channels:
            cat = ch["category"]
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(ch)
        
        for cat, chs in by_cat.items():
            safe_cat = cat.lower().replace(" ", "_").replace("/", "_")
            save_json(chs, os.path.join(tv_out_dir, "categorias", f"{safe_cat}.json"))
            save_m3u(chs, os.path.join(tv_out_dir, "categorias", f"{safe_cat}.m3u"))
        
        # Índice de categorias
        cat_index = [{"name": cat, "count": len(chs)} 
                     for cat, chs in sorted(by_cat.items(), key=lambda x: len(x[1]), reverse=True)]
        save_json(cat_index, os.path.join(tv_out_dir, "categorias", "index.json"))
        
        # Por país
        by_country = {}
        for ch in tv_channels:
            cc = ch.get("country", "")
            if cc:
                if cc not in by_country:
                    by_country[cc] = []
                by_country[cc].append(ch)
        
        for cc, chs in by_country.items():
            save_json(chs, os.path.join(tv_out_dir, "paises", f"{cc}.json"))
        
        country_index = [{"code": cc, "count": len(chs)} 
                         for cc, chs in sorted(by_country.items(), key=lambda x: len(x[1]), reverse=True)]
        save_json(country_index, os.path.join(tv_out_dir, "paises", "index.json"))
        
        print(f"  ✓ {len(by_cat)} categorias | {len(by_country)} países salvos")
    
    # VOD
    if choice in ["2", "3"]:
        vod_channels, vod_count = process_xtream_vod()
        all_channels.extend(vod_channels)
        
        vod_out_dir = os.path.join(OUTPUT_DIR, "vod")
        
        save_m3u(vod_channels, os.path.join(vod_out_dir, "vod_todos.m3u"))
        print(f"\n  ✓ M3U salvo: downloads/vod/vod_todos.m3u")
        
        save_json(vod_channels, os.path.join(vod_out_dir, "vod_todos.json"))
        print(f"  ✓ JSON salvo: downloads/vod/vod_todos.json")
        
        by_cat = {}
        for m in vod_channels:
            cat = m["category"]
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(m)
        
        for cat, movies in by_cat.items():
            safe_cat = cat.lower().replace(" ", "_").replace("/", "_")
            save_json(movies, os.path.join(vod_out_dir, "categorias", f"{safe_cat}.json"))
        
        cat_index = [{"name": cat, "count": len(movies)} 
                     for cat, movies in sorted(by_cat.items(), key=lambda x: len(x[1]), reverse=True)]
        save_json(cat_index, os.path.join(vod_out_dir, "categorias", "index.json"))
        
        print(f"  ✓ {len(by_cat)} categorias de VOD salvas")
    
    # Resumo
    print("\n" + "█" * 60)
    print("  ✅ LISTA PÚBLICA GERADA!")
    print("█" * 60)
    print(f"\n  Total de itens: {len(all_channels)}")
    print(f"\n  📁 Arquivos em: downloads/tv/ e downloads/vod/")
    print(f"\n  📌 Próximos passos:")
    print(f"     1. Revise os arquivos gerados")
    print(f"     2. Faça commit e push pro GitHub")
    print(f"     3. Use a URL pública no Nouns TV:")
    print(f"        https://raw.githubusercontent.com/nounstv/fast/main/downloads/tv/tv_todos.m3u")
    print()


if __name__ == "__main__":
    main()
