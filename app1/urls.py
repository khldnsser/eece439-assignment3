from django.contrib.auth import views as auth_views
from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('budget/', views.budget, name='budget'),
    path('add_expense/', views.add_expense, name='add_expense'),
    path('display_expense/', views.display_expense, name='display_expense'),
    path('update_expense/<int:ExpenseID>/', views.update_expense, name='update_expense'),
    path('delete_expense/<int:ExpenseID>/', views.delete_expense, name='delete_expense'),
]
