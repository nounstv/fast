#!/usr/bin/env python3
"""
Merge TV channels from two sources:
- tvFamelack (curated, more stable streams)
- tv/IPTV (larger list, many streams but some outdated)

Strategy:
- For channels in BOTH: keep Famelack data (more reliable URLs), 
  but enrich with IPTV data (logo, streams array)
- For channels ONLY in Famelack: keep as-is
- For channels ONLY in IPTV: add them (more channels = better)
- Normalize all to the same schema

Output: fast/tv_merged.json
"""

import json
import os
import hashlib

BASE = os.path.dirname(os.path.abspath(__file__))

# Load sources
# Famelack is in downloads/tv/tv_todos.json
famelack = json.load(open(os.path.join(BASE, 'downloads', 'tv', 'tv_todos.json')))
# IPTV is also in downloads/tv/tv_todos.json ? Wait, let me check the scripts output.
# No, in baixar_tudo.py, it was saving to downloads/tv/tv_todos.json. 
# In baixar_iptv_org.py, it saves to downloads/tv/tv_todos.json. They would overwrite each other if we use the same downloads folder!
# Ah! Famelack TV downloaded outputs to downloads/tv/tv_todos.json. 
# But we need them separate to merge them. Let's make sure Famelack outputs to downloads/tv_famelack/tv_todos.json.
# Let's adjust merge_tv.py loader to expect Famelack at downloads/tv_famelack/tv_todos.json, and IPTV at downloads/tv/tv_todos.json.
famelack = json.load(open(os.path.join(BASE, 'downloads', 'tv_famelack', 'tv_todos.json')))
iptv = json.load(open(os.path.join(BASE, 'downloads', 'tv', 'tv_todos.json')))

print(f'Famelack: {len(famelack)} canais')
print(f'IPTV: {len(iptv)} canais')

# Index by normalized name
def normalize(name):
    return name.lower().strip()

famelack_by_name = {}
for ch in famelack:
    key = normalize(ch['name'])
    if key not in famelack_by_name:  # first occurrence wins
        famelack_by_name[key] = ch

iptv_by_name = {}
for ch in iptv:
    key = normalize(ch['name'])
    if key not in iptv_by_name:
        iptv_by_name[key] = ch

overlap = set(famelack_by_name.keys()) & set(iptv_by_name.keys())
only_famelack = set(famelack_by_name.keys()) - set(iptv_by_name.keys())
only_iptv = set(iptv_by_name.keys()) - set(famelack_by_name.keys())

print(f'\nOverlap: {len(overlap)}')
print(f'Só Famelack: {len(only_famelack)}')
print(f'Só IPTV: {len(only_iptv)}')

def gen_id(name, country):
    """Generate a short stable ID from name+country"""
    h = hashlib.md5(f'{name}:{country}'.encode()).hexdigest()[:12]
    return f'tv_{h}'

def to_merged(ch, source='famelack', iptv_ch=None):
    """Normalize a channel to the merged schema"""
    result = {
        'id': ch.get('id') or gen_id(ch['name'], ch.get('country', '')),
        'name': ch['name'],
        'logo': ch.get('logo') or (iptv_ch or {}).get('logo', ''),
        'logoText': ch.get('logoText') or ch['name'][:3].upper(),
        'url': ch['url'],
        'httpReferrer': ch.get('httpReferrer') or (iptv_ch or {}).get('httpReferrer'),
        'userAgent': ch.get('userAgent') or (iptv_ch or {}).get('userAgent'),
        'streams': ch.get('allStreams', ch.get('streams', [])),
        'category': ch.get('category', 'General'),
        'categories': ch.get('categories', []),
        'country': ch.get('country', ''),
        'countryName': ch.get('countryName', ''),
        'languages': ch.get('languages', []),
        'description': ch.get('description', ''),
        'source': source,
    }
    
    # Normalize streams to array of URLs for allStreams
    if isinstance(result['streams'], list):
        urls = []
        for s in result['streams']:
            if isinstance(s, str):
                urls.append(s)
            elif isinstance(s, dict) and 'url' in s:
                urls.append(s['url'])
        # Add the IPTV URL if it's different and available
        if iptv_ch and iptv_ch['url'] not in urls:
            urls.append(iptv_ch['url'])
        result['streams'] = [{'url': u, 'http_referrer': None, 'user_agent': None} for u in urls]
    
    return result

merged = []

# 1. Channels in BOTH: Famelack data, enriched with IPTV
for name in sorted(overlap):
    fch = famelack_by_name[name]
    ich = iptv_by_name[name]
    merged.append(to_merged(fch, source='both', iptv_ch=ich))

# 2. Channels ONLY in Famelack
for name in sorted(only_famelack):
    fch = famelack_by_name[name]
    merged.append(to_merged(fch, source='famelack'))

# 3. Channels ONLY in IPTV
for name in sorted(only_iptv):
    ich = iptv_by_name[name]
    merged.append(to_merged(ich, source='iptv'))

print(f'\nTotal merged: {len(merged)}')

# Stats
sources = {}
for ch in merged:
    s = ch['source']
    sources[s] = sources.get(s, 0) + 1
print(f'Sources: {sources}')

countries = len(set(ch['country'] for ch in merged if ch['country']))
categories = sorted(set(ch['category'] for ch in merged))
print(f'Countries: {countries}')
print(f'Categories ({len(categories)}): {", ".join(categories)}')

# Save
out_path = os.path.join(BASE, 'tv_merged.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)

print(f'\nSaved to: {out_path}')
print(f'File size: {os.path.getsize(out_path) / 1024 / 1024:.1f} MB')
