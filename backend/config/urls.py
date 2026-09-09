"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.views.static import serve
from django.urls import include, path, re_path

urlpatterns = [
    path('api/auth/', include('apps.accounts.urls')),
    path('api/environment/', include('apps.accounts.environment_urls')),
]

index_file = settings.FRONTEND_DIST_DIR / 'index.html'
assets_dir = settings.FRONTEND_DIST_DIR / 'assets'
if index_file.exists() and assets_dir.exists():
    urlpatterns += [
        re_path(r'^assets/(?P<path>.*)$', serve, {'document_root': assets_dir}),
        path('', TemplateView.as_view(template_name='index.html')),
        path('admin/', TemplateView.as_view(template_name='index.html')),
        re_path(r'^(?!api/|media/|assets/).*$',
                TemplateView.as_view(template_name='index.html')),
    ]
else:
    urlpatterns += [
        path('', lambda request: HttpResponse('frontend dist not found, use Vite dev server: http://localhost:5173/')),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
