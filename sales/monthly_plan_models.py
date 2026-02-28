"""
Monthly Plan Models
Created: February 20, 2026

Models for tracking monthly sales planning per user.
Each user can create a plan for a month with daily route assignments and targets.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import calendar

User = get_user_model()


class MonthlyPlan(models.Model):
    """
    A sales rep's monthly plan - one per user per month.
    Contains targets for R/D (cases), P/C (productive calls/bills),
    N/O (new outlets), and Purchase (from company).
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='monthly_plans'
    )

    year = models.PositiveIntegerField(
        help_text="Plan year (e.g., 2026)"
    )

    month = models.PositiveIntegerField(
        help_text="Plan month (1-12)"
    )

    area = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Area/territory for this plan"
    )

    notes = models.TextField(
        blank=True,
        default='',
        help_text="Optional notes about this month's plan"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'monthly_plans'
        unique_together = [['user', 'year', 'month']]
        ordering = ['-year', '-month']
        verbose_name = 'Monthly Plan'
        verbose_name_plural = 'Monthly Plans'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_month_display()} {self.year}"

    def get_month_display(self):
        return calendar.month_name[self.month]

    @property
    def days_in_month(self):
        return calendar.monthrange(self.year, self.month)[1]

    def get_total_targets(self):
        from django.db.models import Sum
        totals = self.days.aggregate(
            total_rd=Sum('target_rd'),
            total_pc=Sum('target_pc'),
            total_no=Sum('target_no'),
            total_purchase=Sum('target_purchase'),
        )
        return {
            'rd': totals['total_rd'] or 0,
            'pc': totals['total_pc'] or 0,
            'no': totals['total_no'] or 0,
            'purchase': totals['total_purchase'] or 0,
        }


class MonthlyPlanDay(models.Model):
    """
    One day's plan within a monthly plan.
    Stores route and daily targets. Achievements are computed at view time.
    """

    plan = models.ForeignKey(
        MonthlyPlan,
        on_delete=models.CASCADE,
        related_name='days'
    )

    day = models.PositiveIntegerField(
        help_text="Day of month (1-31)"
    )

    route = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Route for this day, or 'Off' for a day off"
    )

    is_off = models.BooleanField(
        default=False,
        help_text="Whether this is a day off"
    )

    target_rd = models.IntegerField(
        default=0,
        help_text="R/D target (cases)"
    )

    target_pc = models.IntegerField(
        default=0,
        help_text="P/C target (productive calls / bill count)"
    )

    target_no = models.IntegerField(
        default=0,
        help_text="N/O target (new outlets)"
    )

    target_purchase = models.IntegerField(
        default=0,
        help_text="Purchase target (from company)"
    )

    class Meta:
        db_table = 'monthly_plan_days'
        unique_together = [['plan', 'day']]
        ordering = ['day']
        verbose_name = 'Monthly Plan Day'
        verbose_name_plural = 'Monthly Plan Days'

    def __str__(self):
        if self.is_off:
            return f"Day {self.day}: Off"
        return f"Day {self.day}: {self.route} (R/D:{self.target_rd}, P/C:{self.target_pc})"
