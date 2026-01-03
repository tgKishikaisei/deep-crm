import json

from django.shortcuts import render

# Create your views here.

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from django.views.generic.base import TemplateView
from django.views.generic import TemplateView as Templateview
from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from django.core.cache import cache

from .models import Deal, Client, Task
from .filters import ClientFilter

from users.models import User

from .tasks import send_congrats_email

class HomeView(Templateview):
    template_name = 'home.html'


# Миксин для проверки, является ли пользователь администратором
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'ADMIN'


class DealListView(LoginRequiredMixin, ListView):
    """
    Представление для отображения списка сделок
    Доступна всем авторизованным пользователям
    """
    model = Deal
    template_name = 'crm/deal_list.html'  # Указываем путь к нашему будущему шаблон
    context_object_name = 'deals'  # Имя, по которому будем обрашаться к списку в шаблоне
    paginate_by = 10  # Добавляем пагинацию, по 10 сделок на страницу

    def get_queryset(self):
        """
        Переопределяем метод для фильтрации сделок
        Админ видит все сделки, менеджер - только свои
        """
        user = self.request.user
        queryset = super().get_queryset().select_related('client', 'manager')  # Оптимизация запроса!

        if user.role == 'MANAGER':
            return queryset.filter(manager=user)
        return queryset


class DealDetailView(LoginRequiredMixin, DetailView):
    """
    Детальное представление сделки
    Менеджер может видеть только свою сделку
    """
    model = Deal
    template_name = 'crm/deal_detail.html'
    context_object_name = 'deal'

    def get_queryset(self):
        user = self.request.user

        # МАГИЯ ЗДЕСЬ: select_related
        # Мы говорим: "Сделай JOIN таблиц client и manager сразу"
        queryset = super().get_queryset().select_related('client', 'manager')

        if user.role == 'MANAGER':
            queryset = queryset.filter(manager=user)

        # ... фильтры ...
        # self.filterset = DealFilter(self.request.GET, queryset=queryset)
        return queryset


class DealCreateView(LoginRequiredMixin, CreateView):
    """
    Представление для создания новой сделки
    """
    model = Deal
    template_name = 'crm/deal_form.html'
    fields = ['client', 'title', 'amount', 'stage']  # Поля, которую будут в форме
    success_url = reverse_lazy('crm:deal_list')  # Куда перенаправить после успеха

    def form_valid(self, form):
        """
        Переопределяем метод, чтобы автоматически назначить
        текущего пользователя менеджером сделки
        """

        form.instance.manager = self.request.user
        return super().form_valid(form)


class DealUpdateView(LoginRequiredMixin, UpdateView):
    """
    Представление для редактирования сделки
    Менеджер может редактировать только свои сделки
    """
    model = Deal
    template_name = 'crm/deal_form.html'
    fields = ['client', 'title', 'amount', 'stage']
    success_url = reverse_lazy('crm:deal_list')

    def get_queryset(self):
        """
        Безопасность! Убеждаемся, что менеджер не может
        отредактировать чужую сделку, просто подставим ID в URL
        """
        user = self.request.user
        queryset = super().get_queryset()

        if user.role == 'MANAGER':
            return queryset.filter(manager=user)
        return queryset

    def form_valid(self, form):
        # Сначала сохраняем изменения
        response = super().form_valid(form)

        # Проверяем, стала ли стадия WON (Успех)
        if form.instance.stage == 'WON':
            # ЗАПУСКАЕМ ФОНОВУЮ ЗАДАЧУ
            # Используем .delay() - это магия Celery
            # Мы передаем только строки (email, название), а не объекты базы!
            send_congrats_email.delay(form.instance.client.email, form.instance.title)

        return response
