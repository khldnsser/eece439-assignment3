from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Budget, Expense


class ExpenseTrackerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', password='StrongPass439!')
        self.other_user = User.objects.create_user(username='other', password='OtherPass439!')
        self.today = timezone.localdate()
        self.expense = Expense.objects.create(
            User=self.user, ExpenseTitle='Lunch', Amount='12.50', Category='Food', Date=self.today
        )
        self.other_expense = Expense.objects.create(
            User=self.other_user, ExpenseTitle='Private bill', Amount='900.00', Category='Bills', Date=self.today
        )
        self.client.force_login(self.user)

    def test_pages_require_login(self):
        self.client.logout()
        urls = [
            reverse('index'), reverse('profile'), reverse('budget'), reverse('add_expense'), reverse('display_expense'),
            reverse('update_expense', args=[self.expense.pk]),
            reverse('delete_expense', args=[self.expense.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), reverse('login') + '?next=' + url)

    def test_registration_creates_account_and_logs_in(self):
        self.client.logout()
        response = self.client.post(reverse('register'), {
            'username': 'newstudent', 'email': 'student@example.com',
            'password1': 'NewStrongPass439!', 'password2': 'NewStrongPass439!',
        })
        self.assertRedirects(response, reverse('index'))
        user = User.objects.get(username='newstudent')
        self.assertTrue(user.check_password('NewStrongPass439!'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_registration_rejects_duplicate_username(self):
        self.client.logout()
        response = self.client.post(reverse('register'), {
            'username': 'student', 'password1': 'NewStrongPass439!', 'password2': 'NewStrongPass439!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('username', response.context['form'].errors)
        self.assertEqual(User.objects.count(), 2)

    def test_login_and_post_logout(self):
        self.client.logout()
        invalid = self.client.post(reverse('login'), {'username': 'student', 'password': 'wrong'})
        self.assertTrue(invalid.context['form'].errors)
        response = self.client.post(reverse('login'), {'username': 'student', 'password': 'StrongPass439!'})
        self.assertRedirects(response, reverse('index'))
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_profile_updates_only_current_user(self):
        response = self.client.post(reverse('profile'), {
            'first_name': 'New', 'last_name': 'Name', 'email': 'new@example.com',
            'id': self.other_user.pk, 'is_staff': True,
        })
        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.other_user.refresh_from_db()
        self.assertEqual(self.user.email, 'new@example.com')
        self.assertFalse(self.user.is_staff)
        self.assertEqual(self.other_user.email, '')

    def test_add_expense_assigns_current_user(self):
        response = self.client.post(reverse('add_expense'), {
            'ExpenseTitle': 'Bus', 'Amount': '3.25', 'Category': 'Transport',
            'Date': self.today.isoformat(), 'User': self.other_user.pk,
        })
        self.assertRedirects(response, reverse('display_expense'))
        expense = Expense.objects.get(ExpenseTitle='Bus')
        self.assertEqual(expense.User, self.user)
        self.assertEqual(expense.Amount, Decimal('3.25'))

    def test_invalid_expenses_are_not_saved(self):
        for changes in [
            {'Amount': '0'}, {'Amount': '-1'}, {'Amount': '1.234'},
            {'Category': 'Unknown'}, {'Date': 'invalid'}, {'ExpenseTitle': ''},
        ]:
            with self.subTest(changes=changes):
                data = {
                    'ExpenseTitle': 'Invalid expense', 'Amount': '5.00',
                    'Category': 'Other', 'Date': self.today.isoformat(),
                }
                data.update(changes)
                response = self.client.post(reverse('add_expense'), data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
        self.assertEqual(Expense.objects.count(), 2)

    def test_edit_expense(self):
        response = self.client.post(reverse('update_expense', args=[self.expense.pk]), {
            'ExpenseTitle': 'Dinner', 'Amount': '20.00', 'Category': 'Food',
            'Date': self.today.isoformat(),
        })
        self.assertRedirects(response, reverse('display_expense'))
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.ExpenseTitle, 'Dinner')
        self.assertEqual(self.expense.Amount, Decimal('20.00'))

    def test_delete_requires_confirmation_post(self):
        url = reverse('delete_expense', args=[self.expense.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Expense.objects.filter(pk=self.expense.pk).exists())
        self.assertRedirects(self.client.post(url), reverse('display_expense'))
        self.assertFalse(Expense.objects.filter(pk=self.expense.pk).exists())

    def test_cannot_edit_or_delete_another_users_expense(self):
        for name in ['update_expense', 'delete_expense']:
            url = reverse(name, args=[self.other_expense.pk])
            with self.subTest(view=name):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {'Amount': '1.00'}).status_code, 404)
        self.other_expense.refresh_from_db()
        self.assertEqual(self.other_expense.Amount, Decimal('900.00'))

    def test_history_and_dashboard_hide_other_users_expenses(self):
        for name in ['display_expense', 'index']:
            with self.subTest(view=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, 'Lunch')
                self.assertNotContains(response, 'Private bill')

    def test_filters_work_individually_and_together(self):
        Expense.objects.create(
            User=self.user, ExpenseTitle='Bus', Amount='3.00', Category='Transport',
            Date=self.today - timedelta(days=1),
        )
        filters = [
            {'Category': 'Food'},
            {'StartDate': self.today.isoformat(), 'EndDate': self.today.isoformat()},
            {'MinAmount': '12.50', 'MaxAmount': '12.50'},
            {
                'Category': 'Food', 'StartDate': self.today.isoformat(),
                'EndDate': self.today.isoformat(), 'MinAmount': '12.50', 'MaxAmount': '12.50',
            },
        ]
        for data in filters:
            with self.subTest(filters=data):
                response = self.client.get(reverse('display_expense'), data)
                self.assertQuerySetEqual(response.context['expenses'], [self.expense])

    def test_invalid_filters_show_errors(self):
        for data in [
            {'StartDate': '2026-10-20', 'EndDate': '2026-10-01'},
            {'MinAmount': '20', 'MaxAmount': '10'},
            {'Category': 'Unknown'}, {'StartDate': 'bad-date'}, {'MinAmount': '-1'},
        ]:
            with self.subTest(filters=data):
                response = self.client.get(reverse('display_expense'), data)
                self.assertTrue(response.context['form'].errors)
                self.assertQuerySetEqual(response.context['expenses'], [])

    def test_dashboard_totals_and_monthly_summary(self):
        previous_month = self.today.replace(day=1) - timedelta(days=1)
        Expense.objects.create(
            User=self.user, ExpenseTitle='Movie', Amount='7.25', Category='Entertainment', Date=self.today
        )
        Expense.objects.create(
            User=self.user, ExpenseTitle='Previous bill', Amount='25.00', Category='Bills', Date=previous_month
        )
        response = self.client.get(reverse('index'))
        self.assertEqual(response.context['total'], Decimal('19.75'))
        self.assertEqual(list(response.context['category_totals']), [
            {'Category': 'Entertainment', 'total': Decimal('7.25')},
            {'Category': 'Food', 'total': Decimal('12.50')},
        ])
        summary = list(response.context['monthly_summary'])
        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0]['month'], self.today.replace(day=1))
        self.assertEqual(summary[0]['total'], Decimal('19.75'))
        self.assertEqual(summary[0]['count'], 2)
        self.assertEqual(summary[1]['total'], Decimal('25.00'))

    def test_recent_expenses_are_limited_and_ordered(self):
        for day in range(1, 7):
            Expense.objects.create(
                User=self.user, ExpenseTitle='Expense ' + str(day), Amount='1.00', Category='Other',
                Date=self.today - timedelta(days=day),
            )
        response = self.client.get(reverse('index'))
        recent = list(response.context['recent_expenses'])
        self.assertEqual(len(recent), 5)
        self.assertEqual(recent[0], self.expense)
        self.assertEqual(recent[-1].Date, self.today - timedelta(days=4))

    def test_empty_account_pages(self):
        self.client.force_login(self.other_user)
        self.other_expense.delete()
        response = self.client.get(reverse('index'))
        self.assertEqual(response.context['total'], Decimal('0.00'))
        self.assertContains(response, 'No expenses yet.')
        self.assertContains(self.client.get(reverse('display_expense')), 'No expenses found.')

    def test_forms_and_edit_date_render(self):
        for name in ['profile', 'budget', 'add_expense']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        response = self.client.get(reverse('update_expense', args=[self.expense.pk]))
        self.assertContains(response, 'value="' + self.today.isoformat() + '"')
        self.client.logout()
        for name in ['login', 'register']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_csrf_protects_expense_changes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(reverse('delete_expense', args=[self.expense.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Expense.objects.filter(pk=self.expense.pk).exists())

    def test_set_and_update_monthly_budget(self):
        month = self.today.replace(day=1)
        response = self.client.post(reverse('budget'), {'Amount': '100.00', 'User': self.other_user.pk})
        self.assertRedirects(response, reverse('index'))
        budget = Budget.objects.get(User=self.user)
        self.assertEqual(budget.Month, month)
        self.assertEqual(budget.Amount, Decimal('100.00'))
        self.client.post(reverse('budget'), {'Amount': '50.00'})
        self.assertEqual(Budget.objects.filter(User=self.user).count(), 1)
        budget.refresh_from_db()
        self.assertEqual(budget.Amount, Decimal('50.00'))
        self.assertContains(self.client.get(reverse('budget')), 'value="50.00"')

    def test_invalid_budget_is_not_saved(self):
        for amount in ['0', '-5', '1.234', '']:
            with self.subTest(amount=amount):
                response = self.client.post(reverse('budget'), {'Amount': amount})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
        self.assertFalse(Budget.objects.exists())

    def test_dashboard_without_budget(self):
        response = self.client.get(reverse('index'))
        self.assertIsNone(response.context['budget'])
        self.assertContains(response, 'No budget set for this month.')

    def test_dashboard_within_budget(self):
        Budget.objects.create(User=self.user, Month=self.today.replace(day=1), Amount='12.50')
        Budget.objects.create(User=self.other_user, Month=self.today.replace(day=1), Amount='1.00')
        response = self.client.get(reverse('index'))
        self.assertEqual(response.context['remaining'], Decimal('0.00'))
        self.assertContains(response, 'Within budget: 0.00 remaining.')
        self.assertNotContains(response, 'Budget exceeded')

    def test_dashboard_exceeded_budget(self):
        Budget.objects.create(User=self.user, Month=self.today.replace(day=1), Amount='10.00')
        response = self.client.get(reverse('index'))
        self.assertEqual(response.context['exceeded_by'], Decimal('2.50'))
        self.assertContains(response, 'Budget exceeded by 2.50.')

    def test_previous_month_budget_does_not_apply(self):
        previous_month = (self.today.replace(day=1) - timedelta(days=1)).replace(day=1)
        Budget.objects.create(User=self.user, Month=previous_month, Amount='1.00')
        response = self.client.get(reverse('index'))
        self.assertIsNone(response.context['budget'])

    def expense_data(self, **changes):
        data = {'ExpenseTitle': 'Snack', 'Amount': '5.00', 'Category': 'Food', 'Date': self.today.isoformat()}
        data.update(changes)
        return data

    def test_add_expense_up_to_budget_is_allowed(self):
        Budget.objects.create(User=self.user, Month=self.today.replace(day=1), Amount='20.00')
        response = self.client.post(reverse('add_expense'), self.expense_data(Amount='7.50'))
        self.assertRedirects(response, reverse('display_expense'))
        self.assertTrue(Expense.objects.filter(ExpenseTitle='Snack').exists())

    def test_add_expense_over_budget_is_rejected(self):
        Budget.objects.create(User=self.user, Month=self.today.replace(day=1), Amount='20.00')
        response = self.client.post(reverse('add_expense'), self.expense_data(Amount='7.51'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Remaining: 7.50', response.context['form'].errors['Amount'][0])
        self.assertFalse(Expense.objects.filter(ExpenseTitle='Snack').exists())

    def test_budget_only_limits_its_own_user_and_month(self):
        Budget.objects.create(User=self.other_user, Month=self.today.replace(day=1), Amount='1.00')
        previous_month = self.today.replace(day=1) - timedelta(days=1)
        Budget.objects.create(User=self.user, Month=previous_month.replace(day=1), Amount='1.00')
        self.client.post(reverse('add_expense'), self.expense_data(Amount='50.00'))
        self.assertTrue(Expense.objects.filter(ExpenseTitle='Snack').exists())

    def test_edit_expense_over_budget_is_rejected(self):
        Budget.objects.create(User=self.user, Month=self.today.replace(day=1), Amount='20.00')
        url = reverse('update_expense', args=[self.expense.pk])
        self.assertRedirects(self.client.post(url, self.expense_data(Amount='20.00')), reverse('display_expense'))
        response = self.client.post(url, self.expense_data(Amount='20.01'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Amount', response.context['form'].errors)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.Amount, Decimal('20.00'))

    def test_moving_expense_into_budgeted_month_is_rejected(self):
        previous_month = self.today.replace(day=1) - timedelta(days=1)
        old = Expense.objects.create(
            User=self.user, ExpenseTitle='Old', Amount='10.00', Category='Bills', Date=previous_month
        )
        Budget.objects.create(User=self.user, Month=self.today.replace(day=1), Amount='15.00')
        response = self.client.post(reverse('update_expense', args=[old.pk]), self.expense_data(Amount='10.00'))
        self.assertEqual(response.status_code, 200)
        old.refresh_from_db()
        self.assertEqual(old.Date, previous_month)

    def test_budget_below_current_spending_is_rejected(self):
        response = self.client.post(reverse('budget'), {'Amount': '12.49'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('12.50 already spent', response.context['form'].errors['Amount'][0])
        self.assertFalse(Budget.objects.exists())
        self.assertRedirects(self.client.post(reverse('budget'), {'Amount': '12.50'}), reverse('index'))

    def test_admin_enforces_budget(self):
        admin = User.objects.create_superuser(username='admin', password='AdminPass439!')
        self.client.force_login(admin)
        Budget.objects.create(User=self.user, Month=self.today.replace(day=1), Amount='20.00')
        response = self.client.post(reverse('admin:app1_expense_add'), dict(self.expense_data(Amount='8.00'), User=self.user.pk))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Expense.objects.filter(ExpenseTitle='Snack').exists())
