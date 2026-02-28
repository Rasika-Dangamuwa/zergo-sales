from django.urls import path
from . import views

app_name = 'shops'

urlpatterns = [
    path('', views.shop_list, name='list'),
    path('add/', views.add_shop, name='add'),
    path('<int:pk>/', views.shop_detail, name='detail'),
    path('<int:pk>/edit/', views.edit_shop, name='edit'),
    path('<int:pk>/access/', views.manage_shop_access, name='manage_access'),
    path('<int:pk>/upload-photo/', views.upload_shop_photo, name='upload_photo'),
    path('<int:pk>/mark-visit/', views.mark_visit, name='mark_visit'),
    path('<int:pk>/toggle-active/', views.toggle_shop_active, name='toggle_active'),
    path('map/', views.shop_map, name='map'),
    path('nearby/', views.nearby_shops_page, name='nearby'),
    path('api/shops-geojson/', views.shops_geojson, name='shops_geojson'),
    path('api/track-location/', views.track_location, name='track_location'),
    path('api/nearby/', views.nearby_shops, name='nearby_shops'),
]
