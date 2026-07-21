import urllib.request
import re
from xml.sax.saxutils import escape

URL_CATEGORIA = "https://nextnovels.com/category/novela-ligera/"

def obtener_novelas():
    entradas = []
    try:
        req = urllib.request.Request(
            URL_CATEGORIA, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        patron_links = re.findall(r'href="(https://nextnovels.com/descargar-[^"]+)"', html)
        if not patron_links:
            return ""
            
        links_unicos = list(dict.fromkeys(patron_links))
        
        for loc in links_unicos[:10]:
            slug = loc.replace("https://nextnovels.com/descargar-", "").replace("/", "")
            titulo = slug.replace("-en-espanol", "").replace("-", " ").title()
            
            # Construimos la entrada en formato XML Atom (OPDS 1.2)
            entrada = f"""    <entry>
        <title>{escape(titulo)}</title>
        <id>{escape(loc)}</id>
        <updated>2026-01-01T00:00:00Z</updated>
        <link href="{escape(loc)}" type="text/html" rel="alternate"/>
        <link href="{escape(loc)}" type="application/epub+zip" rel="http://opds-spec.org/acquisition"/>
    </entry>"""
            entradas.append(entrada)
            
    except Exception as e:
        print(f"Error: {e}")
        
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
    
    # Guardamos como .xml en lugar de .json
    with open("catalogo.xml", "w", encoding="utf-8") as f:
        f.write(xml_contenido)
    print("¡Catálogo OPDS XML generado con éxito!")

if __name__ == "__main__":
    generar_opds()
