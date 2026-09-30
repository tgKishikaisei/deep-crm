from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_GET
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView

from core.middleware import allow_eval_csp
from users.models import User

from .access import clients_for, deals_for, is_crm_admin, tasks_for
from .filters import ClientFilter
from .models import Client, Deal, Task
from .tasks import send_congrats_email


def dashboard_cache_key(user_id) -> str:
    return f"dashboard_stats_{user_id}"


class HomeView(TemplateView):
    template_name = 'home.html'


# Миксин для проверки, является ли пользователь администратором.
# Не-админу отвечаем 404, а не 403: не подтверждаем, что такой раздел существует.
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_crm_admin(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise Http404


class DealClientFieldMixin:
    """В выпадающем списке клиентов — только клиенты текущего менеджера.

    Иначе менеджер мог бы привязать свою сделку к чужому клиенту и увидеть
    его данные на странице сделки.
    """

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['client'].queryset = clients_for(self.request.user)
        return form


class DealListView(LoginRequiredMixin, ListView):
    """Список сделок: админ видит все, менеджер — только свои."""
    template_name = 'crm/deal_list.html'
    context_object_name = 'deals'
    paginate_by = 10

    def get_queryset(self):
        return deals_for(self.request.user)


class DealDetailView(LoginRequiredMixin, DetailView):
    """Детальное представление сделки: чужая сделка → 404."""
    template_name = 'crm/deal_detail.html'
    context_object_name = 'deal'

    def get_queryset(self):
        return deals_for(self.request.user)


class DealCreateView(LoginRequiredMixin, DealClientFieldMixin, CreateView):
    """Создание сделки: менеджером автоматически становится текущий пользователь."""
    model = Deal
    template_name = 'crm/deal_form.html'
    fields = ['client', 'title', 'amount', 'stage']
    success_url = reverse_lazy('crm:deal_list')

    def form_valid(self, form):
        form.instance.manager = self.request.user
        return super().form_valid(form)


class DealUpdateView(LoginRequiredMixin, DealClientFieldMixin, UpdateView):
    """Редактирование сделки: менеджер может редактировать только свои сделки."""
    template_name = 'crm/deal_form.html'
    fields = ['client', 'title', 'amount', 'stage']
    success_url = reverse_lazy('crm:deal_list')

    def get_queryset(self):
        return deals_for(self.request.user)

    def form_valid(self, form):
        was_won = Deal.objects.filter(pk=form.instance.pk, stage=Deal.Stage.WON).exists()
        response = super().form_valid(form)

        # Письмо уходит только при переходе в WON и только после коммита транзакции.
        if form.instance.stage == Deal.Stage.WON and not was_won:
            email, title = form.instance.client.email, form.instance.title
            transaction.on_commit(lambda: send_congrats_email.delay(email, title))

        return response


class DealDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Удаление сделки — только администратор."""
    model = Deal
    template_name = 'crm/deal_confirm_delete.html'
    success_url = reverse_lazy('crm:deal_list')


class ClientListView(LoginRequiredMixin, ListView):
    template_name = 'crm/client_list.html'
    context_object_name = 'clients'
    paginate_by = 10

    def get_queryset(self):
        queryset = clients_for(self.request.user).select_related('manager')
        # self.filterset нужен get_context_data, чтобы отрисовать форму фильтра.
        self.filterset = ClientFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        return context


class ClientDetailView(LoginRequiredMixin, DetailView):
    template_name = 'crm/client_detail.html'
    context_object_name = 'client'

    def get_queryset(self):
        return clients_for(self.request.user)


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    template_name = 'crm/client_form.html'
    fields = ['company_name', 'contact_person', 'email', 'phone']
    success_url = reverse_lazy('crm:client_list')

    def form_valid(self, form):
        form.instance.manager = self.request.user
        return super().form_valid(form)


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'crm/client_form.html'
    fields = ['company_name', 'contact_person', 'email', 'phone']
    success_url = reverse_lazy('crm:client_list')

    def get_queryset(self):
        return clients_for(self.request.user)


class ClientDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Удаление клиента — только администратор."""
    model = Client
    template_name = 'crm/client_confirm_delete.html'
    success_url = reverse_lazy('crm:client_list')


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Кэш на пользователя (Manager1 не увидит данные Manager2).
        # Сбрасывается сигналами при изменении сделок, клиентов и задач (crm/signals.py).
        cache_key = dashboard_cache_key(user.id)
        cached_data = cache.get(cache_key)
        if cached_data:
            context.update(cached_data)
            return context

        user_deals = Deal.objects.filter(manager=user)
        user_clients = Client.objects.filter(manager=user)
        data = {}

        active_deals = user_deals.filter(stage__in=[Deal.Stage.NEW, Deal.Stage.IN_PROGRESS])
        data['active_deals_count'] = active_deals.count()
        data['active_deals_total_amount'] = active_deals.aggregate(total=Sum('amount'))['total'] or 0

        one_month_ago = timezone.now() - timedelta(days=30)
        data['new_clients_count'] = user_clients.filter(created_at__gte=one_month_ago).count()

        # list(): в кэш должен попасть результат, а не «ленивый» QuerySet.
        data['latest_deals'] = list(user_deals.select_related('client').order_by('-created_at')[:5])

        # Данные графиков передаются в шаблон через json_script (без |safe).
        stages = [Deal.Stage.NEW, Deal.Stage.IN_PROGRESS, Deal.Stage.WON, Deal.Stage.LOST]
        data['chart_stages_data'] = [user_deals.filter(stage=s).count() for s in stages]

        last_deals = list(user_deals.order_by('-created_at')[:7])[::-1]
        data['chart_titles'] = [deal.title for deal in last_deals]
        data['chart_amounts'] = [float(deal.amount) for deal in last_deals]

        data['upcoming_tasks'] = list(
            Task.objects.filter(assignee=user, status=Task.Status.PENDING).order_by('due_date')[:5]
        )

        cache.set(cache_key, data, 300)
        context.update(data)
        return context


class KanbanView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/kanban.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Личная доска: только сделки текущего пользователя.
        deals = Deal.objects.filter(manager=self.request.user).select_related('client')
        context['deals_new'] = deals.filter(stage=Deal.Stage.NEW)
        context['deals_progress'] = deals.filter(stage=Deal.Stage.IN_PROGRESS)
        context['deals_won'] = deals.filter(stage=Deal.Stage.WON)
        context['deals_lost'] = deals.filter(stage=Deal.Stage.LOST)
        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/profile.html'


class GlobalSearchView(LoginRequiredMixin, View):
    """Поиск по клиентам и сделкам — только в пределах данных пользователя."""

    def get(self, request):
        query = request.GET.get('q', '').strip()[:100]
        results = []

        if len(query) >= 2:
            clients = clients_for(request.user).filter(
                Q(company_name__icontains=query)
                | Q(contact_person__icontains=query)
                | Q(email__icontains=query)
            )[:5]
            for client in clients:
                results.append({
                    'type': 'client',
                    'title': client.company_name,
                    'desc': str(client.contact_person),
                    'url': reverse('crm:client_detail', kwargs={'pk': client.pk}),
                })

            for deal in deals_for(request.user).filter(title__icontains=query)[:5]:
                results.append({
                    'type': 'deal',
                    'title': deal.title,
                    'desc': f"{deal.amount} ₽",
                    'url': reverse('crm:deal_detail', kwargs={'pk': deal.pk}),
                })

        return JsonResponse({'results': results})


class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/calendar.html'


@require_GET
@login_required
def calendar_events(request):
    """События календаря (сделки и задачи), только для вошедших пользователей."""
    user = request.user
    events = []

    for deal in Deal.objects.filter(manager=user).only('pk', 'title', 'created_at', 'stage'):
        events.append({
            'title': f"💰 {deal.title}",
            'start': deal.created_at.strftime('%Y-%m-%d'),
            'url': reverse('crm:deal_detail', kwargs={'pk': deal.pk}),
            'color': '#2ecc71' if deal.stage == Deal.Stage.WON else '#00d2ff',
            'className': 'fc-event-glass',
        })

    for task in Task.objects.filter(assignee=user).only('title', 'due_date', 'status', 'deal_id'):
        events.append({
            'title': f"📌 {task.title}",
            'start': task.due_date.strftime('%Y-%m-%d'),
            'url': reverse('crm:deal_detail', kwargs={'pk': task.deal_id}),
            'color': '#6c757d' if task.status == Task.Status.COMPLETED else '#f1c40f',
            'className': 'fc-event-glass',
        })

    return JsonResponse(events, safe=False)


class TaskListView(LoginRequiredMixin, ListView):
    """Список задач пользователя, сначала срочные."""
    template_name = 'crm/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 10

    def get_queryset(self):
        return tasks_for(self.request.user).order_by('due_date')


class TaskCreateView(LoginRequiredMixin, CreateView):
    """Создание задачи в сделке.

    Сделка из URL проверяется на владельца: чужую сделку нельзя дополнить задачей
    и потом открыть через календарь.
    """
    model = Task
    template_name = 'crm/task_form.html'
    fields = ['title', 'description', 'due_date', 'status']

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.deal = get_object_or_404(deals_for(request.user), pk=kwargs['deal_pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.deal = self.deal
        form.instance.assignee = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('crm:deal_detail', kwargs={'pk': self.object.deal_id})


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование задачи: queryset ограничен задачами пользователя."""
    template_name = 'crm/task_form.html'
    fields = ['title', 'description', 'due_date', 'status']

    def get_queryset(self):
        return tasks_for(self.request.user)

    def get_success_url(self):
        return reverse('crm:deal_detail', kwargs={'pk': self.object.deal_id})


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление задачи: queryset ограничен задачами пользователя."""
    template_name = 'crm/task_confirm_delete.html'

    def get_queryset(self):
        return tasks_for(self.request.user)

    def get_success_url(self):
        return reverse('crm:deal_detail', kwargs={'pk': self.object.deal_id})


class AboutView(TemplateView):
    template_name = 'about.html'


class LeaderboardView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/leaderboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Сумма УСПЕШНЫХ сделок по активным пользователям.
        leaders = User.objects.filter(is_active=True).annotate(
            total_sales=Sum('deals__amount', filter=Q(deals__stage=Deal.Stage.WON))
        ).order_by(F('total_sales').desc(nulls_last=True), 'username')
        context['top_leaders'] = leaders[:3]
        context['other_leaders'] = leaders[3:]
        return context


class MotivationView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/motivation.html'


class VisionView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/vision.html'


class LabView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/lab.html'

    def get(self, request, *args, **kwargs):
        # spline-viewer вычисляет код через eval — ослабляем CSP только на этой странице.
        return allow_eval_csp(super().get(request, *args, **kwargs))
