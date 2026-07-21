import json
import urllib.request
import xml.etree.ElementTree as ET

# URL del sitemap de WordPress de la web para obtener las entradas de forma limpia
SITEMAP_URL = "https://nextnovels.com/post-sitemap.xml"

def obtener_novelas():
    publications = []
    
    try:
        # Descargar el sitemap de la web
        req = urllib.request.Request(
            SITEMAP_URL, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        # El sitemap usa namespaces de XML de Google
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        # Recorrer las URLs del sitemap (limitamos a las últimas 20 para la prueba inicial)
        for url in root.findall('ns:url', namespace):
            loc = url.find('ns:loc', namespace).text
            
            # Filtramos solo las páginas de descarga de novelas
            if loc and "descargar-" in loc:
                # Generamos un título limpio basado en la URL
                titulo_slug = loc.split("descargar-")[1].replace("-en-espanol/", "").replace("-", " ").title()
                
                pub = {
                    "metadata": {
                        "title": titulo_slug,
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
                            "href": loc,  # Enlace a la ficha o descarga directa
                            "title": "Ver / Descargar Novela"
                        }
                    ]
                }
                publications.append(pub)
                
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
    
    # Guardar el resultado en un archivo JSON estándar para OPDS 2.0
    with open("catalogo.json", "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=4)
    print("¡Catálogo OPDS generado con éxito!")

if __name__ == "__main__":
    generar_opds()
