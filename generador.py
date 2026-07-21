import urllib.request
import re
from xml.sax.saxutils import escape

URL_CATEGORIA = "https://nextnovels.com/category/novela-ligera/page/"

def extraer_detalles_articulo(url_articulo):
    """Extrae el enlace de descarga, la imagen de portada y la sinopsis desde la página del artículo."""
    enlace_descarga = url_articulo
    tipo_mime = "text/html"
    imagen_portada = ""
    descripcion = ""
    
    try:
        req = urllib.request.Request(
            url_articulo, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        # 1. Extraer imagen de portada (OpenGraph image)
        match_img = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if match_img:
            imagen_portada = match_img.group(1)
            
        # 2. Extraer descripción / sinopsis
        match_desc = re.search(r'<meta name="description" content="([^"]+)"', html)
        if match_desc:
            descripcion = match_desc.group(1)

        # 3. Buscar dominios de descarga externos habituales
        dominios_validos = (
            'mega.nz', 'mediafire.com', 'drive.google.com',
            'terabox.com', '1024terabox.com', 'mirrobox.com', 'nephobox.com'
        )

        matches = re.findall(r'href="(https?://[^"]+)"', html)
        for link in matches:
            if '.epub' in link.lower() and 'nextnovels.com' not in link:
                enlace_descarga = link
                tipo_mime = "application/epub+zip"
                break
        
        if tipo_mime == "text/html":
            for link in matches:
                if any(d in link.lower() for d in dominios_validos):
                    enlace_descarga = link
                    break
                    
    except Exception:
        pass
    
    return enlace_descarga, tipo_mime, imagen_portada, descripcion

def obtener_novelas():
    entradas = []
    links_procesados = set()
    
    # Recorremos las primeras 3 páginas de la categoría
    for num_pagina in range(1, 4):
        url_pag = f"{URL_CATEGORIA}{num_pagina}/" if num_pagina > 1 else "https://nextnovels.com/category/novela-ligera/"
        try:
            req = urllib.request.Request(
                url_pag, 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                
            patron_links = re.findall(r'href="(https://nextnovels.com/descargar-[^"]+)"', html)
            
            for loc in patron_links:
                if loc not in links_procesados:
                    links_procesados.add(loc)
                    slug = loc.replace("https://nextnovels.com/descargar-", "").replace("/", "")
                    titulo = slug.replace("-en-espanol", "").replace("-", " ").title()
                    
                    # Obtenemos todos los metadatos ricos
                    enlace_descarga, tipo_mime, imagen_portada, descripcion = extraer_detalles_articulo(loc)
                    
                    # Construimos las etiquetas opcionales si existen
                    tag_imagen = f'<link href="{escape(imagen_portada)}" type="image/jpeg" rel="http://opds-spec.org/image"/>' if imagen_portada else ''
                    tag_thumb = f'<link href="{escape(imagen_portada)}" type="image/jpeg" rel="http://opds-spec.org/thumbnail"/>' if imagen_portada else ''
                    tag_summary = f'<summary type="text">{escape(descripcion)}</summary>' if descripcion else ''
                    
                    entrada = f"""    <entry>
        <title>{escape(titulo)}</title>
        <id>{escape(loc)}</id>
        <updated>2026-01-01T00:00:00Z</updated>
        {tag_summary}
        <link href="{escape(loc)}" type="text/html" rel="alternate"/>
        <link href="{escape(enlace_descarga)}" type="{tipo_mime}" rel="http://opds-spec.org/acquisition"/>
        {tag_imagen}
        {tag_thumb}
    </entry>"""
                    entradas.append(entrada)
        except Exception as e:
            print(f"Error en página {num_pagina}: {e}")
            
    return "\n".join(entradas)

def generar_opds():
    items = obtener_novelas()
    
    xml_contenido = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opds="http://opds-spec.org/2010/catalog">
    <title>Next Novels - OPDS Catalog</title>
    <id>urn:uuid:next-novels-opds</id>
    <updated>2026-01-01T00:00:00Z</updated>
    <author>
        <name>Deiviz25</name>
    </author>
{items}
</feed>"""
    
    with open("catalogo.xml", "w", encoding="utf-8") as f:
        f.write(xml_contenido)
    print("¡Catálogo OPDS enriquecido generado con éxito!")

if __name__ == "__main__":
    generar_opds()
