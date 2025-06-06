from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Devolucion(models.Model):
    """Modelo para registrar devoluciones de productos."""
    
    ESTADO_CHOICES = [
        ('normal', 'Normal (buen estado)'),
        ('mal_estado', 'Devolución (mal estado)'),
        ('pendiente_buen', 'Pendiente (buen estado)'),
        ('pendiente_mal', 'Pendiente (mal estado)'),
        ('extraviado', 'Extraviado'),
        ('otro', 'Otro'),
    ]
    
    MARKETPLACE_CHOICES = [
        ('', 'Seleccione marketplace'),
        ('mercadolibre', 'Mercado Libre'),
        ('falabella', 'Falabella'),
        ('ripley', 'Ripley'),
        ('walmart', 'Walmart'),
        ('paris', 'Paris'),
        ('shopify', 'Shopify'),
        ('woocommerce', 'Woocommerce'),
        ('otro', 'Otro'),
    ]
    
    numero_boleta = models.CharField(max_length=100, verbose_name="Número de Boleta")
    numero_orden = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de Orden")
    nombre_producto = models.CharField(max_length=255, verbose_name="Nombre del Producto")
    codigo_producto = models.CharField(max_length=100, blank=True, null=True, verbose_name="Código del Producto")
    cantidad = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    estado_devolucion = models.CharField(max_length=20, choices=ESTADO_CHOICES, verbose_name="Estado de la Devolución")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Nuevos campos
    marketplace = models.CharField(max_length=50, choices=MARKETPLACE_CHOICES, blank=True, null=True, verbose_name="Marketplace")
    nota_credito = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de Nota de Crédito")
    porcentaje_pago = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, verbose_name="Porcentaje de Pago")
    usuario_registro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Registrado por")
    
    # Campos de fechas
    fecha_registro = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Registro")
    fecha_devolucion = models.DateField(default=timezone.now, verbose_name="Fecha de Devolución")
    fecha_cierre = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de Cierre")
    
    @property
    def estado_pendiente(self):
        """Determina si la devolución está en estado pendiente."""
        return self.estado_devolucion in ['pendiente_buen', 'pendiente_mal', 'otro']
    
    @property
    def estado_completado(self):
        """Determina si la devolución está completada (tiene nota de crédito)."""
        return bool(self.nota_credito)
    
    def save(self, *args, **kwargs):
        # Si tiene nota de crédito y no tiene fecha de cierre, se asigna la fecha actual
        if self.nota_credito and not self.fecha_cierre:
            self.fecha_cierre = timezone.now()
        # Si se elimina la nota de crédito, se elimina la fecha de cierre
        elif not self.nota_credito:
            self.fecha_cierre = None
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Devolución"
        verbose_name_plural = "Devoluciones"
        ordering = ['-fecha_registro']
    
    def __str__(self):
        return f"Devolución {self.numero_boleta} - {self.nombre_producto}"