#!/usr/bin/env python3
import urllib.request
import json
import os
import sys
import time

# API do Radio-Browser (servidores disponíveis)
API_SERVERS = [
    "https://de1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
    "https://at1.api.radio-browser.info"
]

headers = {
    "User-Agent": "FastPlay-RadioDownloader/1.0"
}

# Mapeamento de gêneros para categorização
GENRE_MAP = {
    "sertanejo": ["sertanejo", "country", "caipira", "modão", "modao"],
    "gospel": ["gospel", "religios", "evangel", "católic", "catolic", "cristã", "crista", "adventist", "church", "worship", "praise"],
    "rock": ["rock", "metal", "punk", "indie", "grunge", "alternative", "hard rock"],
    "pop": ["pop", "hits", "top 40", "dance", "edm", "eletronic", "techno", "house", "funk", "hip hop", "rap", "reggaeton", "trap"],
    "mpb": ["mpb", "bossa", "brasileir", "jazz", "blues", "soul", "r&b", "clássic", "classic", "erudita", "instrumental"],
    "pagode": ["pagode", "samba", "axé", "axe", "forró", "forro", "baião", "xote", "arrocha"],
    "news": ["news", "notícia", "noticia", "jornalism", "talk", "esporte", "sport", "debate", "informaç", "informac"]
}

def fetch_json(url):
    """Faz uma requisição GET e retorna o JSON parseado."""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return None

def categorize_station(station):
    """Categoriza uma estação com base nas tags e nome."""
    tags = (station.get("tags", "") or "").lower()
    name = (station.get("name", "") or "").lower()
    combined = tags + " " + name

    for genre, keywords in GENRE_MAP.items():
        for kw in keywords:
            if kw in combined:
                return genre
    
    return "pop"  # padrão

def get_genre_label(genre_key):
    """Retorna o label amigável de um gênero."""
    labels = {
        "pop": "Pop / Hits",
        "rock": "Rock",
        "sertanejo": "Sertanejo",
        "gospel": "Gospel",
        "mpb": "MPB / Jazz",
        "pagode": "Pagode / Samba",
        "news": "Notícias / Talk"
    }
    return labels.get(genre_key, genre_key.capitalize())

def format_stations(stations):
    """Formata lista de estações da API para o formato do player."""
    formatted = []
    for st in stations:
        url = st.get("url_resolved", "") or st.get("url", "")
        if not url:
            continue
        formatted.append({
            "id": st.get("stationuuid", ""),
            "name": (st.get("name", "Sem Nome") or "Sem Nome").strip(),
            "url": url,
            "favicon": st.get("favicon", "") or "",
            "category": categorize_station(st),
            "codec": st.get("codec", "MP3") or "MP3",
            "bitrate": st.get("bitrate", 0) or 0,
            "votes": st.get("votes", 0) or 0,
            "country": (st.get("countrycode", "??") or "??").upper(),
            "countryName": st.get("country", "") or "",
            "state": st.get("state", "") or "",
            "tags": st.get("tags", "") or "",
            "language": st.get("language", "") or "",
            "homepage": st.get("homepage", "") or ""
        })
    return formatted

def save_json(data, filepath):
    """Salva dados em JSON."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"  ✗ Erro ao salvar {filepath}: {e}")
        return False

def save_m3u(stations, filepath):
    """Salva a lista de estações em formato M3U."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for st in stations:
                name = (st.get("name", "Sem Nome") or "Sem Nome").strip()
                url = st.get("url_resolved", "") or st.get("url", "")
                genre = get_genre_label(categorize_station(st))
                country = (st.get("countrycode", "??") or "??").upper()
                
                if not url:
                    continue
                
                f.write(f'#EXTINF:-1 radio="true" tvg-name="{name}" group-title="{genre}" tvg-country="{country}",{name}\n')
                f.write(f'{url}\n')
        return True
    except Exception as e:
        print(f"  ✗ Erro ao salvar {filepath}: {e}")
        return False

def fetch_countries(server):
    """Busca a lista de países disponíveis na API."""
    url = f"{server}/json/countries"
    data = fetch_json(url)
    if data:
        # Filtra apenas países com estações
        return [c for c in data if c.get("stationcount", 0) > 0]
    return None

def fetch_stations_for_country(server, country_name, limit=500):
    """Busca estações de um país específico."""
    encoded = urllib.request.quote(country_name)
    url = f"{server}/json/stations/bycountry/{encoded}?limit={limit}&order=votes&reverse=true&hidebroken=true"
    return fetch_json(url)

