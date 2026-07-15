"""AI feature views — credit risk, collection intelligence, settings."""
import json
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from .models import AISettings
from shops.models import Shop


def _extract_json(raw):
    """Extract JSON object or array from AI response, tolerating surrounding text."""
    text = raw.strip()
    # Strip markdown code fences
    text = re.sub(r'```[a-z]*\n?', '', text).strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find first JSON array [...] or object {...}
    for start_char, end_char in (('[', ']'), ('{', '}')):
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    raise json.JSONDecodeError('No valid JSON found', text, 0)


@login_required
def ai_settings(request):
    """Admin-only AI settings page."""
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')

    settings_obj = AISettings.get_settings()

    if request.method == 'POST':
        settings_obj.is_enabled = request.POST.get('is_enabled') == 'on'
        settings_obj.credit_risk_enabled = request.POST.get('credit_risk_enabled') == 'on'
        settings_obj.collection_intelligence_enabled = (
            request.POST.get('collection_intelligence_enabled') == 'on'
        )
        api_key = request.POST.get('api_key', '').strip()
        if api_key:
            settings_obj.api_key = api_key
        settings_obj.api_base_url = request.POST.get(
            'api_base_url', 'https://openrouter.ai/api/v1'
        ).strip()
        settings_obj.model_name = request.POST.get(
            'model_name', 'google/gemini-2.0-flash-exp:free'
        ).strip()
        settings_obj.save()
        messages.success(request, 'AI settings saved.')
        return redirect('sales:ai_settings')

    return render(request, 'sales/ai_settings.html', {'ai_settings': settings_obj})


@login_required
def ai_test_connection(request):
    """AJAX: test the AI API connection."""
    if request.user.user_type not in ('admin', 'office'):
        return JsonResponse({'ok': False, 'error': 'Access denied'}, status=403)

    settings_obj = AISettings.get_settings()
    if not settings_obj.api_key:
        return JsonResponse({'ok': False, 'error': 'No API key configured'})

    try:
        from .ai_utils import call_ai
        reply = call_ai('Say "OK" in exactly one word.', settings_obj)
        return JsonResponse({'ok': True, 'reply': reply})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
def ai_credit_risk(request, shop_id):
    """AJAX: return credit risk assessment for a shop."""
    settings_obj = AISettings.get_settings()
    if not settings_obj.is_enabled or not settings_obj.credit_risk_enabled:
        return JsonResponse({'enabled': False})

    if not settings_obj.api_key:
        return JsonResponse({'enabled': False, 'error': 'AI not configured'})

    shop = get_object_or_404(Shop, pk=shop_id, is_active=True)

    try:
        from .ai_utils import call_ai, get_credit_risk_data
        data, prompt = get_credit_risk_data(shop)
        raw = call_ai(prompt, settings_obj)
        result = _extract_json(raw)
        result['enabled'] = True
        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({
            'enabled': True,
            'risk_level': 'UNKNOWN',
            'reason': 'Could not parse AI response.',
            'recommended_action': 'Review manually.',
        })
    except Exception as e:
        return JsonResponse({'enabled': True, 'error': str(e)}, status=500)


@login_required
def ai_collection_intelligence(request):
    """AJAX: return prioritized shop list for collection visits."""
    if request.user.user_type not in ('admin', 'office'):
        return JsonResponse({'error': 'Access denied'}, status=403)

    settings_obj = AISettings.get_settings()
    if not settings_obj.is_enabled or not settings_obj.collection_intelligence_enabled:
        return JsonResponse({'enabled': False})

    if not settings_obj.api_key:
        return JsonResponse({'enabled': False, 'error': 'AI not configured'})

    # Get shops that have actual unsettled bills (don't rely on shop.current_balance field)
    from sales.models import Bill
    from django.db.models import Sum
    shop_ids_with_debt = Bill.objects.filter(
        bill_status='confirmed',
        settlement_status__in=['unsettled', 'partial_settled'],
        balance_amount__gt=0,
    ).values_list('shop_id', flat=True).distinct()
    shops_with_balance = Shop.objects.filter(pk__in=shop_ids_with_debt, is_active=True)

    try:
        from .ai_utils import call_ai, get_collection_data
        shop_rows, prompt = get_collection_data(shops_with_balance)

        if not prompt:
            return JsonResponse({'enabled': True, 'shops': [], 'message': 'No outstanding balances found.'})

        raw = call_ai(prompt, settings_obj)
        result = _extract_json(raw)
        return JsonResponse({'enabled': True, 'shops': result})
    except json.JSONDecodeError:
        return JsonResponse({'enabled': True, 'error': 'Could not parse AI response.'}, status=500)
    except Exception as e:
        return JsonResponse({'enabled': True, 'error': str(e)}, status=500)
