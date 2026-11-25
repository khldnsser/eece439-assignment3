from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Expense(models.Model):
    CATEGORIES = [
        ('Food', 'Food'),
        ('Transport', 'Transport'),
        ('Bills', 'Bills'),
        ('Shopping', 'Shopping'),
        ('Entertainment', 'Entertainment'),
        ('Other', 'Other'),
    ]

    ExpenseID = models.AutoField(primary_key=True)
    User = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ExpenseTitle = models.CharField('Title', max_length=100)
    Amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    Category = models.CharField(max_length=20, choices=CATEGORIES)
    Date = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ['-Date', '-ExpenseID']

    def __str__(self):
        return self.ExpenseTitle

    def clean(self):
        if not self.User_id or self.Amount is None or self.Date is None:
            return
        month = self.Date.replace(day=1)
        budget = Budget.objects.filter(User_id=self.User_id, Month=month).first()
        if budget is None:
            return
        spent = Expense.objects.filter(
            User_id=self.User_id, Date__year=month.year, Date__month=month.month
        ).exclude(pk=self.pk).aggregate(total=models.Sum('Amount'))['total'] or Decimal('0.00')
        if spent + self.Amount > budget.Amount:
            raise ValidationError({'Amount': 'This expense exceeds the budget of %.2f for %s. Remaining: %.2f.' % (
                budget.Amount, month.strftime('%B %Y'), budget.Amount - spent
            )})


class Budget(models.Model):
    BudgetID = models.AutoField(primary_key=True)
    User = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    Month = models.DateField()
    Amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['User', 'Month'], name='unique_budget_per_user_month')]

    def __str__(self):
        return self.User.username + ' ' + self.Month.strftime('%Y-%m')

    def clean(self):
        if not self.User_id or self.Amount is None or self.Month is None:
            return
        self.Month = self.Month.replace(day=1)
        spent = Expense.objects.filter(
            User_id=self.User_id, Date__year=self.Month.year, Date__month=self.Month.month
        ).aggregate(total=models.Sum('Amount'))['total'] or Decimal('0.00')
        if self.Amount < spent:
            raise ValidationError({'Amount': 'The budget cannot be less than the %.2f already spent in %s.' % (
                spent, self.Month.strftime('%B %Y')
            )})
