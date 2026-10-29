from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.services, name='services'),
    path('blog/', views.blog, name='blog'),
    path('blog/rss/', views.blog_rss, name='blog_rss'),
    path('blog/category/<slug:slug>/', views.blog, name='blog_category'),
    path('blog/<slug:slug>/', views.post_detail, name='post_detail'),
    path('projects/', views.projects, name='projects'),
    path('projects/<slug:slug>/', views.project_detail, name='project_detail'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap_xml'),
    path('news-sitemap.xml', views.news_sitemap_xml, name='news_sitemap_xml'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
]
