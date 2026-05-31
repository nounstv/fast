#!/usr/bin/env python3
import json
import os
import sys

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

def main():
    json_path = "/Users/rodrigo/rodrigom3e/nouns/ProjetoCompletoNouns/developer/fast/downloads/radios_GLOBAL.json"
    m3u_path = "/Users/rodrigo/rodrigom3e/nouns/ProjetoCompletoNouns/developer/fast/downloads/radios_GLOBAL.m3u"
    
    if not os.path.exists(json_path):
        print(f"Erro: Arquivo não encontrado: {json_path}")
        sys.exit(1)
        
    print(f"Lendo {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        stations = json.load(f)
        
    print(f"Total de estações encontradas: {len(stations)}")
    print("Convertendo para .m3u...")
    
    try:
        with open(m3u_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for st in stations:
                name = (st.get("name", "Sem Nome") or "Sem Nome").strip()
                url = st.get("url") or st.get("url_resolved", "")
                category_key = st.get("category", "pop")
                genre = get_genre_label(category_key)
                country = (st.get("country", "??") or "??").upper()
                favicon = st.get("favicon", "")
                
                if not url:
                    continue
                
                # Substituir aspas duplas no nome para evitar quebra de atributos no M3U
                safe_name = name.replace('"', "'")
                
                logo_attr = f' tvg-logo="{favicon}"' if favicon else ""
                
                f.write(f'#EXTINF:-1 radio="true" tvg-name="{safe_name}"{logo_attr} group-title="{genre}" tvg-country="{country}",{safe_name}\n')
                f.write(f'{url}\n')
                
        print(f"Sucesso! Arquivo .m3u salvo em: {m3u_path}")
    except Exception as e:
        print(f"Erro ao salvar arquivo .m3u: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
