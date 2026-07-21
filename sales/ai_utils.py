"""AI utility functions — supports Gemini Interactions API, generateContent, and OpenAI-compatible APIs."""
import json
import urllib.request
import urllib.error
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


def _is_gemini(base_url):
    return 'generativelanguage.googleapis.com' in base_url and '/openai' not in base_url


def _is_interactions_api(base_url):
    """Gemini v1 uses the new Interactions API; v1beta uses generateContent."""
    return _is_gemini(base_url) and base_url.rstrip('/').endswith('/v1')


def call_ai(prompt, settings, max_tokens=4000):
    """Send a prompt to the configured AI API and return the response text."""
    base_url = settings.api_base_url.rstrip('/')

    if _is_interactions_api(base_url):
        # New Google Gemini Interactions API (v1, recommended for auth keys)
        url = f'{base_url}/interactions'
        payload = json.dumps({
            'model': f'models/{settings.model_name}',
            'input': prompt,
        }).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': settings.api_key,
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return (data.get('output_text') or
                    data['candidates'][0]['content']['parts'][0]['text']).strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'AI API error {e.code}: {body[:300]}')
        except Exception as e:
            raise RuntimeError(f'AI call failed: {e}')

    elif _is_gemini(base_url):
        # Native Google Gemini generateContent API (v1beta)
        url = f'{base_url}/models/{settings.model_name}:generateContent'
        payload = json.dumps({
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'maxOutputTokens': max_tokens, 'temperature': 0.3},
        }).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': settings.api_key,
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'AI API error {e.code}: {body[:300]}')
        except Exception as e:
            raise RuntimeError(f'AI call failed: {e}')
    else:
        # OpenAI-compatible API (OpenRouter, OpenAI, etc.)
        url = base_url + '/chat/completions'
        payload = json.dumps({
            'model': settings.model_name,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': 0.3,
        }).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {settings.api_key}',
                'HTTP-Referer': 'https://zergo.app',
                'X-Title': 'Zergo Distributors',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return data['choices'][0]['message']['content'].strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'AI API error {e.code}: {body[:300]}')
        except Exception as e:
            raise RuntimeError(f'AI call failed: {e}')


def get_credit_risk_data(shop):
    """Collect credit risk metrics for a shop and return a dict + prompt."""
    from payments.models import SalesAccountSettlement, BadDebtWriteOff
    from sales.models import Bill

    now = timezone.now()
    today = now.date()
    days_90 = now - timedelta(days=90)
    days_30 = today - timedelta(days=30)
    days_60 = today - timedelta(days=60)

    confirmed_bills = Bill.objects.filter(shop=shop, bill_status='confirmed')

    # Total outstanding
    total_outstanding = confirmed_bills.filter(
        settlement_status__in=['unsettled', 'partial_settled']
    ).aggregate(s=models_sum('balance_amount'))['s'] or Decimal('0')

    # Credit utilization
    credit_limit = shop.credit_limit or Decimal('0')
    credit_util_pct = (
        float(total_outstanding / credit_limit * 100) if credit_limit > 0 else None
    )

    # Bounced cheques last 90 days
    bounced_cheques = SalesAccountSettlement.objects.filter(
        shop=shop,
        settlement_method='cheque',
        settlement_status='bounced',
        settlement_date__gte=days_90,
    ).count()

    # Overdue bills
    overdue_30 = confirmed_bills.filter(
        settlement_status__in=['unsettled', 'partial_settled'],
        bill_date__date__lte=days_30,
    ).count()
    overdue_60 = confirmed_bills.filter(
        settlement_status__in=['unsettled', 'partial_settled'],
        bill_date__date__lte=days_60,
    ).count()

    # Last payment date
    last_payment = SalesAccountSettlement.objects.filter(
        shop=shop,
        settlement_status='completed',
    ).order_by('-settlement_date').first()
    last_payment_date = last_payment.settlement_date.date() if last_payment else None
    days_since_payment = (today - last_payment_date).days if last_payment_date else None

    # Write-offs
    write_offs = BadDebtWriteOff.objects.filter(
        shop=shop, approval_status='approved'
    ).count()

    # Cancelled settlements last 90 days
    cancelled_settlements = SalesAccountSettlement.objects.filter(
        shop=shop,
        settlement_status='cancelled',
        settlement_date__gte=days_90,
    ).count()

    data = {
        'shop_name': shop.shop_name,
        'total_outstanding': float(total_outstanding),
        'credit_limit': float(credit_limit),
        'credit_util_pct': credit_util_pct,
        'bounced_cheques_90d': bounced_cheques,
        'overdue_30d_bills': overdue_30,
        'overdue_60d_bills': overdue_60,
        'days_since_last_payment': days_since_payment,
        'write_offs': write_offs,
        'cancelled_settlements_90d': cancelled_settlements,
    }

    credit_util_str = (
        f"{credit_util_pct:.1f}% of Rs. {float(credit_limit):,.0f} limit"
        if credit_util_pct is not None
        else 'No credit limit set'
    )
    payment_str = (
        f"{days_since_payment} days ago" if days_since_payment is not None else 'Never'
    )

    prompt = f"""You are a credit risk analyst for a Sri Lankan distribution company.
Analyze this shop's credit risk and respond ONLY with valid JSON.

Shop: {shop.shop_name}
Outstanding balance: Rs. {float(total_outstanding):,.2f}
Credit utilization: {credit_util_str}
Bounced cheques (last 90 days): {bounced_cheques}
Bills overdue 30+ days: {overdue_30}
Bills overdue 60+ days: {overdue_60}
Last payment: {payment_str}
Write-offs (approved): {write_offs}
Cancelled settlements (last 90 days): {cancelled_settlements}

Respond ONLY with this JSON structure (no markdown, no extra text):
{{"risk_level": "LOW|MEDIUM|HIGH|CRITICAL", "reason": "one concise sentence", "recommended_action": "one actionable instruction"}}"""

    return data, prompt


