import urllib.request
import re
from xml.sax.saxutils import escape

URL_CATEGORIA = "https://nextnovels.com/category/novela-ligera/page/"

def clasificar_enlace(url_articulo):
    """Busca el enlace de descarga y determina si es un archivo epub directo o un servicio web externo."""
    try:
        req = urllib.request.Request(
            url_articulo, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        dominios_validos = (
            'mega.nz', 'mediafire.com', 'drive.google.com',
            'terabox.com', '1024terabox.com', 'mirrobox.com', 'nephobox.com'
        )

        # 1. Buscar si hay un enlace directo que termine estrictamente en .epub
        matches = re.findall(r'href="(https?://[^"]+)"', html)
        for link in matches:
            if '.epub' in link.lower() and 'nextnovels.com' not in link:
                return link, "application/epub+zip"

        # 2. Buscar botones de descarga con servicios externos (Terabox, Mega, etc.)
        botones = re.findall(
            r'<a[^>]+class="[^"]*et_pb_button[^"]*"[^>]+href="(https?://[^"]+)"[^>]*>\s*Descargar\s*</a>',
            html
        )
        for link in botones:
            if any(d in link.lower() for d in dominios_validos):
                # Como Terabox/Mega no es un archivo directo, lo marcamos como text/html 
                # para que OpenComic lo abra en el navegador en lugar de intentar descargarlo y fallar.
                return link, "text/html"

        # 3. Respaldo general buscando dominios en todo el HTML
        for link in matches:
            if any(d in link.lower() for d in dominios_validos):
                return link, "text/html"
                
    except Exception:
        pass
    
    # Si todo falla, devolvemos el artículo web original como text/html de seguridad
    return url_articulo, "text/html"

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
                    
                    # Obtenemos el enlace clasificado y su tipo MIME correcto
                    enlace_descarga, tipo_mime = clasificar_enlace(loc)
                    
                    entrada = f"""    <entry>
        <title>{escape(titulo)}</title>
        <id>{escape(loc)}</id>
        <updated>2026-01-01T00:00:00Z</updated>
        <link href="{escape(loc)}" type="text/html" rel="alternate"/>
        <link href="{escape(enlace_descarga)}" type="{tipo_mime}" rel="http://opds-spec.org/acquisition"/>
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
    print("¡Catálogo OPDS honesto generado con éxito!")

if __name__ == "__main__":
    generar_opds()