class DealDeleteView(LoginRequiredMixin, DetailView):
    """
    Представление для удаления сделки
    Доступно только администратору
    """
    model = Deal
    template_name = 'crm/deal_confirm_delete.html'
    success_url = reverse_lazy('crm:deal_list')

    def get_queryset(self):
        """
        Доступ на удаление имеет только админ
        """
        user = self.request.user
        if user.role == 'ADMIN':
            return super().get_queryset()
        # Возвращаем пустой queryset, если не админ, что приведет к 404
        return self.model.objects.none()


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'crm/client_list.html'
    context_object_name = 'clients'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        # Сначала получаем базовый queryset
        queryset = super().get_queryset().select_related('manager')

        # Если пользователь - менеджер, фильтруем по нему
        if user.role == 'MANAGER':
            queryset = queryset.filter(manager=user)

        # 1. СОЗДАЕМ АТРИБУТ self.filterset
        # Эта строка ОБЯЗАТЕЛЬНА, чтобы следующий метод мог работать
        self.filterset = ClientFilter(self.request.GET, queryset=queryset)

        # Возвращаем отфильтрованный queryset для отображения в таблице
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        # 2. ИСПОЛЬЗУЕМ АТРИБУТ self.filterset
        # Этот метод вызывается ПОСЛЕ get_queryset, поэтому self.filterset уже существует
        context = super().get_context_data(**kwargs)
        # Передаем объект фильтра в контекст, чтобы отобразить форму в шаблоне
        context['filter'] = self.filterset
        return context


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'crm/client_detail.html'
    context_object_name = 'client'

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user.role == 'MANAGER':
            return queryset.filter(manager=user)
        return queryset


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    template_name = 'crm/client_form.html'
    fields = ['company_name', 'contact_person', 'email', 'phone']
    success_url = reverse_lazy('crm:client_list')

    def form_valid(self, form):
        form.instance.manager = self.request.user
        return super().form_valid(form)


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    template_name = 'crm/client_form.html'
    fields = ['company_name', 'contact_person', 'email', 'phone']
    success_url = reverse_lazy('crm:client_list')

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user.role == 'MANAGER':
            return queryset.filter(manager=user)
        return queryset


class ClientDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """
    Представление для удаления клиента
    Доступна только для администратора благодаря (AdminRequiredMixin)
    """
    model = Client
    template_name = 'crm/client_confirm_delete.html'
    success_url = reverse_lazy('crm:client_list')

    def get_queryset(self):
        """
        Допольнительно убеждаемся, что только админ может получить доступ
        Хотя AdminRequiredMixin уже делает проверку, это хорошая практика
        Для зашиты на уровне данных
        """
        if self.request.user.role == 'ADMIN':
            return super().get_queryset()
        return self.model.objects.none()


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # --- 2. ПРОВЕРКА КЭША ---
        # Создаем уникальный ключ для каждого пользователя
        # (чтобы Manager1 не увидел данные Manager2)
        cache_key = f"dashboard_stats_{user.id}"

        # Пытаемся достать данные из Redis
        cached_data = cache.get(cache_key)

        if cached_data:
            # Если данные есть в кэше — просто добавляем их в контекст и выходим!
            # База данных не тревожится.
            print("⚡ Данные загружены из Redis")  # Для проверки в консоли
            context.update(cached_data)
            return context

        # --- 3. ЕСЛИ КЭША НЕТ — СЧИТАЕМ (Твой старый код) ---
        print("🐢 Считаем данные из Базы Данных...")

        user_deals = Deal.objects.filter(manager=user)
        user_clients = Client.objects.filter(manager=user)

        # Собираем все тяжелые данные в словарь 'data'
        data = {}

        # Карточка Активные сделки
        active_deals = user_deals.filter(stage__in=['NEW', 'IN_PROGRESS'])
        data['active_deals_count'] = active_deals.count()

        # Карточка Сумма
        total_amount_dict = active_deals.aggregate(total=Sum('amount'))
        data['active_deals_total_amount'] = total_amount_dict['total'] or 0

        # Карточка Новые клиенты
        one_month_ago = timezone.now() - timedelta(days=30)
        data['new_clients_count'] = user_clients.filter(created_at__gte=one_month_ago).count()

        # Список последних сделок
        # ВАЖНО: Оборачиваем в list(), чтобы выполнить запрос к БД сейчас и сохранить результат,
        # иначе в кэш попадет "ленивый" запрос, который не сработает потом.
        data['latest_deals'] = list(user_deals.order_by('-created_at')[:5])

        # Графики
        count_new = user_deals.filter(stage='NEW').count()
        count_progress = user_deals.filter(stage='IN_PROGRESS').count()
        count_won = user_deals.filter(stage='WON').count()
        count_lost = user_deals.filter(stage='LOST').count()

        data['chart_stages_data'] = json.dumps([count_new, count_progress, count_won, count_lost])

        last_deals = user_deals.order_by('-created_at')[:7]
        deal_titles = [deal.title for deal in last_deals]
        deal_amounts = [float(deal.amount) for deal in last_deals]

        data['chart_titles'] = json.dumps(deal_titles[::-1])
        data['chart_amounts'] = json.dumps(deal_amounts[::-1])

        # Задачи (тоже list)
        data['upcoming_tasks'] = list(Task.objects.filter(assignee=user, status='PENDING').order_by('due_date')[:5])

        # --- 4. СОХРАНЯЕМ В КЭШ ---
        # Сохраняем словарь 'data' в Redis на 300 секунд (5 минут)
        cache.set(cache_key, data, 300)

        # Обновляем контекст страницы
        context.update(data)

        return context
