import requests
import time
import json
from django.conf import settings
import logging

# Configurar logger
logger = logging.getLogger(__name__)

class BsaleAPI:
    """Clase para interactuar con la API de Bsale."""
    
    def __init__(self):
        self.api_token = settings.BSALE_API_TOKEN
        self.base_url = settings.BSALE_BASE_URL
        self.headers = {
            "access_token": self.api_token,
            "Content-Type": "application/json"
        }
        
        # Configuración para optimizar rendimiento - valores más altos para Heroku
        self.sleep_time = 0.2  # Aumentado para dar más tiempo entre solicitudes
        self.timeout = 30      # Timeout más largo para entornos de producción
        self.max_retries = 5   # Más reintentos
        
        # Campos para expansión
        self.expand_fields = [
            "document_type", "client", "office", "details", 
            "sellers", "references"
        ]
        
        # Log de inicialización
        logger.info(f"BsaleAPI inicializada. Base URL: {self.base_url}")
        if not self.api_token:
            logger.error("API Token no configurado")
    
    def fetch_api_data(self, endpoint, params=None, expand=False, retry=None):
        """Obtener datos de la API de Bsale con reintentos."""
        if retry is None:
            retry = self.max_retries
            
        url = f"{self.base_url}/{endpoint}"
        
        # Añadir expansión si se solicita
        if expand and params is None:
            params = {}
        if expand:
            params['expand'] = f"[{','.join(self.expand_fields)}]"
        
        # Log de la solicitud
        logger.info(f"Solicitando: {url}")
        logger.info(f"Parámetros: {json.dumps(params) if params else 'Ninguno'}")
        
        # Pausa para respetar límites de API
        time.sleep(self.sleep_time)
        
        for intento in range(retry + 1):
            try:
                logger.info(f"Intento {intento + 1} de {retry + 1}")
                response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
                
                logger.info(f"Código de respuesta: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        logger.error(f"Error decodificando JSON: {response.text[:200]}")
                        return None
                        
                elif response.status_code == 401:
                    logger.error("Error de autenticación: token inválido")
                    return None
                    
                elif response.status_code == 429:  # Rate Limit
                    logger.warning(f"Rate limit alcanzado. Esperando antes de reintentar.")
                    time.sleep(2 ** intento + 1)  # Backoff exponencial
                    continue
                    
                else:
                    logger.error(f"Error de API: {response.status_code}, Respuesta: {response.text[:200]}")
                    if intento < retry:
                        time.sleep(1 + intento)
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout en solicitud a API. Intento {intento + 1}")
                if intento < retry:
                    time.sleep(1 + intento)
                    continue
                return None
                
            except requests.exceptions.ConnectionError:
                logger.error(f"Error de conexión. Intento {intento + 1}")
                if intento < retry:
                    time.sleep(2 + intento)
                    continue
                return None
                
            except Exception as e:
                logger.error(f"Error inesperado: {str(e)}")
                if intento < retry:
                    time.sleep(1)
                    continue
                return None
        
        logger.error(f"Todos los intentos fallidos para: {url}")
        return None
    
    def buscar_por_numero_boleta(self, numero_boleta):
        """Buscar documentos por número de boleta."""
        logger.info(f"Buscando boleta: {numero_boleta}")
        
        params = {
            "number": numero_boleta
        }
        
        resultado = self.fetch_api_data("documents.json", params, expand=True)
        
        if resultado:
            if "items" in resultado:
                logger.info(f"Resultados encontrados: {len(resultado['items'])}")
            else:
                logger.warning(f"No se encontraron items en la respuesta")
        else:
            logger.error(f"No se obtuvo respuesta de la API")
            
        return resultado
    
    def procesar_documento(self, doc):
        """Extrae información relevante de un documento."""
        if not doc:
            logger.error("Documento vacío")
            return None
            
        numero_boleta = doc.get("number", "")
        logger.info(f"Procesando documento: {numero_boleta}")
        
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
            
            logger.info(f"Productos encontrados: {len(productos)}")
        else:
            logger.warning("No se encontraron detalles o items en el documento")
        
        # Resultado final
        return {
            "numero_boleta": numero_boleta,
            "cliente": cliente,
            "productos": productos
        }