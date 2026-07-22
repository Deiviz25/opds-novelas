from datetime import datetime, timezone
UPDATED = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
import urllib.request
import urllib.error
import re
import time
from html.parser import HTMLParser
from xml.sax.saxutils import escape

try:
    import cloudscraper
    _SCRAPER = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
except ImportError:
    _SCRAPER = None

URL_INDICE_VISUAL = "https://nextnovels.com/indice-visual-oriente/"
URL_CATEGORIA_BASE = "https://nextnovels.com/category/novela-ligera/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Referer': 'https://nextnovels.com/',
}

MAX_PAGINAS = 200
# Nº de novelas por página del feed. Se sube bastante (por encima del total
# actual de ~670) para que todo el catálogo quepa en catalogo.xml y el
# lector OPDS no obligue a ir pasando página a página. Si el catálogo crece
# mucho más allá de esto, el script seguirá funcionando: simplemente
# empezará a crear catalogo-2.xml, catalogo-3.xml, etc. automáticamente.
NOVELAS_POR_PAGINA_FEED = 2000


class IndexParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.novelas = []
        self.current_link = None
        self.current_img = None
        self.current_alt = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'a':
            href = attrs_dict.get('href', '')
            if 'nextnovels.com' in href and ('descargar-' in href or 'novela' in href):
                self.current_link = href
        elif tag == 'img':
            img_src = attrs_dict.get('data-src') or attrs_dict.get('src', '')
            alt = attrs_dict.get('alt', '')
            if img_src and 'wp-content/uploads' in img_src:
                self.current_img = img_src
                self.current_alt = alt
                
                if self.current_link and self.current_img:
                    self.novelas.append({
                        'link': self.current_link,
                        'img': self.current_img,
                        'alt': self.current_alt
                    })


def _descargar_html(url, reintentos=2):
    """Descarga HTML con manejo de errores. Usa cloudscraper si está disponible
    (para evitar bloqueos anti-bot tipo Cloudflare/Wordfence en runners de CI),
    con urllib como respaldo."""
    ultimo_error = None
    for intento in range(reintentos + 1):
        try:
            if _SCRAPER is not None:
                resp = _SCRAPER.get(url, headers=HEADERS, timeout=20)
                status = resp.status_code
                html = resp.text
            else:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=20) as response:
                    status = response.status
                    html = response.read().decode('utf-8', errors='ignore')

            if status != 200:
                raise RuntimeError(f"HTTP {status}")

            # Diagnóstico: si la página no parece la real (p.ej. un challenge
            # anti-bot), avisar en el log en vez de fallar en silencio.
            if 'nextnovels' not in html.lower() and 'novela' not in html.lower():
                print(f"Aviso: respuesta sospechosa de {url} (¿bloqueo anti-bot?). "
                      f"Primeros 200 caracteres: {html[:200]!r}")

            return html
        except Exception as e:
            ultimo_error = e
            if intento < reintentos:
                time.sleep(3 * (intento + 1))

    print(f"Error descargando {url}: {ultimo_error}")
    return None


def obtener_novelas_desde_indice():
    """Obtiene novelas del índice visual con portadas bonitas"""
    novelas_dict = {}
    
    html = _descargar_html(URL_INDICE_VISUAL)
    if not html:
        return novelas_dict

    parser = IndexParser()
    parser.feed(html)
    
    for item in parser.novelas:
        loc = item['link']
        if "indice-visual" in loc or "category" in loc:
            continue
        
        novelas_dict[loc] = {
            'titulo': item['alt'] if item['alt'] else loc.split("/")[-2].replace("-", " ").title(),
            'img': re.sub(r'-\d+x\d+(?=\.\w+$)', '', item['img']) if item['img'] else None,
            'desde_indice': True
        }
    
    print(f"Índice visual: {len(novelas_dict)} novelas encontradas")
    return novelas_dict


