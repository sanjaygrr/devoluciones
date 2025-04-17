from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Q
import xlwt
import datetime

from .models import Devolucion
from .forms import BusquedaBoletaForm, DevolucionForm, FiltroDevolucionesForm, NotaCreditoForm
from .bsale_api import BsaleAPI

@login_required
def index(request):
    """Vista principal con formulario de búsqueda."""
    form = BusquedaBoletaForm()
    return render(request, 'devoluciones_app/index.html', {'form': form})

@login_required
def buscar_boleta(request):
    """Buscar una boleta en Bsale."""
    if request.method != 'POST':
        return redirect('index')
    
    form = BusquedaBoletaForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Por favor, ingrese un número de boleta válido.")
        return redirect('index')
    
    numero_boleta = form.cleaned_data['numero_boleta']
    
    # Logs para depuración
    print(f"Buscando boleta: {numero_boleta}")
    
    # Conectar con la API de Bsale
    bsale_api = BsaleAPI()
    
    # Verificar token antes de la búsqueda
    print(f"Token API configurado: {bsale_api.api_token[:5]}...{bsale_api.api_token[-5:] if bsale_api.api_token else 'No configurado'}")
    print(f"Base URL configurada: {bsale_api.base_url}")
    
    try:
        resultado = bsale_api.buscar_por_numero_boleta(numero_boleta)
        
        # Log del resultado para depuración
        print(f"Resultado API: {resultado is not None}")
        if resultado:
            print(f"Items en resultado: {len(resultado.get('items', []))}")
        
        if not resultado or "items" not in resultado or not resultado["items"]:
            messages.warning(request, "No se encontraron resultados para la boleta ingresada.")
            return redirect('index')
        
        # Procesar el primer documento encontrado
        documento = bsale_api.procesar_documento(resultado["items"][0])
        
        return render(request, 'devoluciones_app/resultados_busqueda.html', {
            'documento': documento,
            'form': form
        })
    except Exception as e:
        print(f"Error al buscar boleta: {str(e)}")
        messages.error(request, f"Error al buscar la boleta: {str(e)}")
        return redirect('index')

@login_required
def registrar_devolucion(request, numero_boleta, id_producto):
    """Registrar devolución de un producto específico."""
    # Buscar la boleta nuevamente para confirmar
    bsale_api = BsaleAPI()
    resultado = bsale_api.buscar_por_numero_boleta(numero_boleta)
    
    if not resultado or "items" not in resultado or not resultado["items"]:
        messages.error(request, "No se pudo recuperar la información de la boleta.")
        return redirect('index')
    
    documento = bsale_api.procesar_documento(resultado["items"][0])
    
    # Buscar el producto específico
    producto = None
    for p in documento["productos"]:
        if str(p["id"]) == id_producto:
            producto = p
            break
    
    if not producto:
        messages.error(request, "No se encontró el producto seleccionado.")
        return redirect('index')
    
    if request.method == 'POST':
        form = DevolucionForm(request.POST)
        if form.is_valid():
            devolucion = form.save(commit=False)
            # Si el estado es normal o mal_estado, se guarda con fecha de cierre
            if devolucion.estado_devolucion in ['normal', 'mal_estado']:
                devolucion.fecha_cierre = timezone.now()
            devolucion.save()
            messages.success(request, "Devolución registrada correctamente.")
            return redirect('historial_devoluciones')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        # Inicializar formulario con datos del producto
        initial_data = {
            'numero_boleta': numero_boleta,
            'nombre_producto': producto['descripcion'],
            'codigo_producto': producto['codigo'],
            'cantidad': 1,  # Default a 1 unidad
            'fecha_devolucion': timezone.now().date(),
        }
        form = DevolucionForm(initial=initial_data)
        # Limitar la cantidad máxima al total disponible
        form.fields['cantidad'].widget.attrs['max'] = producto['cantidad']
    
    return render(request, 'devoluciones_app/registrar_devolucion.html', {
        'form': form,
        'producto': producto,
        'numero_boleta': numero_boleta
    })

@login_required
def historial_devoluciones(request):
    """Ver historial de devoluciones con filtros."""
    devoluciones = Devolucion.objects.all()
    
    # Procesar formulario de filtro
    form = FiltroDevolucionesForm(request.GET)
    if form.is_valid():
        # Filtrar por fecha desde
        if form.cleaned_data.get('fecha_desde'):
            devoluciones = devoluciones.filter(fecha_devolucion__gte=form.cleaned_data['fecha_desde'])
        
        # Filtrar por fecha hasta
        if form.cleaned_data.get('fecha_hasta'):
            devoluciones = devoluciones.filter(fecha_devolucion__lte=form.cleaned_data['fecha_hasta'])
        
        # Filtrar por estado
        if form.cleaned_data.get('estado'):
            devoluciones = devoluciones.filter(estado_devolucion=form.cleaned_data['estado'])
        
        # Filtrar por pendiente/completado
        if form.cleaned_data.get('pendiente') == 'si':
            devoluciones = devoluciones.filter(nota_credito__isnull=True)
        elif form.cleaned_data.get('pendiente') == 'no':
            devoluciones = devoluciones.filter(nota_credito__isnull=False)
        
        # Filtrar por búsqueda general
        if form.cleaned_data.get('busqueda'):
            query = form.cleaned_data['busqueda']
            devoluciones = devoluciones.filter(
                Q(numero_boleta__icontains=query) |
                Q(nombre_producto__icontains=query) |
                Q(codigo_producto__icontains=query) |
                Q(nota_credito__icontains=query)
            )
    
    # Ordenar por fecha de registro (las más recientes primero)
    devoluciones = devoluciones.order_by('-fecha_registro')
    
    return render(request, 'devoluciones_app/historial_devoluciones.html', {
        'devoluciones': devoluciones,
        'form': form
    })

