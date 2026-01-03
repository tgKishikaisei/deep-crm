

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api

app_name = 'crm'  # Пространство имен для URL-адресов

# Создаем роутер и регестрируем наши API
router = DefaultRouter()
router.register(r'clients', api.ClientViewSet, basename='api_client')
router.register(r'deals', api.DealViewSet, basename='api_deal')
router.register(r'tasks', api.TaskViewSet, basename='api_task')

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('deals/', views.DealListView.as_view(), name='deal_list'),
    # path('', views.HomeView.as_view(), name='home'),

    # Список сделок (главная страница)
    path('deal/<int:pk>/', views.DealDetailView.as_view(),
         name='deal_detail'),
    path('deal/create/', views.DealCreateView.as_view(),
         name='deal_create'),
    path('deal/<int:pk>/update/',
         views.DealUpdateView.as_view(), name='deal_update'),
    path('deal/<int:pk>/delete/',
         views.DealDeleteView.as_view(), name='deal_delete'),
    path('kanban/', views.KanbanView.as_view(), name='kanban'),

    # URL-ы для Клиентов
    path('clients/',
         views.ClientListView.as_view(), name='client_list'),
    path('client/<int:pk>/',
         views.ClientDetailView.as_view(), name='client_detail'),
    path('client/create/',
         views.ClientCreateView.as_view(), name='client_create'),
    path('client/<int:pk>/update/',
         views.ClientUpdateView.as_view(), name='client_update'),
    path('client/<int:pk>/delete/',
         views.ClientDeleteView.as_view(), name='client_delete'),

    # Путь для поиска
    path('search/', views.GlobalSearchView.as_view(), name='global_search'),

    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('api/events/', views.calendar_events, name='calendar_events'),

    # Задачи
    path('tasks/', views.TaskListView.as_view(), name='task_list'),  # Все задачи
    path('deal/<int:deal_pk>/add-task/', views.TaskCreateView.as_view(), name='task_create'),  # Создать задачу для конкретной сделки
    path('task/<int:pk>/update/', views.TaskUpdateView.as_view(), name='task_update'),
    path('task/<int:pk>/delete/',views.TaskDeleteView.as_view(), name='task_delete'),

    path('about/', views.AboutView.as_view(), name='about'),

    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),

    path('motivation/', views.MotivationView.as_view(), name='motivation'),

    path('vision/', views.VisionView.as_view(), name='vision'),

    path('lab/', views.LabView.as_view(), name='lab'),

    path('api/v1/', include(router.urls)),
]