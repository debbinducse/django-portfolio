from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django.conf import settings

# Create your models here.
class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    date_posted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog_category', kwargs={'slug': self.slug})


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Post(models.Model):
    CATEGORIES = [
        ('homelab', 'Homelab'),
        ('django', 'Django'),
        ('dns-vpn', 'DNS and VPN'),
        ('ai-security', 'AI-assisted security'),
        ('freelance', 'Freelance'),
    ]

    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    POST_TYPE_CHOICES = [
        ('tutorial', 'Tutorial / How-to'),
        ('case-study', 'Case Study'),
        ('deep-dive', 'Deep Dive / Analysis'),
        ('opinion', 'Opinion / Essay'),
        ('announcement', 'Announcement'),
    ]

    title = models.CharField(max_length=200, help_text="Main headline. Aim for 60–80 characters; put the primary keyword near the front.")
    subtitle = models.CharField(max_length=160, blank=True, help_text="One-line promise under the title (max 160 chars). Say what the reader will walk away with.")
    slug = models.SlugField(max_length=200, unique=True)
    excerpt = models.TextField(blank=True, help_text="Summary shown on blog listing cards. 140–160 characters is ideal for previews and SERPs.")
    body = models.TextField(help_text="Fallback free-form body. Used when none of the structured sections below are filled in.")

    # Professional structure: Problem -> Solution -> Implementation -> Challenges -> Results -> Lessons Learned
    problem = models.TextField(blank=True, help_text="The pain point or question this post addresses. Hook the reader here (2–4 paragraphs).")
    solution = models.TextField(blank=True, help_text="Your approach and why it works. High level — save details for Implementation.")
    implementation = models.TextField(blank=True, help_text="Step-by-step build: code blocks, configs, commands. The meat of the post.")
    challenges = models.TextField(blank=True, help_text="What broke, what surprised you, dead ends. This section builds the most credibility.")
    results = models.TextField(blank=True, help_text="Measurable outcomes: benchmarks, before/after numbers, screenshots.")
    lessons_learned = models.TextField(blank=True, help_text="Takeaways and what you'd do differently. End strong — this is what readers remember.")

    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, blank=True)
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default='tutorial')
    key_takeaways = models.TextField(blank=True, help_text="3–5 bullet points, one per line. Rendered as a TL;DR box at the top of the post.")
    prerequisites = models.TextField(blank=True, help_text="What the reader needs to know/have before starting, one item per line.")
    faq = models.TextField(blank=True, help_text="Q&A pairs for the FAQ section and FAQ schema. Format: one 'Q: ...' line followed by 'A: ...' lines.")

    published_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    meta_title = models.CharField(max_length=60, blank=True, help_text="SEO title (max 60 chars). Leave blank to use post title.")
    meta_description = models.CharField(max_length=160, blank=True, help_text="SEO description (max 160 chars). Leave blank to use excerpt.")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    featured_image = models.ImageField(upload_to='blog/featured/', blank=True, null=True)
    featured_image_alt = models.CharField(max_length=125, blank=True, help_text="Alt text for featured image (max 125 chars)")
    reading_minutes = models.PositiveIntegerField(default=0, help_text="Estimated reading time in minutes. 0 = auto-calculate.")
    is_sponsored = models.BooleanField(default=False)
    affiliate_disclosure = models.TextField(blank=True, help_text="Disclosure text shown above post body if set.")
    canonical_url = models.URLField(blank=True, help_text="Canonical URL if different from post URL.")

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    SECTIONS = [
        ('problem', 'The Problem'),
        ('solution', 'The Solution'),
        ('implementation', 'Implementation'),
        ('challenges', 'Challenges & Gotchas'),
        ('results', 'Results'),
        ('lessons_learned', 'Lessons Learned'),
    ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        total_words = sum(len(getattr(self, f).split()) for f, _ in self.SECTIONS) + len(self.body.split())
        if total_words:
            self.reading_minutes = max(1, round(total_words / 200))
        super().save(*args, **kwargs)

    @property
    def has_structured_content(self):
        return any(getattr(self, field) for field, _ in self.SECTIONS)

    def structured_sections(self):
        """Return [(heading, text)] for non-empty sections, in canonical order."""
        return [(title, getattr(self, field)) for field, title in self.SECTIONS if getattr(self, field)]

    def total_word_count(self):
        return sum(len(getattr(self, field).split()) for field, _ in self.SECTIONS) + len(self.body.split())

    def takeaways_list(self):
        return [line.strip() for line in self.key_takeaways.splitlines() if line.strip()]

    def prerequisites_list(self):
        return [line.strip() for line in self.prerequisites.splitlines() if line.strip()]

    def faq_pairs(self):
        """Parse 'Q: ...' / 'A: ...' lines into [{'question': ..., 'answer': ...}]."""
        pairs = []
        current = None
        for line in self.faq.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith('q:'):
                if current:
                    pairs.append(current)
                current = {'question': stripped[2:].strip(), 'answer': []}
            elif stripped.lower().startswith('a:') and current is not None:
                current['answer'].append(stripped[2:].strip())
            elif current is not None:
                current['answer'].append(stripped)
        if current:
            pairs.append(current)
        return pairs

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'slug': self.slug})

    def get_canonical_url(self):
        if self.canonical_url:
            return self.canonical_url
        return settings.SITE_URL + self.get_absolute_url()

    def get_meta_title(self):
        return self.meta_title or self.title

    def get_meta_description(self):
        return self.meta_description or (self.excerpt[:160] if self.excerpt else '')

    def approved_comments(self):
        return self.comments.filter(is_approved=True, parent__isnull=True).order_by('created_at')

    def related_posts(self, limit=3):
        qs = Post.objects.filter(is_published=True).exclude(pk=self.pk)
        if self.category:
            qs = qs.filter(category=self.category)
        tags = self.tags.all()
        if tags.exists():
            qs = qs.filter(tags__in=tags).distinct()
        return qs[:limit]


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.name} on {self.post.title}"

    def is_reply(self):
        return self.parent is not None


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200, default='')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} from {self.name}"


class Project(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    summary = models.TextField(blank=True)
    functions = models.TextField(blank=True)
    stack = models.TextField(blank=True)
    repo_url = models.URLField(blank=True)
    live_url = models.URLField(blank=True)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-featured', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('project_detail', kwargs={'slug': self.slug})
