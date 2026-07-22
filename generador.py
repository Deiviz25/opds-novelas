import urllib.request
import re
from xml.sax.saxutils import escape

URL_CATEGORIA = "https://nextnovels.com/category/novela-ligera/page/"

def extraer_enlace_epub(url_articulo):
    """Entra a la página de la novela para buscar el enlace de descarga real del archivo EPUB."""
    try:
        req = urllib.request.Request(
            url_articulo, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        # Dominios de descarga habituales usados por nextnovels.com
        dominios_validos = (
            '.epub', 'mega.nz', 'mediafire.com', 'drive.google.com',
            'terabox.com', '1024terabox.com', 'mirrobox.com', 'nephobox.com'
        )

        # Busca específicamente dentro de los botones "Descargar" (evita coger
        # enlaces de "Ver"/"Leer" que apuntan a Crunchyroll, YupManga, etc.)
        botones = re.findall(
            r'<a[^>]+class="[^"]*et_pb_button[^"]*"[^>]+href="(https?://[^"]+)"[^>]*>\s*Descargar\s*</a>',
            html
        )
        for link in botones:
            if any(d in link.lower() for d in dominios_validos):
                return link

        # Respaldo: busca en todo el HTML por si el botón no coincide con el patrón anterior
        matches = re.findall(r'href="(https?://[^"]+)"', html)
        for link in matches:
            if any(d in link.lower() for d in dominios_validos):
                return link
    except Exception:
        pass
    
    # Si no encuentra un enlace externo, devuelve el enlace del artículo como respaldo
    return url_articulo

def obtener_novelas():
    entradas = []
    links_procesados = set()
    
    # Recorremos las primeras 3 páginas de la categoría para no coger solo la portada
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
                    
                    # Obtenemos el enlace de descarga real
                    enlace_descarga = extraer_enlace_epub(loc)
                    
                    entrada = f"""    <entry>
        <title>{escape(titulo)}</title>
        <id>{escape(loc)}</id>
        <updated>2026-01-01T00:00:00Z</updated>
        <link href="{escape(loc)}" type="text/html" rel="alternate"/>
        <link href="{escape(enlace_descarga)}" type="application/epub+zip" rel="http://opds-spec.org/acquisition"/>
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
    print("¡Catálogo OPDS XML ampliado generado con éxito!")

if __name__ == "__main__":
    generar_opds()
