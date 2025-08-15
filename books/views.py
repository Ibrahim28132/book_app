from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.shortcuts import get_object_or_404
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from .serializers import *
from .models import *

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class VerifyEmailView(generics.GenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, request, token):
        profile = get_object_or_404(UserProfile, verification_token=token)
        profile.email_verified = True
        profile.verification_token = ''
        profile.save()
        return Response({'message': 'Email verified successfully'})

# Password reset: Use DRF's built-in or add custom view
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from rest_framework.views import APIView

class PasswordResetRequestView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()
        if user:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            send_mail(
                'Password Reset',
                f'Click here: http://yourdomain.com/reset/{uid}/{token}',
                'from@example.com',
                [email]
            )
        return Response({'message': 'If email exists, reset link sent'})

class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, uidb64, token):
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        if default_token_generator.check_token(user, token):
            new_password = request.data.get('new_password')
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Password reset successful'})
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(UserProfile, user=self.request.user)

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['author__name', 'category__name', 'price']
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'published_date']

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Review.objects.filter(book_id=self.kwargs['book_pk'])

    def perform_create(self, serializer):
        book = get_object_or_404(Book, id=self.kwargs['book_pk'])
        serializer.save(user=self.request.user, book=book)

# Nested under books: /books/{id}/reviews/

class WishlistView(generics.RetrieveUpdateAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        wishlist, created = Wishlist.objects.get_or_create(user=self.request.user)
        return wishlist

    @action(detail=False, methods=['post'])
    def add(self, request):
        wishlist = self.get_object()
        book = get_object_or_404(Book, id=request.data['book_id'])
        wishlist.books.add(book)
        return Response({'message': 'Added to wishlist'})

    @action(detail=False, methods=['post'])
    def remove(self, request):
        wishlist = self.get_object()
        book = get_object_or_404(Book, id=request.data['book_id'])
        wishlist.books.remove(book)
        return Response({'message': 'Removed from wishlist'})

class CartView(generics.RetrieveUpdateAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        cart = self.get_object()
        book = get_object_or_404(Book, id=request.data['book_id'])
        quantity = request.data.get('quantity', 1)
        item, created = CartItem.objects.get_or_create(cart=cart, book=book)
        if not created:
            item.quantity += quantity
            item.save()
        return Response({'message': 'Item added'})

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        cart = self.get_object()
        book = get_object_or_404(Book, id=request.data['book_id'])
        CartItem.objects.filter(cart=cart, book=book).delete()
        return Response({'message': 'Item removed'})

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        cart = Cart.objects.get(user=self.request.user)
        total = sum(item.book.price * item.quantity for item in cart.cartitem_set.all())
        profile = UserProfile.objects.get(user=self.request.user)
        if not profile.address:
            raise serializers.ValidationError("Add shipping address to profile")
        order = serializer.save(user=self.request.user, total_amount=total, shipping_address=profile.address)
        for item in cart.cartitem_set.all():
            OrderItem.objects.create(order=order, book=item.book, quantity=item.quantity, price=item.book.price)
            item.book.stock -= item.quantity
            item.book.save()
        cart.cartitem_set.all().delete()
        # Send order confirmation email
        send_mail('Order Placed', 'Your order has been placed.', 'from@example.com', [self.request.user.email])

class PaymentStubView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data['order_id']
        # In real-world, integrate Stripe here
        # stripe.PaymentIntent.create(amount=..., currency='usd')
        return Response({'message': 'Payment processed (stub)', 'status': 'success'})
