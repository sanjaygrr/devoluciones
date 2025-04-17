from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('buscar/', views.buscar_boleta, name='buscar_boleta'),
    path('registrar/<str:numero_boleta>/<str:id_producto>/', views.registrar_devolucion, name='registrar_devolucion'),
    path('historial/', views.historial_devoluciones, name='historial_devoluciones'),
    path('editar/<int:pk>/', views.editar_devolucion, name='editar_devolucion'),
    path('nota-credito/<int:pk>/', views.agregar_nota_credito, name='agregar_nota_credito'),
    path('exportar/', views.exportar_excel, name='exportar_excel'),
    path('fix-database/', views.fix_database, name='fix_database'),
]