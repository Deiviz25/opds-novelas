import urllib.request
import urllib.error
import re
from html.parser import HTMLParser
from xml.sax.saxutils import escape

URL_INDICE_VISUAL = "https://nextnovels.com/indice-visual-oriente/"
URL_CATEGORIA_BASE = "https://nextnovels.com/category/novela-ligera/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

MAX_PAGINAS = 200
NOVELAS_POR_PAGINA_FEED = 30


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


def _descargar_html(url):
    """Descarga HTML con manejo de errores"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error descargando {url}: {e}")
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
        <updated>2026-01-01T00:00:00Z</updated>
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
    <updated>2026-01-01T00:00:00Z</updated>
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


def generar_opds():
    print("Extrayendo novelas del índice visual...")
    novelas = obtener_novelas_desde_indice()
    
    print("Extrayendo novelas de la categoría (todas las páginas)...")
    novelas_cat = obtener_novelas_desde_categoria()
    
    # Fusionar: las del índice visual tienen prioridad (tienen portadas)
    novelas.update(novelas_cat)
    
    print(f"Total de novelas únicas: {len(novelas)}")
    
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
    
    print(f"¡Catálogo OPDS generado con éxito! {len(bloques)} páginas, {len(todas_las_entradas)} novelas.")


if __name__ == "__main__":
    generar_opds()
