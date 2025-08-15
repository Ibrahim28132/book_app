from django.contrib import admin
from .models import Author, Category, Book, Cart, CartItem, Order, OrderItem

admin.site.register(Author)
admin.site.register(Category)
admin.site.register(Book)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
