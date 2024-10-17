from django.utils import timezone
from django.db import models
from django.template.defaultfilters import slugify
from django.contrib.auth.models import User


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class Category(BaseModel):
    title = models.CharField(max_length=300, unique=True)
    slug = models.SlugField(max_length=300, blank=True, unique=True)
    image = models.ImageField(upload_to='images/', blank=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Product(BaseModel):
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, blank=True)
    price = models.FloatField()
    description = models.TextField()
    user_likes = models.ManyToManyField(User, related_name='likes', blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    discount = models.FloatField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            similar_slugs = Product.objects.filter(slug__startswith=base_slug).count()
            self.slug = base_slug if similar_slugs == 0 else f'{base_slug}-{similar_slugs + 1}'
        super().save(*args, **kwargs)

    @property
    def discounted_price(self):
        return self.price * (1 - self.discount / 100) if self.discount > 0 else self.price

    @property
    def monthly_pay(self):
        return f'{round(self.discounted_price / 24, 1)} sum / 24 months' if self.discounted_price else None

    def __str__(self):
        return self.name


class Image(BaseModel):
    image = models.ImageField(upload_to='images/')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Image of {self.product.name}"


class AttributeValue(BaseModel):
    value = models.CharField(max_length=300)

    def __str__(self):
        return self.value


class AttributeKey(BaseModel):
    key = models.CharField(max_length=300)

    def __str__(self):
        return self.key


class Attribute(BaseModel):
    key = models.ForeignKey(AttributeKey, on_delete=models.CASCADE)
    value = models.ForeignKey(AttributeValue, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='attributes')

    def __str__(self):
        return f'{self.product.name} + {self.key}'


class Comment(BaseModel):
    class RatingChoices(models.IntegerChoices):
        Zero = 0
        One = 1
        Two = 2
        Three = 3
        Four = 4
        Five = 5

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comments')
    rating = models.IntegerField(choices=RatingChoices.choices, default=RatingChoices.Zero.value)
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments_u')

    def __str__(self):
        return f'Comment by {self.user.username} on {self.product.name}'
