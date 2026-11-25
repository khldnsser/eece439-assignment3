from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import ModelForm
from .models import Budget, Expense


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class ProfileForm(ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class CreateExpenseForm(ModelForm):
    class Meta:
        model = Expense
        fields = ['ExpenseTitle', 'Amount', 'Category', 'Date']
        widgets = {'Date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}


class BudgetForm(ModelForm):
    class Meta:
        model = Budget
        fields = ['Amount']
        labels = {'Amount': 'Monthly budget'}


class ExpenseFilterForm(forms.Form):
    Category = forms.ChoiceField(choices=[('', 'All categories')] + Expense.CATEGORIES, required=False)
    StartDate = forms.DateField(label='From date', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    EndDate = forms.DateField(label='To date', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    MinAmount = forms.DecimalField(label='Minimum amount', required=False, min_value=0, max_digits=10, decimal_places=2)
    MaxAmount = forms.DecimalField(label='Maximum amount', required=False, min_value=0, max_digits=10, decimal_places=2)

    def clean(self):
        data = super().clean()
        start = data.get('StartDate')
        end = data.get('EndDate')
        minimum = data.get('MinAmount')
        maximum = data.get('MaxAmount')
        if start and end and start > end:
            self.add_error('EndDate', 'To date must be on or after from date.')
        if minimum is not None and maximum is not None and minimum > maximum:
            self.add_error('MaxAmount', 'Maximum amount must be at least the minimum amount.')
        return data
