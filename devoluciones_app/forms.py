from django import forms
from django.core.exceptions import ValidationError
from .models import Devolucion

class BusquedaBoletaForm(forms.Form):
    """Formulario para buscar boletas."""
    numero_boleta = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese número de boleta'
        })
    )

class DevolucionForm(forms.ModelForm):
    """Formulario para registrar devoluciones."""
    class Meta:
        model = Devolucion
        fields = [
            'numero_boleta', 'numero_orden', 'nombre_producto', 'codigo_producto', 
            'cantidad', 'estado_devolucion', 'marketplace', 'porcentaje_pago', 
            'observaciones', 'fecha_devolucion', 'nota_credito'
        ]  # El campo usuario_registro se asigna automáticamente
        widgets = {
            'numero_boleta': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'numero_orden': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'nombre_producto': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'codigo_producto': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'estado_devolucion': forms.Select(attrs={'class': 'form-control', 'id': 'id_estado_devolucion'}),
            'marketplace': forms.Select(attrs={'class': 'form-control'}),
            'porcentaje_pago': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': '0.01'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fecha_devolucion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'nota_credito': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_nota_credito'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        estado = cleaned_data.get('estado_devolucion')
        nota_credito = cleaned_data.get('nota_credito')
        
        # Validar que los estados pendientes no tengan nota de crédito
        if estado in ['pendiente_buen', 'pendiente_mal', 'otro'] and nota_credito:
            self.add_error('nota_credito', 'No se puede asignar nota de crédito a devoluciones pendientes')
        
        # Validar que los estados normal y mal estado tengan nota de crédito
        if estado in ['normal', 'mal_estado'] and not nota_credito:
            self.add_error('nota_credito', 'Los estados Normal y Devolución requieren nota de crédito')
        
        return cleaned_data

class FiltroDevolucionesForm(forms.Form):
    """Formulario para filtrar devoluciones en el historial."""
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos')] + Devolucion.ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    marketplace = forms.ChoiceField(
        choices=[('', 'Todos')] + Devolucion.MARKETPLACE_CHOICES[1:],  # Excluir la primera opción "Seleccione marketplace"
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    pendiente = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('si', 'Pendientes'),
            ('no', 'Completados')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    busqueda = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Boleta, producto...'})
    )

class NotaCreditoForm(forms.ModelForm):
    """Formulario para agregar nota de crédito a devoluciones pendientes."""
    class Meta:
        model = Devolucion
        fields = ['nota_credito']
        widgets = {
            'nota_credito': forms.TextInput(attrs={'class': 'form-control'})
        }