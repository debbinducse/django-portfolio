from django.contrib import admin
from django.utils.html import format_html
from .models import BlogPost, ContactMessage, Post, Comment, Project, Category, Tag


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ('name', 'email', 'body', 'parent', 'is_approved', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = True
    verbose_name = 'Comment'
    verbose_name_plural = 'Comments'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('parent').order_by('created_at')


class CommentAdmin(admin.ModelAdmin):
    list_display = ('name', 'post', 'parent', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at', 'post')
    search_fields = ('name', 'email', 'body')
    actions = ['approve_comments']

    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
    approve_comments.short_description = 'Approve selected comments'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('post', 'parent')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'post_type_label', 'difficulty', 'category', 'word_count_display', 'structure_progress', 'is_published', 'published_at')
    list_display_links = ('title',)
    list_filter = ('is_published', 'is_sponsored', 'post_type', 'difficulty', 'category', 'tags', 'published_at')
    search_fields = ('title', 'subtitle', 'body', 'problem', 'solution', 'implementation', 'excerpt', 'meta_title', 'meta_description')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'reading_minutes', 'content_checklist')
    inlines = [CommentInline]
    filter_horizontal = ('tags',)
    save_on_top = True

    fieldsets = (
        ('1. Framing — hook the reader', {
            'fields': ('title', 'subtitle', 'slug', 'excerpt', 'post_type', 'difficulty', 'category', 'tags'),
            'description': 'Title: 60–80 chars. Subtitle: ≤160 chars, one clear promise. Excerpt: 140–160 chars for listings/SERPs.',
        }),
        ('2. TL;DR — respect the reader\'s time', {
            'fields': ('key_takeaways', 'prerequisites'),
            'description': 'Key takeaways: 3–5 bullets, one per line. Prerequisites: what the reader needs first, one per line.',
            'classes': ('collapse',),
        }),
        ('3. Story structure — Problem → Solution → Implementation → Challenges → Results → Lessons', {
            'fields': ('problem', 'solution', 'implementation', 'challenges', 'results', 'lessons_learned'),
            'description': 'Fill these in order. Each becomes an H2 section on the page. Leave any that don\'t apply blank.',
        }),
        ('4. Free-form body (fallback)', {
            'fields': ('body',),
            'description': 'Only used if no structured sections above are filled. Most posts can leave this blank.',
            'classes': ('collapse',),
        }),
        ('5. FAQ & extras', {
            'fields': ('faq', 'affiliate_disclosure', 'is_sponsored'),
            'description': 'FAQ format: "Q: question" line followed by "A: answer" line(s). Also emitted as FAQ schema.',
            'classes': ('collapse',),
        }),
        ('6. SEO & social', {
            'fields': ('meta_title', 'meta_description', 'canonical_url', 'featured_image', 'featured_image_alt'),
            'description': 'Meta title ≤60 chars (blank = post title). Meta description 140–160 chars (blank = excerpt). Featured image: 1200×630px ideal for OG sharing.',
        }),
        ('7. Publish', {
            'fields': ('content_checklist', 'is_published', 'published_at', 'reading_minutes', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Type')
    def post_type_label(self, obj):
        return obj.get_post_type_display()

    @admin.display(description='Words')
    def word_count_display(self, obj):
        words = obj.total_word_count()
        # Professional technical posts: 1,200–2,500 words
        if words < 800:
            note, css = 'thin (aim 1200+)', '#b45309'
        elif words > 3000:
            note, css = 'long', '#6b7280'
        else:
            note, css = 'good', '#047857'
        return format_html('<b>{}</b> <span style="color:{}">({})</span>', f'{words:,}', css, note)

    @admin.display(description='Structure')
    def structure_progress(self, obj):
        filled = sum(1 for field, _ in obj.SECTIONS if getattr(obj, field))
        icons = ''.join('✅' if getattr(obj, field) else '⬜' for field, _ in obj.SECTIONS)
        return format_html('{} {}/6', icons, filled)

    @admin.display(description='Pre-publish checklist')
    def content_checklist(self, obj):
        words = obj.total_word_count()
        checks = [
            ('Title is 60–80 characters', 40 <= len(obj.title) <= 80),
            ('Subtitle set (≤160 chars)', bool(obj.subtitle) and len(obj.subtitle) <= 160),
            ('Excerpt is 140–160 characters', 120 <= len(obj.excerpt) <= 160),
            ('At least Problem + Solution filled', bool(obj.problem) and bool(obj.solution)),
            ('Has Implementation detail', bool(obj.implementation)),
            ('Has Challenges or Results (credibility)', bool(obj.challenges) or bool(obj.results)),
            ('Ends with Lessons Learned', bool(obj.lessons_learned)),
            ('3–5 key takeaways', 3 <= len(obj.takeaways_list()) <= 5),
            ('Word count 1,200–2,500', 1200 <= words <= 2500),
            ('Featured image + alt text', bool(obj.featured_image) and bool(obj.featured_image_alt)),
            ('Meta title ≤60 chars', len(obj.meta_title or obj.title) <= 60),
            ('Meta description ≤160 chars', len(obj.get_meta_description()) <= 160),
            ('Category assigned', obj.category_id is not None),
            ('At least 2 tags', obj.tags.count() >= 2 if obj.pk else False),
        ]
        rows = ''.join(
            format_html(
                '<li style="padding:2px 0;color:{}">{} {}</li>',
                '#047857' if ok else '#b45309', '✔' if ok else '✖', label
            )
            for label, ok in checks
        )
        done = sum(1 for _, ok in checks if ok)
        return format_html(
            '<div style="border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;background:#fafafa">'
            '<b>Writing score: {}/{} {}</b><ul style="margin:8px 0 0;list-style:none;padding:0">{}</ul></div>',
            done, len(checks),
            '— ready to publish 🎉' if done == len(checks) else '',
            rows
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('category').prefetch_related('tags', 'comments')


admin.site.register(BlogPost)
admin.site.register(ContactMessage)
admin.site.register(Post, PostAdmin)
admin.site.register(Comment, CommentAdmin)


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'featured', 'created_at')
    list_filter = ('featured', 'created_at')
    search_fields = ('title', 'summary', 'stack')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(Project, ProjectAdmin)