def obtener_novelas_desde_categoria():
    """Recorre TODAS las páginas de la categoría para completar el catálogo"""
    novelas_dict = {}
    
    for num_pagina in range(1, MAX_PAGINAS + 1):
        url_pag = URL_CATEGORIA_BASE if num_pagina == 1 else f"{URL_CATEGORIA_BASE}page/{num_pagina}/"
        
        html = _descargar_html(url_pag)
        if not html:
            break
        
        encontrados = re.findall(r'href="(https://nextnovels\.com/descargar-[^"]+)"', html)
        if not encontrados:
            # No hay más novelas, fin del catálogo
            break
        
        for loc in encontrados:
            if loc not in novelas_dict:
                slug = loc.replace("https://nextnovels.com/descargar-", "").replace("/", "")
                novelas_dict[loc] = {
                    'titulo': slug.replace("-en-espanol", "").replace("-", " ").title(),
                    'img': None,
                    'desde_indice': False
                }
        
        print(f"Categoría pág. {num_pagina}: {len(encontrados)} links encontrados")
        time.sleep(1)
    
    return novelas_dict


def extraer_detalles_internos(url_articulo):
    """Extrae enlace de descarga, tipo MIME y descripción"""
    enlace_descarga = url_articulo
    tipo_mime = "text/html"
    descripcion = ""
    
    html = _descargar_html(url_articulo)
    if not html:
        return enlace_descarga, tipo_mime, descripcion
    
    match_desc = re.search(r'<meta name="description" content="([^"]+)"', html)
    if match_desc:
        descripcion = match_desc.group(1)[:200]  # Limitar longitud

    dominios_validos = (
        'mega.nz', 'mediafire.com', 'drive.google.com',
        'terabox.com', '1024terabox.com', 'mirrobox.com', 'nephobox.com'
    )

    matches = re.findall(r'href="(https?://[^"]+)"', html)
    for link in matches:
        if '.epub' in link.lower() and 'nextnovels.com' not in link:
            enlace_descarga = link
            tipo_mime = "application/epub+zip"
            return enlace_descarga, tipo_mime, descripcion
    
    for link in matches:
        if any(d in link.lower() for d in dominios_validos):
            enlace_descarga = link
            break
    
    return enlace_descarga, tipo_mime, descripcion


def construir_entrada(loc, titulo, img=None):
    """Construye una entrada XML OPDS"""
    enlace_descarga, tipo_mime, descripcion = extraer_detalles_internos(loc)
    
    tag_imagen = f'<link href="{escape(img)}" type="image/jpeg" rel="http://opds-spec.org/image"/>' if img else ''
    tag_thumb = f'<link href="{escape(img)}" type="image/jpeg" rel="http://opds-spec.org/image/thumbnail"/>' if img else ''
    tag_summary = f'<summary type="text">{escape(descripcion)}</summary>' if descripcion else '<summary type="text">Novela ligera disponible en Next Novels.</summary>'
    
    return f"""    <entry>
        <title>{escape(titulo)}</title>
        <id>{escape(loc)}</id>
        <updated>{UPDATED}</updated>
        {tag_summary}
        <link href="{escape(loc)}" type="text/html" rel="alternate"/>
        <link href="{escape(enlace_descarga)}" type="{tipo_mime}" rel="http://opds-spec.org/acquisition"/>
        {tag_imagen}
        {tag_thumb}
    </entry>"""


