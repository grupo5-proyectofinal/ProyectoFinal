from django.contrib import admin

from .models import Category, Membership, Pool, PoolImage

admin.site.register(Category)
admin.site.register(Pool)
admin.site.register(PoolImage)
admin.site.register(Membership)
