Python
import json
import urllib.request
import re

URL_CATEGORIA = "https://nextnovels.com/category/novela-ligera/"

def extraer_enlace_descarga(url_pagina):
    """Entra a la página de la novela y busca el enlace real de descarga (Mega, MediaFire, etc.)"""
    try:
        req = urllib.request.Request(
            url_pagina, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        # Busca enlaces externos comunes de descarga o archivos .epub dentro de la página
        # Excluimos los enlaces propios de la web para buscar el servidor de descarga final
        matches = re.findall(r'href="(https?://[^"]+)"', html)
        for link in matches:
            if any(domain in link for domain in ['mega.nz', 'mediafire.com', 'drive.google.com', '.epub', 'zippyshare', 'pixeldrain']):
                return link
                
    except Exception:
        pass
        
    # Si no encuentra un enlace externo claro, devuelve la propia página como fallback
    return url_pagina

def obtener_novelas():
    publications = []
    
    try:
        req = urllib.request.Request(
            URL_CATEGORIA, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode('utf-8')
            
        patron_links = re.findall(r'href="(https://nextnovels.com/descargar-[^"]+)"', html_content)
        
        if not patron_links:
            return []
            
        links_unicos = list(dict.fromkeys(patron_links))
        
        # Limitamos a las primeras 5 novelas para que el script corra rápido en GitHub Actions
        for loc in links_unicos[:5]:
            slug = loc.replace("https://nextnovels.com/descargar-", "").replace("/", "")
            titulo = slug.replace("-en-espanol", "").replace("-", " ").title()
            
            # Buscamos el enlace real de descarga
            enlace_real = extraer_enlace_descarga(loc)
            
            pub = {
                "metadata": {
                    "title": titulo,
                    "numberOfItems": 1
                },
                "links": [
                    {
                        "rel": "alternate",
                        "type": "text/html",
                        "href": loc
                    }
                ],
                "readingOrder": [
                    {
                        "type": "application/epub+zip",
                        "href": enlace_real,
                        "title": "Descargar EPUB"
                    }
                ]
            }
            publications.append(pub)
                
    except Exception as e:
        print(f"Error: {e}")
        
    return publications

def generar_opds():
    novelas = obtener_novelas()
    
    catalogo = {
        "metadata": {
            "title": "Next Novels - OPDS Catalog",
            "conformsTo": "https://opds-spec.org/opds-2.0"
        },
        "publications": novelas if novelas else []
    }
    
    with open("catalogo.json", "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=4)
    print("¡Catálogo OPDS generado con éxito!")

if __name__ == "__main__":
    generar_opds()
                
    except Exception as e:
        print(f"Error al conectar con la web: {e}")
        
    return publications

def generar_opds():
    catalogo = {
        "metadata": {
            "title": "Next Novels - OPDS Catalog",
            "conformsTo": "https://opds-spec.org/opds-2.0"
        },
        "publications": obtener_novelas()
    }
    
    with open("catalogo.json", "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=4)
    print("¡Catálogo OPDS generado con éxito!")

if __name__ == "__main__":
    generar_opds()