# class DashboardView(LoginRequiredMixin, TemplateView):
#     template_name = 'crm/dashboard.html'
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         user = self.request.user
#
#         # Определяем базовый Queryset для сделок и клиентов текущего пользователя
#         user_deals = Deal.objects.filter(manager=user)
#         user_clients = Client.objects.filter(manager=user)
#
#         # Карточка Активные сделки
#         active_deals = user_deals.filter(stage__in=['NEW', 'IN_PROGRESS'])
#         context['active_deals_count'] = active_deals.count()
#
#         # Карточка Сумма активных сделок
#         # .aggregate() возвращает словарь Мы получаем из него значение по ключу
#         total_amount_dict = active_deals.aggregate(total=Sum('amount'))
#         context['active_deals_total_amount'] = total_amount_dict['total'] or 0  # or 0 на случай если сделок нет
#
#         # Карточка Новые клиенты за 30 дней
#         one_month_ago = timezone.now() - timedelta(days=30)
#         context['new_clients_count'] = user_clients.filter(created_at__gte=one_month_ago).count()
#
#         # Список последних 5 сделок
#         context['latest_deals'] = user_deals.order_by('-created_at')[:5]
#
#         # Данные для Круговой диограммы (По стадии)
#         # Считаем количество сделок в каждой стадии
#         count_new = user_deals.filter(stage='NEW').count()
#         count_progress = user_deals.filter(stage='IN_PROGRESS').count()
#         count_won = user_deals.filter(stage='WON').count()
#         count_lost = user_deals.filter(stage='LOST').count()
#
#         # Передаем как список
#         context['chart_stages_data'] = json.dumps([count_new, count_progress, count_won, count_lost])
#
#         # Данные для Графика (Последние 5 сделок по сумме)
#         # Возьмем последние 5 сделок и покажем их суммы
#         last_deals = user_deals.order_by('-created_at')[:7]
#
#         # Название сделок (для оси X)
#         deal_titles = [deal.title for deal in last_deals]
#
#         # Суммы (для оси Y)
#         deal_amounts = [float(deal.amount) for deal in last_deals]  # float нужен для JSON
#
#         # Разворачиваем список, чтобы старые были слева (для графика красивая)
#         context['chart_titles'] = json.dumps(deal_titles[::-1])
#         context['chart_amounts'] = json.dumps(deal_amounts[::-1])
#         # TODO: Добавить логику для задач, когда они будут реализованы
#         context['upcoming_tasks'] = Task.objects.filter(assignee=user, status='PENDING').order_by('due_date')[:5]
#         return context


class KanbanView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/kanban.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Получаем сделки менеджера
        deals = Deal.objects.filter(manager=user)

        # Разбираем из по стадиям для колонок
        context['deals_new'] = deals.filter(stage='NEW')
        context['deals_progress'] = deals.filter(stage='IN_PROGRESS')
        context['deals_won'] = deals.filter(stage='WON')
        context['deals_lost'] = deals.filter(stage='LOST')

        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/profile.html'


