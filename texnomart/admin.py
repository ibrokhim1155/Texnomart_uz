from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Product, Category, Image, Comment, Attribute, AttributeValue, AttributeKey


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    exclude = ('slug',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    fields = ['title', 'image', 'get_image']
    list_display = ['title', 'get_image', 'slug']
    search_fields = ['title']
    readonly_fields = ['get_image']

    def get_image(self, obj):
        if obj.image:
            return mark_safe(f"<img src='{obj.image.url}' width='50' height='50'>")
        return "No image"

    get_image.short_description = 'Image'


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['is_primary', 'image', 'product']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['rating', 'product', 'user', 'content']
    readonly_fields = ['user']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)


admin.site.register(Attribute)
admin.site.register(AttributeValue)
admin.site.register(AttributeKey)
