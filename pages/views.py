from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.http import HttpResponse
from django.utils.feedgenerator import Rss201rev2Feed
from django.utils.timezone import now
from django.urls import reverse
from datetime import timedelta
from .models import BlogPost, ContactMessage, Post, Comment, Project, Category, Tag


def home(request):
    latest_posts = Post.objects.filter(is_published=True).order_by('-published_at')[:3]
    featured_projects = Project.objects.filter(featured=True)[:3]
    return render(request, 'pages/home.html', {'latest_posts': latest_posts, 'featured_projects': featured_projects})


def services(request):
    return render(request, 'pages/services.html')


def about(request):
    github_url = getattr(settings, 'GITHUB_URL', '')
    return render(request, 'pages/about.html', {'GITHUB_URL': github_url})


def contact(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        if name and email and subject and message:
            ContactMessage.objects.create(name=name, email=email, subject=subject, message=message)
            return render(request, 'pages/contact.html', {'success': True})
    return render(request, 'pages/contact.html')


def blog(request):
    category_slug = request.GET.get('category')
    posts = Post.objects.filter(is_published=True).select_related('category').prefetch_related('tags')
    categories = Category.objects.all()

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        posts = posts.filter(category=category)
    else:
        category = None

    posts = posts.order_by('-published_at')
    return render(request, 'pages/blog.html', {'posts': posts, 'categories': categories, 'current_category': category})


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    comments = post.approved_comments()
    github_url = getattr(settings, 'GITHUB_URL', '')
    related_posts = post.related_posts()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        body = request.POST.get('body', '').strip()
        parent_id = request.POST.get('parent_id')

        if name and email and body:
            parent = None
            if parent_id:
                try:
                    parent = Comment.objects.get(id=parent_id, post=post, is_approved=True)
                except Comment.DoesNotExist:
                    parent = None
            Comment.objects.create(
                post=post,
                parent=parent,
                name=name,
                email=email,
                body=body,
                is_approved=False
            )
            return redirect('post_detail', slug=slug)

    return render(request, 'pages/post_detail.html', {
        'post': post,
        'comments': comments,
        'GITHUB_URL': github_url,
        'related_posts': related_posts,
    })


def projects(request):
    projects = Project.objects.all()
    featured = Project.objects.filter(featured=True)
    return render(request, 'pages/projects.html', {'projects': projects, 'featured': featured})


def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug)
    return render(request, 'pages/project_detail.html', {'project': project})


def blog_rss(request):
    posts = Post.objects.filter(is_published=True).order_by('-published_at')[:20]
    site_url = getattr(settings, 'SITE_URL', 'https://debbairagi.com.bd')

    feed = Rss201rev2Feed(
        title="Debbindu Bairagi - Blog",
        link=site_url + "/blog/",
        description="Linux admin and Django developer. Homelab, Django, DNS/VPN, AI-assisted security, Freelance.",
        language="en",
        author_name="Debbindu Bairagi",
        author_email="",
        author_link=site_url + "/about/",
    )

    for post in posts:
        post_url = site_url + post.get_absolute_url()
        feed.add_item(
            title=post.title,
            link=post_url,
            description=post.excerpt or post.body[:300],
            author_name="Debbindu Bairagi",
            author_email="",
            author_link=site_url + "/about/",
            pubdate=post.published_at or post.created_at,
            unique_id=post_url,
            categories=[post.category.name] if post.category else [],
        )

    response = HttpResponse(content_type='application/rss+xml; charset=utf-8')
    feed.write(response, 'utf-8')
    return response


def sitemap_xml(request):
    site_url = getattr(settings, 'SITE_URL', 'https://debbairagi.com.bd')
    posts = Post.objects.filter(is_published=True).order_by('-published_at')
    projects = Project.objects.all()

    urls = [
        {'loc': site_url + '/', 'changefreq': 'weekly', 'priority': '1.0'},
        {'loc': site_url + '/about/', 'changefreq': 'monthly', 'priority': '0.8'},
        {'loc': site_url + '/services/', 'changefreq': 'monthly', 'priority': '0.6'},
        {'loc': site_url + '/contact/', 'changefreq': 'monthly', 'priority': '0.6'},
        {'loc': site_url + '/blog/', 'changefreq': 'daily', 'priority': '0.9'},
        {'loc': site_url + '/projects/', 'changefreq': 'weekly', 'priority': '0.8'},
    ]

    for project in projects:
        urls.append({
            'loc': site_url + project.get_absolute_url(),
            'changefreq': 'monthly',
            'priority': '0.7',
            'lastmod': project.updated_at.date() if project.updated_at else None,
        })

    for post in posts:
        urls.append({
            'loc': site_url + post.get_absolute_url(),
            'changefreq': 'weekly',
            'priority': '0.8',
            'lastmod': (post.updated_at or post.published_at or post.created_at).date(),
        })

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for url in urls:
        xml.append('  <url>')
        xml.append(f'    <loc>{url["loc"]}</loc>')
        if url.get('lastmod'):
            xml.append(f'    <lastmod>{url["lastmod"]}</lastmod>')
        if url.get('changefreq'):
            xml.append(f'    <changefreq>{url["changefreq"]}</changefreq>')
        if url.get('priority'):
            xml.append(f'    <priority>{url["priority"]}</priority>')
        xml.append('  </url>')
    xml.append('</urlset>')

    return HttpResponse('\n'.join(xml), content_type='application/xml')


def news_sitemap_xml(request):
    site_url = getattr(settings, 'SITE_URL', 'https://debbairagi.com.bd')
    cutoff = now() - timedelta(hours=48)
    posts = Post.objects.filter(is_published=True, published_at__gte=cutoff).order_by('-published_at')

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">')
    for post in posts:
        post_url = site_url + post.get_absolute_url()
        pub_date = post.published_at or post.created_at
        xml.append('  <url>')
        xml.append(f'    <loc>{post_url}</loc>')
        xml.append(f'    <news:news>')
        xml.append(f'      <news:publication>')
        xml.append(f'        <news:name>Debbindu Bairagi</news:name>')
        xml.append(f'        <news:language>en</news:language>')
        xml.append(f'      </news:publication>')
        xml.append(f'      <news:publication_date>{pub_date.isoformat()}</news:publication_date>')
        xml.append(f'      <news:title>{post.title}</news:title>')
        xml.append(f'    </news:news>')
        xml.append('  </url>')
    xml.append('</urlset>')

    return HttpResponse('\n'.join(xml), content_type='application/xml')


def robots_txt(request):
    site_url = getattr(settings, 'SITE_URL', 'https://debbairagi.com.bd')
    content = f"""User-agent: *
Allow: /

User-agent: Googlebot
Allow: /

Sitemap: {site_url}/sitemap.xml
Sitemap: {site_url}/news-sitemap.xml
"""
    return HttpResponse(content, content_type='text/plain')