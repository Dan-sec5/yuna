from typing import Dict, List

ALL_SCHEMAS: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "buscar_archivos",
            "description": "Busca archivos por patrón glob en una carpeta",
            "parameters": {
                "type": "object",
                "properties": {
                    "patron": {"type": "string", "description": "Patrón glob, ej: *.xlsx"},
                    "carpeta": {"type": "string", "description": "Ruta base, ej: ~/Downloads"},
                },
                "required": ["patron"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "listar_recientes",
            "description": "Lista archivos modificados en los últimos N días",
            "parameters": {
                "type": "object",
                "properties": {
                    "carpeta": {"type": "string", "description": "Ruta a escanear"},
                    "dias": {"type": "integer", "description": "Días atrás, default 7"},
                },
                "required": ["carpeta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "organizar_archivos",
            "description": "Organiza archivos por tipo en subcarpetas",
            "parameters": {
                "type": "object",
                "properties": {
                    "carpeta_origen": {"type": "string", "description": "Carpeta a organizar"},
                },
                "required": ["carpeta_origen"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "leer_excel",
            "description": "Lee un Excel y retorna resumen ejecutivo",
            "parameters": {
                "type": "object",
                "properties": {
                    "ruta": {"type": "string", "description": "Ruta al archivo .xlsx"},
                },
                "required": ["ruta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "leer_csv",
            "description": "Lee un CSV y retorna resumen",
            "parameters": {
                "type": "object",
                "properties": {
                    "ruta": {"type": "string", "description": "Ruta al archivo .csv"},
                },
                "required": ["ruta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "leer_pdf",
            "description": "Extrae texto de un PDF (primeras 5 páginas)",
            "parameters": {
                "type": "object",
                "properties": {
                    "ruta": {"type": "string", "description": "Ruta al archivo .pdf"},
                },
                "required": ["ruta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "leer_texto",
            "description": "Lee un archivo de texto plano",
            "parameters": {
                "type": "object",
                "properties": {
                    "ruta": {"type": "string", "description": "Ruta al archivo"},
                },
                "required": ["ruta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_web",
            "description": "Busca en DuckDuckGo sin API key",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Términos de búsqueda"},
                    "max_resultados": {"type": "integer", "description": "Máximo resultados, default 3"},
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "precio_activo",
            "description": "Obtiene precio actual de un ticker financiero",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Símbolo, ej: AAPL, BTC-USD"},
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "noticias_financieras_mx",
            "description": "Busca noticias financieras de México",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_resultados": {"type": "integer", "description": "Máximo, default 3"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "info_sistema",
            "description": "Retorna info del sistema: fecha, disco, memoria",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notificar",
            "description": "Envía notificación nativa macOS",
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string"},
                    "mensaje": {"type": "string"},
                },
                "required": ["titulo", "mensaje"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crear_archivo",
            "description": "Crea un archivo con contenido",
            "parameters": {
                "type": "object",
                "properties": {
                    "ruta": {"type": "string", "description": "Ruta destino"},
                    "contenido": {"type": "string", "description": "Texto a escribir"},
                },
                "required": ["ruta", "contenido"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_memoria",
            "description": "Consulta la base de datos de memoria (preferencias, episódica)",
            "parameters": {
                "type": "object",
                "properties": {
                    "tabla": {"type": "string", "enum": ["preferencias", "episodic"], "description": "Tabla a consultar"},
                    "clave": {"type": "string", "description": "Clave opcional para filtrar"},
                },
                "required": ["tabla"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escribir_memoria",
            "description": "Guarda un valor en memoria a largo plazo",
            "parameters": {
                "type": "object",
                "properties": {
                    "clave": {"type": "string"},
                    "valor": {"type": "string"},
                },
                "required": ["clave", "valor"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ejecutar_bash_seguro",
            "description": "Ejecuta comando bash de lista blanca (ls, cat, echo, pwd, head, tail, grep, find, wc)",
            "parameters": {
                "type": "object",
                "properties": {
                    "comando": {"type": "string", "description": "Comando permitido"},
                },
                "required": ["comando"]
            }
        }
    },
]

def get_schema(name: str) -> Dict:
    for s in ALL_SCHEMAS:
        if s["function"]["name"] == name:
            return s["function"]
    return {}