class GlobalSearchView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        results = []

        if query:
            # 1. Ищем Клиентов
            clients = Client.objects.filter(
                Q(company_name__icontains=query) |
                Q(contact_person__icontains=query) |
                Q(email__icontains=query)
            )[:5]

            for client in clients:
                results.append({
                    'type': 'client',
                    'title': client.company_name,
                    'desc': str(client.contact_person), # Превращаем в строку на всякий случай
                    'url': str(reverse('crm:client_detail', kwargs={'pk': client.pk})) # <-- ВАЖНО: str(reverse(...))
                })

            # 2. Ищем Сделки
            deals = Deal.objects.filter(
                Q(title__icontains=query)
            )[:5]

            for deal in deals:
                results.append({
                    'type': 'deal',
                    'title': deal.title,
                    'desc': f"{deal.amount} ₽",
                    'url': str(reverse('crm:deal_detail', kwargs={'pk': deal.pk})) # <-- ВАЖНО
                })

        return JsonResponse({'results': results})


# Страница календаря
class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/calendar.html'


# Api которые отдает события (Сделки и Задачи)
def calendar_events(request):
    user = request.user
    events = []

    # Добавляем Сделки (по дате создании)
    deals = Deal.objects.filter(manager=user)
    for deal in deals:
        events.append({
            'title': f"💰 {deal.title}",
            'start': deal.created_at.strftime('%Y-%m-%d'),
            'url': str(reverse_lazy('crm:deal_detail', kwargs={'pk': deal.pk})),
            'color': '#2ecc71' if deal.stage == 'WON' else '#00d2ff',  # Зеленый если успех, иначе синий
            'className': 'fc-event-glass'  # Наш класс для стиля
        })

        # 2. ЗАДАЧИ (Теперь добавляем их)
    tasks = Task.objects.filter(assignee=user)
    for task in tasks:
        # Цвет зависит от статуса: Серый если готово, Желтый если ждет
        color = '#6c757d' if task.status == 'COMPLETED' else '#f1c40f'

        events.append({
            'title': f"📌 {task.title}",
            'start': task.due_date.strftime('%Y-%m-%d'),  # Берем только дату
            'url': str(reverse_lazy('crm:deal_detail', kwargs={'pk': task.deal.pk})),  # Ведем на сделку
            'color': color,
            'className': 'fc-event-glass'
        })

    return JsonResponse(events, safe=False)


# Список всех задач (To do List)
class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'crm/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 10

    def get_queryset(self):
        # Показываем задачи только текущего менеджера, сначала срочные
        return Task.objects.filter(assignee=self.request.user).order_by('due_date')

# СОЗДАНИЕ ЗАДАЧИ (Привязана к сделке)
class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    template_name = 'crm/task_form.html'
    fields = ['title', 'description', 'due_date', 'status']

    def form_valid(self, form):
        # Получаем сделку из URL (deal_pk)
        deal = get_object_or_404(Deal, pk=self.kwargs['deal_pk'])
        form.instance.deal = deal
        form.instance.assignee = self.request.user # Назначаем на себя
        return super().form_valid(form)

    def get_success_url(self):
        # После создания возвращаемся обратно в сделку
        return reverse_lazy('crm:deal_detail', kwargs={'pk': self.object.deal.pk})

# РЕДАКТИРОВАНИЕ ЗАДАЧИ
class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    template_name = 'crm/task_form.html'
    fields = ['title', 'description', 'due_date', 'status']

    def get_success_url(self):
        return reverse_lazy('crm:deal_detail', kwargs={'pk': self.object.deal.pk})


# УДАЛЕНИЕ ЗАДАЧИ
class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = 'crm/task_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('crm:deal_detail', kwargs={'pk': self.object.deal.pk})


class AboutView(TemplateView):
    template_name = 'about.html'


class LeaderboardView(LoginRequiredMixin, Templateview):
    template_name = 'crm/leaderboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Берем всех пользователей и считаем сумму их УСПЕШНЫХ сделок
        leaders = User.objects.annotate(
            total_sales=Sum('deals__amount', filter=Q(deals__stage='WON'))
        ).order_by('-total_sales')  # Сортируем: у кого больше, тот выше

        # Очищаем от тех, у кого 0 продаж (или None), если хочешь
        # leaders = [l for l in leaders if l.total_sales]

        # Разделяем: Топ-3 отдельно, остальные отдельно
        context['top_leaders'] = leaders[:3]
        context['other_leaders'] = leaders[3:]

        return context


class MotivationView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/motivation.html'


class VisionView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/vision.html'


class LabView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/lab.html'