def download_single_country():
    """Modo: Baixar rádios de um país específico."""
    print("\nPaíses disponíveis: BR (Brasil), PT (Portugal), US (EUA), etc.")
    print("Digite 'lista' para ver todos os países disponíveis.")
    country_input = input("\nFiltrar por país? (Ex: BR - Deixe em BRANCO para Brasil): ").strip()
    
    # Mapa de códigos comuns
    country_names = {
        "BR": "Brazil", "PT": "Portugal", "US": "The United States of America",
        "AR": "Argentina", "ES": "Spain", "MX": "Mexico", "CO": "Colombia",
        "CL": "Chile", "PE": "Peru", "UY": "Uruguay", "PY": "Paraguay",
        "GB": "The United Kingdom of Great Britain and Northern Ireland",
        "FR": "France", "DE": "Germany", "IT": "Italy", "JP": "Japan",
        "CA": "Canada", "AU": "Australia", "IN": "India", "RU": "Russia"
    }
    
    server = API_SERVERS[0]

    if country_input.lower() == "lista":
        print("\nBuscando lista de países...")
        countries = fetch_countries(server)
        if countries:
            countries.sort(key=lambda c: c.get("stationcount", 0), reverse=True)
            print(f"\n{'País':<45} {'Estações':>10}")
            print("-" * 57)
            for c in countries[:60]:
                name = c.get("name", "?")
                count = c.get("stationcount", 0)
                code = c.get("iso_3166_1", "??")
                print(f"  {code} - {name:<40} {count:>6}")
            print(f"\n... total: {len(countries)} países")
        country_input = input("\nDigite o código do país (Ex: BR): ").strip().upper()
    else:
        country_input = country_input.upper()
    
    if not country_input:
        country_filter = "Brazil"
    else:
        country_filter = country_names.get(country_input, country_input)
    
    # Filtro de gênero
    print("\nGêneros disponíveis:")
    genres = list(GENRE_MAP.keys())
    for i, g in enumerate(genres, 1):
        print(f"  {i} - {get_genre_label(g)}")
    print(f"  0 - Todos os gêneros")
    genre_choice = input("Escolha o gênero (0 para todos): ").strip()
    selected_genre = None
    if genre_choice.isdigit() and 1 <= int(genre_choice) <= len(genres):
        selected_genre = genres[int(genre_choice) - 1]
        print(f"  → Filtro de gênero: {get_genre_label(selected_genre)}")
    
    # Bitrate mínimo
    min_bitrate_input = input("\nBitrate mínimo (kbps)? (Ex: 128 - BRANCO para todos): ").strip()
    min_bitrate = int(min_bitrate_input) if min_bitrate_input.isdigit() else 0
    
    # Limite
    limit_input = input("Quantidade máxima? (Padrão: 500): ").strip()
    limit = int(limit_input) if limit_input.isdigit() and int(limit_input) > 0 else 500
    
    # Formato
    print("\nFormatos de saída:")
    print("  1 - Apenas JSON (para o FastPlay)")
    print("  2 - Apenas M3U (para VLC, IPTV Players)")
    print("  3 - Ambos os formatos")
    format_choice = input("Escolha (1, 2 ou 3): ").strip()
    if format_choice not in ["1", "2", "3"]:
        format_choice = "1"

    # Baixar
    print(f"\nBaixando estações de '{country_filter}'...")
    
    all_stations = None
    for srv in API_SERVERS:
        print(f"  → Tentando: {srv}...")
        all_stations = fetch_stations_for_country(srv, country_filter, limit)
        if all_stations:
            print(f"  ✓ {len(all_stations)} estações encontradas!")
            server = srv
            break
    
    if not all_stations:
        print("\n✗ Não foi possível conectar. Verifique sua internet.")
        return
    
    # Filtros
    filtered = []
    for st in all_stations:
        url = st.get("url_resolved", "") or st.get("url", "")
        if not url:
            continue
        bitrate = st.get("bitrate", 0) or 0
        if min_bitrate > 0 and bitrate < min_bitrate:
            continue
        if selected_genre and categorize_station(st) != selected_genre:
            continue
        filtered.append(st)
    
    print(f"\n{len(filtered)} estações após filtros.")
    
    if not filtered:
        print("Nenhuma estação encontrada. Tente filtros mais amplos.")
        return
    
    # Resumo
    genre_count = {}
    for st in filtered:
        g = categorize_station(st)
        genre_count[g] = genre_count.get(g, 0) + 1
    print("\nDistribuição por gênero:")
    for g, count in sorted(genre_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  {get_genre_label(g):20s} → {count}")
    
    # Salvar
    os.makedirs("downloads", exist_ok=True)
    country_code = country_filter.replace(" ", "_").upper()[:3]
    suffix = f"_{country_code}"
    if selected_genre:
        suffix += f"_{selected_genre}"
    
    if format_choice in ["1", "3"]:
        path = f"downloads/radios{suffix}.json"
        formatted = format_stations(filtered)
        if save_json(formatted, path):
            print(f"\n✓ JSON salvo: {path} ({len(formatted)} estações)")
    
    if format_choice in ["2", "3"]:
        path = f"downloads/radios{suffix}.m3u"
        if save_m3u(filtered, path):
            print(f"✓ M3U salvo: {path}")


def download_all_countries():
    """Modo: Baixar rádios de TODOS os países (um JSON por país + um JSON global)."""
    
    # Limite por país
    limit_input = input("\nMáximo de estações POR PAÍS? (Padrão: 200): ").strip()
    limit = int(limit_input) if limit_input.isdigit() and int(limit_input) > 0 else 200
    
    # Mínimo de estações para incluir o país
    min_stations_input = input("Mínimo de estações para incluir um país? (Padrão: 5): ").strip()
    min_stations = int(min_stations_input) if min_stations_input.isdigit() else 5
    
    # Formato
    print("\nModo de saída:")
    print("  1 - Um JSON por país (downloads/radios/BR.json, US.json, etc.)")
    print("  2 - Um JSON global com todos os países juntos")
    print("  3 - Ambos (por país + global)")
    mode_choice = input("Escolha (1, 2 ou 3): ").strip()
    if mode_choice not in ["1", "2", "3"]:
        mode_choice = "3"
    
    server = API_SERVERS[0]
    
    # Buscar lista de países
    print("\nBuscando lista de países disponíveis...")
    countries = None
    for srv in API_SERVERS:
        countries = fetch_countries(srv)
        if countries:
            server = srv
            break
    
    if not countries:
        print("✗ Não foi possível obter a lista de países.")
        return
    
    # Filtrar países com mínimo de estações
    valid_countries = [c for c in countries if c.get("stationcount", 0) >= min_stations]
    valid_countries.sort(key=lambda c: c.get("stationcount", 0), reverse=True)
    
    total_countries = len(valid_countries)
    print(f"\n{total_countries} países com ≥ {min_stations} estações encontrados.")
    print(f"Limite de {limit} estações por país.")
    
    confirm = input(f"\nIniciar download de {total_countries} países? (S/N): ").strip().lower()
    if confirm not in ["s", "sim", "y", "yes", ""]:
        print("Download cancelado.")
        return
    
    # Criar diretórios
    os.makedirs("downloads/radios", exist_ok=True)
    
    all_global_stations = []
    success_count = 0
    fail_count = 0
    country_summary = []
    
    print(f"\n{'='*60}")
    print(f" Iniciando download de {total_countries} países...")
    print(f"{'='*60}\n")
    
    for i, country in enumerate(valid_countries, 1):
        country_name = country.get("name", "Unknown")
        country_code = country.get("iso_3166_1", "??").upper()
        expected_count = country.get("stationcount", 0)
        
        progress = f"[{i}/{total_countries}]"
        print(f"  {progress} {country_code} - {country_name} (~{expected_count} estações)...", end=" ", flush=True)
        
        # Fetch stations
        stations = fetch_stations_for_country(server, country_name, limit)
        
        if not stations:
            print("✗ falhou")
            fail_count += 1
            # Tentar outro servidor
            for srv in API_SERVERS:
                if srv != server:
                    stations = fetch_stations_for_country(srv, country_name, limit)
                    if stations:
                        server = srv
                        break
            if not stations:
                continue
        
        # Filtrar só os que têm URL
        valid = [s for s in stations if s.get("url_resolved") or s.get("url")]
        
        if not valid:
            print("✗ sem streams válidos")
            fail_count += 1
            continue
        
        formatted = format_stations(valid)
        
        # Salvar JSON individual por país
        if mode_choice in ["1", "3"]:
            country_path = f"downloads/radios/{country_code}.json"
            save_json(formatted, country_path)
        
        # Acumular para o global
        all_global_stations.extend(formatted)
        
        success_count += 1
        country_summary.append({
            "code": country_code,
            "name": country_name,
            "stations": len(formatted)
        })
        
        print(f"✓ {len(formatted)} estações")
        
        # Pequeno delay para não sobrecarregar a API
        time.sleep(0.3)
    
    # Salvar JSON global
    if mode_choice in ["2", "3"] and all_global_stations:
        global_path = "downloads/radios_GLOBAL.json"
        if save_json(all_global_stations, global_path):
            print(f"\n✓ JSON global salvo: {global_path}")
    
    # Salvar índice de países
    index_path = "downloads/radios/index.json"
    save_json(country_summary, index_path)
    
    # Resumo final
    print(f"\n{'='*60}")
    print(f" DOWNLOAD CONCLUÍDO!")
    print(f"{'='*60}")
    print(f"\n  Países baixados:  {success_count}/{total_countries}")
    print(f"  Países com falha: {fail_count}")
    print(f"  Total de estações: {len(all_global_stations)}")
    print(f"\n  Arquivos salvos em: downloads/radios/")
    
    if country_summary:
        print(f"\n  Top 10 países por quantidade:")
        top = sorted(country_summary, key=lambda x: x["stations"], reverse=True)[:10]
        for cs in top:
            print(f"    {cs['code']} - {cs['name']:<35} {cs['stations']:>5} estações")


def main():
    print("=" * 60)
    print("      BAIXADOR DE ESTAÇÕES DE RÁDIO - RADIO BROWSER")
    print("=" * 60)
    
    print("\nModos disponíveis:")
    print("  1 - Baixar rádios de UM país específico")
    print("  2 - Baixar rádios de TODOS os países (um JSON por país)")
    
    mode = input("\nEscolha o modo (1 ou 2): ").strip()
    
    if mode == "2":
        download_all_countries()
    else:
        download_single_country()
    
    print("\n" + "=" * 60)
    print(" Sucesso! Arquivos na pasta 'downloads/'.")
    print("=" * 60)

if __name__ == "__main__":
    main()
