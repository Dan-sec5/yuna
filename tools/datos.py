import os
import pandas as pd

def leer_excel(ruta: str) -> str:
    """Lee un Excel y retorna resumen ejecutivo"""
    ruta = os.path.expanduser(ruta)
    try:
        xl = pd.ExcelFile(ruta)
        resumen = []
        resumen.append(f"📊 Archivo: {os.path.basename(ruta)}")
        resumen.append(f"📋 Hojas: {', '.join(xl.sheet_names)}")
        for hoja in xl.sheet_names:
            df = pd.read_excel(ruta, sheet_name=hoja)
            resumen.append(f"\n--- Hoja: {hoja} ---")
            resumen.append(f"Filas: {len(df)} | Columnas: {len(df.columns)}")
            resumen.append(f"Columnas: {', '.join(df.columns.astype(str).tolist())}")
            numericas = df.select_dtypes(include='number')
            if not numericas.empty:
                resumen.append("Resumen numérico:")
                for col in numericas.columns[:5]:
                    resumen.append(f"  {col}: min={numericas[col].min():.2f}, max={numericas[col].max():.2f}, promedio={numericas[col].mean():.2f}")
            nulos = df.isnull().sum().sum()
            if nulos > 0:
                resumen.append(f"⚠ Valores nulos: {nulos}")
        return "\n".join(resumen)
    except Exception as e:
        return f"Error leyendo Excel: {e}"

def leer_csv(ruta: str) -> str:
    """Lee un CSV y retorna resumen"""
    ruta = os.path.expanduser(ruta)
    try:
        df = pd.read_csv(ruta, encoding='utf-8', errors='ignore')
        resumen = []
        resumen.append(f"📊 Archivo: {os.path.basename(ruta)}")
        resumen.append(f"Filas: {len(df)} | Columnas: {len(df.columns)}")
        resumen.append(f"Columnas: {', '.join(df.columns.tolist())}")
        numericas = df.select_dtypes(include='number')
        if not numericas.empty:
            resumen.append("Resumen numérico:")
            for col in numericas.columns[:5]:
                resumen.append(f"  {col}: min={numericas[col].min():.2f}, max={numericas[col].max():.2f}")
        return "\n".join(resumen)
    except Exception as e:
        return f"Error leyendo CSV: {e}"

def leer_pdf(ruta: str) -> str:
    """Extrae texto de un PDF"""
    ruta = os.path.expanduser(ruta)
    try:
        import pdfplumber
        texto = []
        with pdfplumber.open(ruta) as pdf:
            texto.append(f"📄 PDF: {os.path.basename(ruta)} ({len(pdf.pages)} páginas)")
            for i, pagina in enumerate(pdf.pages[:5]):
                contenido = pagina.extract_text()
                if contenido:
                    texto.append(f"\n--- Página {i+1} ---")
                    texto.append(contenido[:500])
        return "\n".join(texto)
    except Exception as e:
        return f"Error leyendo PDF: {e}"

def comparar_excel(ruta1: str, ruta2: str, columna_clave: str = None) -> str:
    """Compara dos archivos Excel"""
    try:
        df1 = pd.read_excel(os.path.expanduser(ruta1))
        df2 = pd.read_excel(os.path.expanduser(ruta2))
        resumen = []
        resumen.append(f"Archivo 1: {len(df1)} filas")
        resumen.append(f"Archivo 2: {len(df2)} filas")
        resumen.append(f"Diferencia de filas: {len(df2) - len(df1)}")
        cols_comunes = set(df1.columns) & set(df2.columns)
        resumen.append(f"Columnas en común: {len(cols_comunes)}")
        return "\n".join(resumen)
    except Exception as e:
        return f"Error comparando: {e}"
