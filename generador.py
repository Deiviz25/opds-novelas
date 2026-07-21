import json
import urllib.request
import re

URL_CATEGORIA = "https://nextnovels.com/category/novela-ligera/"

def obtener_novelas():
    publications = []
    try:
        req = urllib.request.Request(
            URL_CATEGORIA, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        patron_links = re.findall(r'href="(https://nextnovels.com/descargar-[^"]+)"', html)
        if not patron_links:
            return []
            
        links_unicos = list(dict.fromkeys(patron_links))
        
        for loc in links_unicos[:5]:
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
        print(f"Error: {e}")
        
    return publications

def generar_opds():
    novelas = obtener_novelas()
    catalogo = {
        "metadata": {
            "title": "Next Novels - OPDS Catalog",
            "conformsTo": "https://opds-spec.org/opds-2.0"
        },
        "publications": novelas
    }
    
    with open("catalogo.json", "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=4)
    print("¡Catálogo OPDS generado con éxito!")

if __name__ == "__main__":
    generar_opds()
