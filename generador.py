import urllib.request
import re
from html.parser import HTMLParser
from xml.sax.saxutils import escape

URL_INDICE_VISUAL = "https://nextnovels.com/indice-visual-oriente/"

class IndexParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.novelas = []
        self.current_link = None
        self.current_img = None
        self.current_alt = None
        self.capture_text = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'a':
            href = attrs_dict.get('href', '')
            if 'nextnovels.com' in href and ('descargar-' in href or 'novela' in href):
                self.current_link = href
        elif tag == 'img':
            # Capturamos src o data-src (lazy loading)
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

def obtener_novelas_desde_indice():
    entradas = []
    links_procesados = set()
    
    try:
        req = urllib.request.Request(
            URL_INDICE_VISUAL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        parser = IndexParser()
        parser.feed(html)
        
        for item in parser.novelas:
            loc = item['link']
            if loc in links_procesados or "indice-visual" in loc or "category" in loc:
                continue
            
            links_procesados.add(loc)
            
            titulo = item['alt'] if item['alt'] else loc.split("/")[-2].replace("-", " ").title()
            imagen_portada = item['img']
            
            # Limpiar sufijos de tamaño de WordPress para obtener la imagen original limpia
            if imagen_portada:
                imagen_portada = re.sub(r'-\d+x\d+(?=\.\w+$)', '', imagen_portada)

            enlace_descarga, tipo_mime, descripcion = extraer_detalles_internos(loc)
            
            tag_imagen = f'<link href="{escape(imagen_portada)}" type="image/jpeg" rel="http://opds-spec.org/image"/>' if imagen_portada else ''
            tag_thumb = f'<link href="{escape(imagen_portada)}" type="image/jpeg" rel="http://opds-spec.org/thumbnail"/>' if imagen_portada else ''
            tag_summary = f'<summary type="text">{escape(descripcion)}</summary>' if descripcion else '<summary type="text">Novela ligera disponible en Next Novels.</summary>'
            
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
        print(f"Error procesando el índice visual: {e}")
            
    return "\n".join(entradas)

def extraer_detalles_internos(url_articulo):
    enlace_descarga = url_articulo
    tipo_mime = "text/html"
    descripcion = ""
    
    try:
        req = urllib.request.Request(
            url_articulo, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        match_desc = re.search(r'<meta name="description" content="([^"]+)"', html)
        if match_desc:
            descripcion = match_desc.group(1)

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
        
    return enlace_descarga, tipo_mime, descripcion

def generar_opds():
    items = obtener_novelas_desde_indice()
    
    xml_contenido = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opds="http://opds-spec.org/2010/catalog">
    <title>Next Novels - Índice Visual OPDS</title>
    <id>urn:uuid:next-novels-visual-opds</id>
    <updated>2026-01-01T00:00:00Z</updated>
    <author>
        <name>Deiviz25</name>
    </author>
{items}
</feed>"""
    
    with open("catalogo.xml", "w", encoding="utf-8") as f:
        f.write(xml_contenido)
    print("¡Catálogo visual OPDS generado con éxito con HTMLParser!")

if __name__ == "__main__":
    generar_opds()
