from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from .views import ReadingProgressViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'authors', AuthorViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'orders', OrderViewSet, basename='order')
router.register('reading-progress', ReadingProgressViewSet)


# Nested reviews
from rest_framework_nested.routers import NestedDefaultRouter  # Install: pip install drf-nested-routers
books_router = NestedDefaultRouter(router, r'books', lookup='book')
books_router.register(r'reviews', ReviewViewSet, basename='book-reviews')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(books_router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('verify/<str:token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('cart/', CartView.as_view(), name='cart'),
    path('payment/', PaymentStubView.as_view(), name='payment'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('recommendations/', RecommendationView.as_view(), name='recommendations'),
]