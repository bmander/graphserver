from django.conf.urls.defaults import *
import views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^$', views.index),
    (r'contour$', views.contour),
    (r'^js/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': '/home/brandon/projects/graphserver/apps/transitshed/frontend/transitshed/js'}),


    # Example:
    # (r'^transitshed/', include('transitshed.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/(.*)', admin.site.root),
)
