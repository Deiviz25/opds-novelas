import json
import urllib.request
import re

# URL directa de la categoría de novelas ligeras en Next Novels
URL_CATEGORIA = "https://nextnovels.com/category/novela-ligera/"

def obtener_novelas():
    publications = []
    
    try:
        # Petición HTTP simulando un navegador real
        req = urllib.request.Request(
            URL_CATEGORIA, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode('utf-8')
            
        # Buscamos enlaces de artículos de descarga usando expresiones regulares en el HTML
        # Esto captura los links que van a /descargar-.../
        patron_links = re.findall(r'href="(https://nextnovels.com/descargar-[^"]+)"', html_content)
        
        # Eliminamos duplicados manteniendo el orden
        links_unicos = list(dict.fromkeys(patron_links))
        
        for loc in links_unicos:
            # Limpiamos el título a partir de la URL de forma legible
            slug = loc.replace("https://nextnovels.com/descargar-", "").replace("/", "")
            titulo = slug.replace("-en-espanol", "").replace("-", " ").title()
            
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
                        "href": loc,
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
    
    with open("catalogo.json", "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=4)
    print("¡Catálogo OPDS generado con éxito!")

if __name__ == "__main__":
    generar_opds()