@login_required
def agregar_nota_credito(request, pk):
    """Agregar o editar nota de crédito para una devolución."""
    devolucion = get_object_or_404(Devolucion, pk=pk)
    
    if request.method == 'POST':
        form = NotaCreditoForm(request.POST, instance=devolucion)
        if form.is_valid():
            # Al guardar, el método save del modelo actualizará automáticamente la fecha de cierre
            form.save()
            messages.success(request, "Nota de crédito registrada correctamente.")
            return redirect('historial_devoluciones')
    else:
        form = NotaCreditoForm(instance=devolucion)
    
    return render(request, 'devoluciones_app/agregar_nota_credito.html', {
        'form': form,
        'devolucion': devolucion
    })

@login_required
def editar_devolucion(request, pk):
    """Editar una devolución existente."""
    devolucion = get_object_or_404(Devolucion, pk=pk)
    
    if request.method == 'POST':
        form = DevolucionForm(request.POST, instance=devolucion)
        if form.is_valid():
            form.save()
            messages.success(request, "Devolución actualizada correctamente.")
            return redirect('historial_devoluciones')
    else:
        form = DevolucionForm(instance=devolucion)
    
    return render(request, 'devoluciones_app/editar_devolucion.html', {
        'form': form,
        'devolucion': devolucion
    })

@login_required
def exportar_excel(request):
    """Exportar devoluciones a Excel con los mismos filtros del historial."""
    # Obtener devoluciones con los mismos filtros que en la vista de historial
    devoluciones = Devolucion.objects.all()
    
    # Aplicar los mismos filtros que en historial_devoluciones
    form = FiltroDevolucionesForm(request.GET)
    if form.is_valid():
        # Aplicar filtros (mismo código que en historial_devoluciones)
        if form.cleaned_data.get('fecha_desde'):
            devoluciones = devoluciones.filter(fecha_devolucion__gte=form.cleaned_data['fecha_desde'])
        
        if form.cleaned_data.get('fecha_hasta'):
            devoluciones = devoluciones.filter(fecha_devolucion__lte=form.cleaned_data['fecha_hasta'])
        
        if form.cleaned_data.get('estado'):
            devoluciones = devoluciones.filter(estado_devolucion=form.cleaned_data['estado'])
        
        if form.cleaned_data.get('pendiente') == 'si':
            devoluciones = devoluciones.filter(nota_credito__isnull=True)
        elif form.cleaned_data.get('pendiente') == 'no':
            devoluciones = devoluciones.filter(nota_credito__isnull=False)
        
        if form.cleaned_data.get('busqueda'):
            query = form.cleaned_data['busqueda']
            devoluciones = devoluciones.filter(
                Q(numero_boleta__icontains=query) |
                Q(nombre_producto__icontains=query) |
                Q(codigo_producto__icontains=query) |
                Q(nota_credito__icontains=query)
            )
    
    # Crear libro de Excel
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="devoluciones_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Devoluciones')
    
    # Estilos
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    
    # Encabezados
    columns = [
        'ID', 'Número Boleta', 'Producto', 'Código', 'Cantidad', 
        'Estado', 'Nota de Crédito', 'Observaciones',
        'Fecha Devolución', 'Fecha Registro', 'Fecha Cierre'
    ]
    
    for col_num, column_title in enumerate(columns):
        ws.write(0, col_num, column_title, font_style)
    
    # Datos
    font_style = xlwt.XFStyle()
    rows = devoluciones.values_list(
        'id', 'numero_boleta', 'nombre_producto', 'codigo_producto', 
        'cantidad', 'estado_devolucion', 'nota_credito', 'observaciones',
        'fecha_devolucion', 'fecha_registro', 'fecha_cierre'
    )
    
    for row_num, row in enumerate(rows, 1):
        for col_num, cell_value in enumerate(row):
            if isinstance(cell_value, datetime.datetime):
                cell_value = cell_value.strftime('%d/%m/%Y %H:%M')
            elif isinstance(cell_value, datetime.date):
                cell_value = cell_value.strftime('%d/%m/%Y')
            elif col_num == 5:  # Estado
                # Convertir código de estado a texto legible
                estados = dict(Devolucion.ESTADO_CHOICES)
                cell_value = estados.get(cell_value, cell_value)
                
            ws.write(row_num, col_num, str(cell_value) if cell_value is not None else "", font_style)
    
    wb.save(response)
    return response