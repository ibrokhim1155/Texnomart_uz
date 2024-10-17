from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Prefetch, Avg, Count, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import GenericAPIView, CreateAPIView, ListCreateAPIView, ListAPIView, \
    RetrieveUpdateAPIView, \
    get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from texnomart.models import Product, Category, Image, Comment, AttributeKey, AttributeValue
from texnomart.permissions import IsSuperAdminOrReadOnly
from texnomart.serializers import ProductSerializer, CategorySerializer, ProductDetailSerializer, \
    AttributeKeySerializer, AttributeValueSerializer


def cache_get_or_set(cache_key, queryset, timeout=60 * 11):
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    cache.set(cache_key, queryset, timeout=timeout)
    return queryset


class AllProductView(ListAPIView):
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', ]
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        cache_key = 'all_products'
        queryset = cache_get_or_set(
            cache_key,
            Product.objects.select_related('category').prefetch_related('images')
        )

        if self.request.user.is_authenticated:
            user_likes = Prefetch(
                'user_likes',
                queryset=User.objects.filter(id=self.request.user.id),
                to_attr='user_liked'
            )
            queryset = queryset.prefetch_related(user_likes)
        return queryset


class CategoryView(GenericAPIView):
    queryset = Category.objects.annotate(products_count=Count('products'), products_price_sum=Sum('products__price'))
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', ]
    authentication_classes = [JWTAuthentication, TokenAuthentication]

    def get(self, request, *args, **kwargs):
        cache_key = 'category_list'
        data = cache_get_or_set(cache_key, self.get_queryset(), timeout=60 * 15)
        serializer = self.get_serializer(data, many=True, context={'request': request})
        return Response(serializer.data)


class AddCategoryView(CreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# queryset = Category.objects.annotate(products_count=Count('products'), products_price_sum=Sum('products__price'))
# serializer_class = CategorySerializer

# def get(self, request, *args, **kwargs):
#     data = self.get_queryset()
#     serializer = self.get_serializer(data, many=True, context={'request': request})
#     return Response(serializer.data)

# def post(self, request, *args, **kwargs):
#     serializer = CategorySerializer(data=request.data)
#     if serializer.is_valid():
#         serializer.save()
#         return Response(serializer.data, status=status.HTTP_201_CREATED)
#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteCategoryView(GenericAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsSuperAdminOrReadOnly]

    def get(self, request, *args, **kwargs):
        category = get_object_or_404(Category, slug=self.kwargs['slug'])
        serializer = self.get_serializer(category, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        category = get_object_or_404(Category, slug=self.kwargs['slug'])
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EditCategoryView(RetrieveUpdateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    def delete(self, request, *args, **kwargs):
        category = get_object_or_404(Category, slug=self.kwargs['slug'])
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryProductsView(GenericAPIView):
    queryset = Product.objects.select_related('category').prefetch_related(
        Prefetch('images', queryset=Image.objects.filter(is_primary=True))
    )
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', ]

    def get(self, request, *args, **kwargs):
        category_slug = self.kwargs['slug']
        cache_key = f'category_products_{category_slug}'
        products = cache_get_or_set(cache_key, self.queryset.filter(category__slug=category_slug), timeout=60 * 15)
        serializer = self.serializer_class(products, many=True, context={'request': request})
        return Response(serializer.data)


class ProductDetailView(GenericAPIView):
    queryset = Product.objects.prefetch_related(
        Prefetch('images', queryset=Image.objects.filter(is_primary=True)),
        Prefetch('comments', queryset=Comment.objects.select_related('user')),
        Prefetch('attributes', queryset=AttributeKey.objects.select_related('key').select_related('value'))
    ).annotate(rating=Avg('comments__rating'))
    serializer_class = ProductDetailSerializer

    def get(self, request, *args, **kwargs):
        product_id = self.kwargs.get('pk')
        product = self.get_queryset().filter(pk=product_id).first()

        if not product:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(product)
        return Response(serializer.data)


class DeleteProductView(GenericAPIView):
    def get(self, request, *args, **kwargs):
        product = get_object_or_404(Product, id=self.kwargs['pk'])
        serializer = ProductSerializer(product, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        product = get_object_or_404(Product, id=self.kwargs['pk'])
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EditProductView(RetrieveUpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def delete(self, request, *args, **kwargs):
        product = get_object_or_404(Product, id=self.kwargs['pk'])
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AttributeKeyView(GenericAPIView):
    queryset = AttributeKey.objects.all()
    serializer_class = AttributeKeySerializer

    def get(self, request, *args, **kwargs):
        cache_key = 'attribute_keys'
        data = cache_get_or_set(cache_key, self.get_queryset(), timeout=60 * 11)
        serializer = AttributeKeySerializer(data, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AttributeValueView(GenericAPIView):
    queryset = AttributeValue.objects.all()
    serializer_class = AttributeValueSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filter_fields = ['created_at']
    search_fields = ['name', ]

    def get(self, request, *args, **kwargs):
        cache_key = 'attribute_values'
        data = cache_get_or_set(cache_key, self.get_queryset(), timeout=60 * 15)
        serializer = AttributeValueSerializer(data, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