def generar_feed_pagina(entradas_xml, num_pagina, total_paginas):
    """Genera un archivo XML OPDS para una página"""
    nombre_archivo = "catalogo.xml" if num_pagina == 1 else f"catalogo-{num_pagina}.xml"
    
    links_nav = []
    if num_pagina > 1:
        anterior = "catalogo.xml" if num_pagina == 2 else f"catalogo-{num_pagina - 1}.xml"
        links_nav.append(f'    <link rel="previous" href="{anterior}" type="application/atom+xml;profile=opds-catalog"/>')
    if num_pagina < total_paginas:
        siguiente = f"catalogo-{num_pagina + 1}.xml"
        links_nav.append(f'    <link rel="next" href="{siguiente}" type="application/atom+xml;profile=opds-catalog"/>')

    xml_contenido = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opds="http://opds-spec.org/2010/catalog">
    <title>Next Novels - OPDS Catalog (pág. {num_pagina}/{total_paginas})</title>
    <id>urn:uuid:next-novels-opds-{num_pagina}</id>
    <updated>{UPDATED}</updated>
    <author>
        <name>Deiviz25</name>
    </author>
    <link rel="self" href="{nombre_archivo}" type="application/atom+xml;profile=opds-catalog"/>
    <link rel="start" href="catalogo.xml" type="application/atom+xml;profile=opds-catalog"/>
{chr(10).join(links_nav)}
{chr(10).join(entradas_xml)}
</feed>"""

    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(xml_contenido)
    
    print(f"Generado {nombre_archivo}")


def _listar_paginas_existentes():
    """Devuelve los números de página de los catalogo*.xml presentes en el directorio actual"""
    import os
    numeros = set()
    for nombre in os.listdir('.'):
        if nombre == 'catalogo.xml':
            numeros.add(1)
        else:
            m = re.match(r'^catalogo-(\d+)\.xml$', nombre)
            if m:
                numeros.add(int(m.group(1)))
    return numeros


UMBRAL_MINIMO_NOVELAS = 50  # por debajo de esto, probablemente hubo un bloqueo/scrape fallido


def generar_opds():
    print("Extrayendo novelas del índice visual...")
    novelas = obtener_novelas_desde_indice()
    
    print("Extrayendo novelas de la categoría (todas las páginas)...")
    novelas_cat = obtener_novelas_desde_categoria()
    
    # Fusionar: las del índice visual tienen prioridad (tienen portadas)
    novelas.update(novelas_cat)
    
    print(f"Total de novelas únicas: {len(novelas)}")

    if len(novelas) < UMBRAL_MINIMO_NOVELAS:
        print(f"ABORTANDO: solo se encontraron {len(novelas)} novelas (mínimo esperado "
              f"{UMBRAL_MINIMO_NOVELAS}). Esto suele indicar un bloqueo anti-bot o un "
              f"cambio en la web, no que el catálogo real se haya reducido. No se "
              f"sobrescribe el catálogo existente.")
        return
    
    print("Procesando novelas...")
    todas_las_entradas = []
    for i, (loc, info) in enumerate(novelas.items(), 1):
        try:
            entrada = construir_entrada(loc, info['titulo'], info.get('img'))
            todas_las_entradas.append(entrada)
        except Exception as e:
            print(f"Error procesando {loc}: {e}")
        
        if i % 20 == 0:
            print(f"  {i}/{len(novelas)}...")
    
    # Dividir en páginas
    bloques = [
        todas_las_entradas[i:i + NOVELAS_POR_PAGINA_FEED]
        for i in range(0, len(todas_las_entradas), NOVELAS_POR_PAGINA_FEED)
    ] or [[]]
    
    print(f"Generando {len(bloques)} página(s) del feed...")
    for idx, bloque in enumerate(bloques, 1):
        generar_feed_pagina(bloque, idx, len(bloques))

    # Limpiar páginas de una ejecución anterior que ya no hacen falta
    import os
    paginas_actuales = set(range(1, len(bloques) + 1))
    for num in _listar_paginas_existentes() - paginas_actuales:
        nombre = "catalogo.xml" if num == 1 else f"catalogo-{num}.xml"
        os.remove(nombre)
        print(f"Eliminado {nombre} (ya no hace falta)")
    
    print(f"¡Catálogo OPDS generado con éxito! {len(bloques)} páginas, {len(todas_las_entradas)} novelas.")


if __name__ == "__main__":
    generar_opds()
