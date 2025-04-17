from django.contrib import admin
from .models import Devolucion

@admin.register(Devolucion)
class DevolucionAdmin(admin.ModelAdmin):
    list_display = ('numero_boleta', 'nombre_producto', 'cantidad', 'estado_devolucion', 'marketplace', 'fecha_devolucion')
    list_filter = ('estado_devolucion', 'marketplace', 'fecha_devolucion')
    search_fields = ('numero_boleta', 'nombre_producto', 'codigo_producto', 'nota_credito')
    date_hierarchy = 'fecha_devolucion'