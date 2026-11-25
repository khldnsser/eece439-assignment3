from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import BudgetForm, CreateExpenseForm, ExpenseFilterForm, ProfileForm, RegisterForm
from .models import Budget, Expense


def register(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'profile.html', {'form': form})


@login_required
def index(request):
    expenses = Expense.objects.filter(User=request.user)
    today = timezone.localdate()
    month_expenses = expenses.filter(Date__year=today.year, Date__month=today.month)
    total = month_expenses.aggregate(total=Sum('Amount'))['total'] or Decimal('0.00')
    category_totals = month_expenses.values('Category').annotate(total=Sum('Amount')).order_by('Category')
    monthly_summary = expenses.annotate(month=TruncMonth('Date')).values('month').annotate(
        total=Sum('Amount'), count=Count('ExpenseID')
    ).order_by('-month')
    budget = Budget.objects.filter(User=request.user, Month=today.replace(day=1)).first()
    return render(request, 'index.html', {
        'month': today,
        'total': total,
        'budget': budget,
        'remaining': budget.Amount - total if budget else None,
        'exceeded_by': total - budget.Amount if budget else None,
        'category_totals': category_totals,
        'recent_expenses': expenses[:5],
        'monthly_summary': monthly_summary,
    })


@login_required
def budget(request):
    month = timezone.localdate().replace(day=1)
    budget = Budget.objects.filter(User=request.user, Month=month).first()
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget or Budget(User=request.user, Month=month))
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget saved.')
            return redirect('index')
    else:
        form = BudgetForm(instance=budget)
    return render(request, 'budget.html', {'form': form, 'month': month})


@login_required
def add_expense(request):
    if request.method == 'POST':
        form = CreateExpenseForm(request.POST, instance=Expense(User=request.user))
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense added.')
            return redirect('display_expense')
    else:
        form = CreateExpenseForm()
    return render(request, 'add_expense.html', {'form': form})


@login_required
def display_expense(request):
    expenses = Expense.objects.filter(User=request.user)
    form = ExpenseFilterForm(request.GET)
    if form.is_valid():
        data = form.cleaned_data
        if data['Category']:
            expenses = expenses.filter(Category=data['Category'])
        if data['StartDate']:
            expenses = expenses.filter(Date__gte=data['StartDate'])
        if data['EndDate']:
            expenses = expenses.filter(Date__lte=data['EndDate'])
        if data['MinAmount'] is not None:
            expenses = expenses.filter(Amount__gte=data['MinAmount'])
        if data['MaxAmount'] is not None:
            expenses = expenses.filter(Amount__lte=data['MaxAmount'])
    else:
        expenses = expenses.none()
    return render(request, 'display_expense.html', {'form': form, 'expenses': expenses})


@login_required
def update_expense(request, ExpenseID):
    expense = get_object_or_404(Expense, ExpenseID=ExpenseID, User=request.user)
    if request.method == 'POST':
        form = CreateExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated.')
            return redirect('display_expense')
    else:
        form = CreateExpenseForm(instance=expense)
    return render(request, 'update_expense.html', {'form': form})


@login_required
def delete_expense(request, ExpenseID):
    expense = get_object_or_404(Expense, ExpenseID=ExpenseID, User=request.user)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted.')
        return redirect('display_expense')
    return render(request, 'delete_expense.html', {'expense': expense})
