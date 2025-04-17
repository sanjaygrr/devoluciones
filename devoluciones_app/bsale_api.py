import requests
import time
from django.conf import settings

class BsaleAPI:
    """Clase para interactuar con la API de Bsale."""
    
    def __init__(self):
        self.api_token = settings.BSALE_API_TOKEN
        self.base_url = settings.BSALE_BASE_URL
        self.headers = {
            "access_token": self.api_token,
            "Content-Type": "application/json"
        }
        
        # Configuración para optimizar rendimiento
        self.sleep_time = 0.1
        self.timeout = 15
        
        # Campos para expansión
        self.expand_fields = [
            "document_type", "client", "office", "details", 
            "sellers", "references"
        ]
    
    def fetch_api_data(self, endpoint, params=None, expand=False, retry=3):
        """Obtener datos de la API de Bsale con reintentos."""
        url = f"{self.base_url}/{endpoint}"
        
        # Añadir expansión si se solicita
        if expand and params is None:
            params = {}
        if expand:
            params['expand'] = f"[{','.join(self.expand_fields)}]"
        
        # Pausa para respetar límites de API
        time.sleep(self.sleep_time)
        
        for intento in range(retry + 1):
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate Limit
                    time.sleep(2 ** intento)  # Backoff exponencial
                    continue
                else:
                    if intento < retry:
                        time.sleep(1)
                        continue
                    return None
            except Exception:
                if intento < retry:
                    time.sleep(1)
                    continue
                return None
        
        return None
    
    def buscar_por_numero_boleta(self, numero_boleta):
        """Buscar documentos por número de boleta."""
        params = {
            "number": numero_boleta
        }
        
        return self.fetch_api_data("documents.json", params, expand=True)
    
    def procesar_documento(self, doc):
        """Extrae información relevante de un documento."""
        if not doc:
            return None
            
        numero_boleta = doc.get("number", "")
        
        # Información del cliente
        cliente = ""
        if "client" in doc and isinstance(doc["client"], dict):
            cliente_info = doc["client"]
            cliente = cliente_info.get("company", "") or f"{cliente_info.get('firstName', '')} {cliente_info.get('lastName', '')}".strip()
        
        # Procesar detalles de productos
        productos = []
        if "details" in doc and "items" in doc.get("details", {}):
            for item in doc["details"]["items"]:
                variant_info = item.get("variant", {})
                producto = {
                    "id": item.get("id", ""),
                    "codigo": variant_info.get("code", ""),
                    "descripcion": variant_info.get("description", ""),
                    "cantidad": item.get("quantity", 0),
                    "precio_unitario": item.get("totalUnitValue", 0),
                    "total": item.get("totalAmount", 0),
                }
                productos.append(producto)
        
        # Resultado final
        return {
            "numero_boleta": numero_boleta,
            "cliente": cliente,
            "productos": productos
        }