def get_collection_data(shops_qs):
    """Collect data for all shops and build a collection intelligence prompt."""
    from payments.models import SalesAccountSettlement
    from sales.models import Bill

    now = timezone.now()
    today = now.date()
    days_90 = now - timedelta(days=90)

    shop_rows = []
    for shop in shops_qs[:50]:  # cap at 50 to keep prompt manageable
        outstanding = Bill.objects.filter(
            shop=shop,
            bill_status='confirmed',
            settlement_status__in=['unsettled', 'partial_settled'],
        ).aggregate(s=models_sum('balance_amount'))['s'] or Decimal('0')

        if outstanding <= 0:
            continue

        last_payment = SalesAccountSettlement.objects.filter(
            shop=shop, settlement_status='completed'
        ).order_by('-settlement_date').first()
        days_since = (
            (today - last_payment.settlement_date.date()).days
            if last_payment else 999
        )

        oldest_bill = Bill.objects.filter(
            shop=shop,
            bill_status='confirmed',
            settlement_status__in=['unsettled', 'partial_settled'],
        ).order_by('bill_date').first()
        oldest_days = (
            (today - oldest_bill.bill_date.date()).days if oldest_bill else 0
        )

        pending_cheques = SalesAccountSettlement.objects.filter(
            shop=shop,
            settlement_method='cheque',
            settlement_status='pending',
        ).count()

        bounced = SalesAccountSettlement.objects.filter(
            shop=shop,
            settlement_method='cheque',
            settlement_status='bounced',
            settlement_date__gte=days_90,
        ).count()

        shop_rows.append({
            'name': shop.shop_name,
            'outstanding': float(outstanding),
            'days_since_payment': days_since,
            'oldest_bill_days': oldest_days,
            'pending_cheques': pending_cheques,
            'bounced_90d': bounced,
        })

    if not shop_rows:
        return [], None

    rows_text = '\n'.join(
        f"- {r['name']}: outstanding Rs. {r['outstanding']:,.0f}, "
        f"last payment {r['days_since_payment']}d ago, oldest bill {r['oldest_bill_days']}d, "
        f"pending cheques {r['pending_cheques']}, bounced 90d {r['bounced_90d']}"
        for r in shop_rows
    )

    prompt = f"""You are a collection intelligence assistant for a Sri Lankan distribution company.
Prioritize which shops to visit for payment collection today.

Shop data:
{rows_text}

Respond ONLY with valid JSON — an array of objects, sorted by priority (most urgent first):
[{{"shop_name": "...", "priority": "URGENT|HIGH|MEDIUM", "reason": "one sentence", "suggested_action": "one actionable step"}}]
Include ALL shops from the list. No markdown, no extra text."""

    return shop_rows, prompt


# Alias so we don't import django ORM Sum inside loops
def models_sum(field):
    from django.db.models import Sum
    return Sum(field)
