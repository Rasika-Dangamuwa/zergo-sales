from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
from .models import (
    Product, Company, Category, StockCount, StockMovement, ProductStatusAdjustment,
    Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem
)
from sales.models import BillItem, Bill


@login_required
def product_list(request):
    """List all active products"""
    products = Product.objects.filter(is_active=True).select_related('company', 'category')
    
    # Filter by company if provided
    company_id = request.GET.get('company')
    if company_id:
        products = products.filter(company_id=company_id)
    
    # Filter by category if provided
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            models.Q(product_name__icontains=search_query) | 
            models.Q(product_code__icontains=search_query)
        )
    
    companies = Company.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'products': products,
        'companies': companies,
        'categories': categories,
        'total_products': products.count()
    }
    return render(request, 'products/product_list.html', context)


@login_required
def product_detail(request, pk):
    """Product detail view"""
    product = get_object_or_404(Product.objects.select_related('company'), pk=pk)
    stock_movements = product.stock_movements.all()[:20]
    
    context = {
        'product': product,
        'stock_movements': stock_movements
    }
    return render(request, 'products/product_detail.html', context)


@login_required
def company_list(request):
    """List all companies"""
    companies = Company.objects.filter(is_active=True)
    
    context = {
        'companies': companies
    }
    return render(request, 'products/company_list.html', context)


@login_required
def stock_alert(request):
    """Show products with low stock"""
    from django.db.models import F, ExpressionWrapper, IntegerField
    
    low_stock_products = Product.objects.filter(
        is_active=True,
        quantity_in_stock__lte=models.F('minimum_stock_level')
    ).annotate(
        shortage=ExpressionWrapper(
            F('minimum_stock_level') - F('quantity_in_stock'),
            output_field=IntegerField()
        )
    ).select_related('company').order_by('display_order')
    
    context = {
        'low_stock_products': low_stock_products
    }
    return render(request, 'products/stock_alert.html', context)


@login_required
def stock_inventory_pdf(request):
    """Generate a professional PDF of current stock inventory"""

    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfgen import canvas
    from business.models import DistributorProfile
    from products.utils import get_size_ordering

    business = DistributorProfile.get_active()
    products = Product.objects.filter(is_active=True).select_related('company', 'category').annotate(
        size_num=get_size_ordering('size')
    ).order_by('size_num', 'marked_price', 'display_order', 'product_name')

    # Page number canvas
    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor('#7f8c8d'))
                self.drawCentredString(A4[0] / 2, 8*mm, f"Page {self._pageNumber} of {num_pages}")
                biz_name = business.business_name if business else ''
                self.drawRightString(A4[0] - 15*mm, 8*mm, biz_name)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

    buffer = io.BytesIO()
    now = timezone.localtime(timezone.now())
    pdf_title = f"Stock Inventory - {now.strftime('%Y-%m-%d')}"

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=12*mm, leftMargin=12*mm,
        topMargin=12*mm, bottomMargin=15*mm,
        title=pdf_title
    )

    elements = []
    styles = getSampleStyleSheet()

    # Header
    header_style = ParagraphStyle('Header', parent=styles['Heading1'], fontSize=18,
        textColor=colors.HexColor('#2c3e50'), alignment=TA_CENTER, spaceAfter=2, fontName='Helvetica-Bold')
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10,
        textColor=colors.HexColor('#7f8c8d'), alignment=TA_CENTER, spaceAfter=4)

    if business:
        elements.append(Paragraph(business.business_name, header_style))
        full_address = business.get_full_address()
        if full_address:
            elements.append(Paragraph(full_address, sub_style))
        if business.primary_phone:
            elements.append(Paragraph(f"Tel: {business.primary_phone}", sub_style))

    elements.append(Spacer(1, 3*mm))
    title_style = ParagraphStyle('Title', parent=styles['Heading2'], fontSize=14,
        textColor=colors.HexColor('#8e44ad'), alignment=TA_CENTER, fontName='Helvetica-Bold')
    elements.append(Paragraph("STOCK INVENTORY REPORT", title_style))
    elements.append(Paragraph(f"Generated: {now.strftime('%B %d, %Y at %I:%M %p')}", sub_style))
    elements.append(Spacer(1, 5*mm))

    # Build table
    col_widths = [8*mm, 60*mm, 18*mm, 22*mm, 22*mm, 22*mm, 25*mm]
    right_style = ParagraphStyle('R', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT)
    cell_style = ParagraphStyle('C', parent=styles['Normal'], fontSize=8)
    hdr_style = ParagraphStyle('H', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=colors.white)
    hdr_right = ParagraphStyle('HR', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_RIGHT)

    header_row = [
        Paragraph('#', hdr_style),
        Paragraph('Product', hdr_style),
        Paragraph('Size', hdr_style),
        Paragraph('MRP', hdr_right),
        Paragraph('Shop Price', hdr_right),
        Paragraph('Stock (Btl)', hdr_right),
        Paragraph('Stock Value', hdr_right),
    ]
    data = [header_row]

    total_bottles = 0
    total_value = Decimal('0.00')
    current_size = None
    row_num = 0

    for product in products:
        # Size group separator
        if product.size != current_size:
            if current_size is not None:
                # Add subtotal separator row
                pass
            current_size = product.size

        row_num += 1
        stock = product.quantity_in_stock
        mrp = product.marked_price
        sp = product.shop_price
        value = stock * sp
        total_bottles += stock
        total_value += value

        data.append([
            Paragraph(str(row_num), cell_style),
            Paragraph(product.product_name, cell_style),
            Paragraph(product.size, cell_style),
            Paragraph(f"Rs.{mrp:,.2f}", right_style),
            Paragraph(f"Rs.{sp:,.2f}", right_style),
            Paragraph(str(stock), right_style),
            Paragraph(f"Rs.{value:,.2f}", right_style),
        ])

    # Total row
    total_label = ParagraphStyle('TL', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    total_val = ParagraphStyle('TV', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT)
    data.append([
        '', Paragraph('TOTAL', total_label), '', '', '',
        Paragraph(str(total_bottles), total_val),
        Paragraph(f"Rs.{total_value:,.2f}", total_val),
    ])

    table = Table(data, colWidths=col_widths, repeatRows=1)

    # Styling
    style_cmds = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8e44ad')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        # Total row
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0e6f6')),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#8e44ad')),
    ]

    # Alternate row colors
    for i in range(1, len(data) - 1):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8f9fa')))

    # Highlight low stock rows
    for i, product in enumerate(products, start=1):
        if product.quantity_in_stock <= product.minimum_stock_level:
            style_cmds.append(('BACKGROUND', (4, i), (4, i), colors.HexColor('#ffe0e0')))

    table.setStyle(TableStyle(style_cmds))
    elements.append(table)

    # Summary box
    elements.append(Spacer(1, 8*mm))
    summary_data = [
        [Paragraph('<b>Summary</b>', ParagraphStyle('SH', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold')), '', ''],
        [Paragraph('Total Products:', cell_style), Paragraph(str(row_num), right_style), ''],
        [Paragraph('Total Stock (Bottles):', cell_style), Paragraph(f"{total_bottles:,}", right_style), ''],
        [Paragraph('Total Stock Value (Shop Price):', cell_style), Paragraph(f"Rs.{total_value:,.2f}", right_style), ''],
    ]
    summary_table = Table(summary_data, colWidths=[50*mm, 40*mm, 90*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#8e44ad')),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('BOX', (0, 0), (1, -1), 1, colors.HexColor('#8e44ad')),
        ('INNERGRID', (0, 0), (1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)

    doc.build(elements, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    filename = f"Stock_Inventory_{now.strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def stock_count(request):
    """Physical stock count - simple and clean implementation"""
    # Only admin and distributor can perform stock counts
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Access denied. Only admin and distributor can perform stock counts.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        saved_count = 0
        update_stock = request.POST.get('update_stock') == 'on'
        
        with transaction.atomic():
            # Get all products for validation
            products = Product.objects.filter(is_active=True)
            
            for product in products:
                # Get the physical count for this product
                count_key = f'count_{product.id}'
                physical_count_value = request.POST.get(count_key, '').strip()
                
                # Skip if no value entered
                if not physical_count_value:
                    continue
                
                # Validate it's a number
                try:
                    physical_count = int(physical_count_value)
                except ValueError:
                    continue
                
                # Get system stock
                system_stock = product.quantity_in_stock
                variance = physical_count - system_stock
                
                # Get adjustment reason if provided
                reason = request.POST.get(f'reason_{product.id}', '').strip()
                
                # Create stock count record
                StockCount.objects.create(
                    product=product,
                    system_stock=system_stock,
                    physical_count=physical_count,
                    variance=variance,
                    adjustment_reason=reason,
                    counted_by=request.user,
                    stock_updated=update_stock
                )
                
                # Update stock if requested
                if update_stock and variance != 0:
                    product.quantity_in_stock = physical_count
                    product.save()
                    
                    # Create stock movement record
                    cost_per_unit = product.cost_after_foc if product.cost_after_foc else Decimal('0')
                    ref_number = f'STKCNT-{timezone.now().strftime("%Y%m%d-%H%M%S")}'
                    StockMovement.objects.create(
                        product=product,
                        movement_type='adjustment',
                        quantity=variance,
                        previous_quantity=system_stock,
                        new_quantity=physical_count,
                        reference_number=ref_number,
                        notes=reason or 'Stock count adjustment',
                        created_by=request.user,
                        unit_cost=cost_per_unit,
                        total_cost=cost_per_unit * abs(variance),
                    )
                    
                    # Sync FIFO layers with stock count adjustment
                    from products.models import FIFOCostLayer
                    if variance > 0:
                        # Found extra stock — create a new FIFO layer
                        FIFOCostLayer.create_layer(
                            product=product,
                            qty=variance,
                            unit_cost=cost_per_unit,
                            source='adjustment',
                            reference=ref_number,
                        )
                    elif variance < 0:
                        # Missing stock — consume from FIFO layers
                        FIFOCostLayer.consume_fifo(product, abs(variance))
                
                saved_count += 1
        
        # Show result message
        if saved_count > 0:
            msg = f'Stock count saved for {saved_count} product(s)'
            if update_stock:
                msg += ' and stock updated'
            messages.success(request, msg)
        else:
            messages.warning(request, 'No products were counted. Please enter physical count values.')
        
        return redirect('products:stock_count')
    
    # GET request - show the form
    company_id = request.GET.get('company')
    
    if company_id:
        products = Product.objects.filter(
            company_id=company_id, 
            is_active=True
        ).select_related('company').order_by('display_order', 'product_name')
    else:
        products = Product.objects.filter(
            is_active=True
        ).select_related('company').order_by('display_order', 'product_name')
    
    companies = Company.objects.filter(is_active=True)
    
    context = {
        'products': products,
        'companies': companies,
        'selected_company_id': int(company_id) if company_id else None,
    }
    return render(request, 'products/stock_count.html', context)


@login_required
def stock_count_history(request):
    """View stock count history with filters"""
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Access denied. Only admin and distributor can view stock count history.')
        return redirect('dashboard:home')
    
    # Get filters
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    product_id = request.GET.get('product')
    
    # Build query
    counts = StockCount.objects.select_related('product', 'counted_by').order_by('-count_date')
    
    if from_date:
        counts = counts.filter(count_date__date__gte=from_date)
    if to_date:
        counts = counts.filter(count_date__date__lte=to_date)
    if product_id:
        counts = counts.filter(product_id=product_id)
    
    # Get products for filter dropdown
    products = Product.objects.filter(is_active=True).order_by('product_name')
    
    context = {
        'counts': counts,
        'products': products,
        'from_date': from_date,
        'to_date': to_date,
        'selected_product_id': int(product_id) if product_id else None,
    }
    return render(request, 'products/stock_count_history.html', context)


@login_required
def stock_count_detail(request, count_id):
    """View details of a specific stock count"""
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Access denied. Only admin and distributor can view stock count details.')
        return redirect('dashboard:home')
    
    count = get_object_or_404(StockCount.objects.select_related('product', 'counted_by'), id=count_id)
    
    # Get related stock movement if exists
    stock_movement = None
    if count.stock_updated:
        stock_movement = StockMovement.objects.filter(
            reference_number__contains=f'STKCNT-'
        ).filter(product=count.product).order_by('-created_at').first()
    
    # Calculate pack and loose breakdown
    packs = 0
    loose = 0
    if count.product.bottles_per_pack > 0:
        packs = count.physical_count // count.product.bottles_per_pack
        loose = count.physical_count % count.product.bottles_per_pack
    
    context = {
        'count': count,
        'stock_movement': stock_movement,
        'packs': packs,
        'loose': loose,
    }
    return render(request, 'products/stock_count_detail.html', context)


@login_required
def stock_count_delete(request, count_id):
    """Delete a stock count record"""
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Access denied. Only admin and distributor can delete stock counts.')
        return redirect('dashboard:home')
    
    count = get_object_or_404(StockCount, id=count_id)
    
    if request.method == 'POST':
        product_name = count.product.product_name
        count_date = count.count_date
        
        # Delete the stock count record
        count.delete()
        messages.success(request, f'Stock count for {product_name} on {count_date.strftime("%Y-%m-%d %H:%M")} has been deleted.')
        return redirect('products:stock_count_history')
    
    context = {'count': count}
    return render(request, 'products/stock_count_delete.html', context)


@login_required
def opening_balance(request):
    """Enter/update opening stock balance for products"""
    # Restrict access to admin and distributor only
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Access denied. Only admin and distributor can manage opening balances.')
        return redirect('dashboard:home')

    from products.models import FIFOCostLayer

    if request.method == 'POST':
        saved_count = 0
        balance_date = request.POST.get('balance_date', '')

        # Use the user-selected date, fall back to today
        if balance_date:
            try:
                ob_date = datetime.strptime(balance_date, '%Y-%m-%d').strftime('%Y%m%d')
            except ValueError:
                ob_date = timezone.now().strftime('%Y%m%d')
        else:
            ob_date = timezone.now().strftime('%Y%m%d')

        ob_reference = f'OB-{ob_date}'

        with transaction.atomic():
            for key, value in request.POST.items():
                if key.startswith('opening_stock_'):
                    product_id = int(key.replace('opening_stock_', ''))
                    opening_stock = value.strip()

                    # Skip empty fields
                    if not opening_stock:
                        continue

                    try:
                        new_ob_qty = int(opening_stock)
                    except ValueError:
                        continue

                    if new_ob_qty < 0:
                        continue

                    product = Product.objects.get(id=product_id)
                    cost_per_unit = product.cost_after_foc if product.cost_after_foc else Decimal('0')

                    # ── Gather existing OB state ──
                    # Sum the INTENDED OB qty (use the max from any existing movement)
                    existing_ob_movements = StockMovement.objects.filter(
                        product=product,
                        movement_type='opening_balance',
                    )
                    old_ob_qty = 0
                    if existing_ob_movements.exists():
                        from django.db.models import Max
                        old_ob_qty = existing_ob_movements.aggregate(m=Max('quantity'))['m'] or 0

                    # Skip if nothing changed
                    if new_ob_qty == old_ob_qty:
                        # Still clean up any duplicate OB records (layers & movements)
                        # Keep exactly one movement and one layer
                        ob_mvs = list(existing_ob_movements.order_by('created_at').values_list('id', flat=True))
                        if len(ob_mvs) > 1:
                            StockMovement.objects.filter(id__in=ob_mvs[1:]).delete()
                        ob_layers = list(FIFOCostLayer.objects.filter(
                            product=product, layer_source='opening_balance'
                        ).order_by('created_at').values_list('id', flat=True))
                        if len(ob_layers) > 1:
                            FIFOCostLayer.objects.filter(id__in=ob_layers[1:]).delete()
                        continue

                    # ── Calculate delta to adjust current stock ──
                    delta = new_ob_qty - old_ob_qty
                    previous_qty = product.quantity_in_stock
                    new_stock = previous_qty + delta

                    product.quantity_in_stock = new_stock
                    product.save()

                    # ── Clean up ALL old OB records ──
                    # Calculate how much of the OB was already consumed (from FIFO layers)
                    old_ob_layers = FIFOCostLayer.objects.filter(
                        product=product,
                        layer_source='opening_balance',
                    )
                    total_consumed = 0
                    for layer in old_ob_layers:
                        total_consumed += (layer.original_quantity - layer.remaining_quantity)

                    # Delete ALL old OB movements and FIFO layers
                    existing_ob_movements.delete()
                    old_ob_layers.delete()

                    # ── Create exactly ONE new OB movement ──
                    StockMovement.objects.create(
                        product=product,
                        movement_type='opening_balance',
                        quantity=new_ob_qty,
                        previous_quantity=previous_qty,
                        new_quantity=new_stock,
                        reference_number=ob_reference,
                        notes=f'Opening balance {"updated" if old_ob_qty > 0 else "entry"}',
                        created_by=request.user,
                        unit_cost=cost_per_unit,
                        total_cost=cost_per_unit * new_ob_qty,
                    )

                    # ── Create exactly ONE new OB FIFO layer ──
                    # Preserve consumed quantity from the old layers
                    new_remaining = max(0, new_ob_qty - total_consumed)
                    if new_ob_qty > 0:
                        FIFOCostLayer.objects.create(
                            product=product,
                            unit_cost=cost_per_unit,
                            original_quantity=new_ob_qty,
                            remaining_quantity=new_remaining,
                            layer_source='opening_balance',
                            reference_number=ob_reference,
                            is_exhausted=(new_remaining <= 0),
                        )

                    saved_count += 1

        if saved_count > 0:
            messages.success(request, f'Opening balance saved for {saved_count} product(s)')
        else:
            messages.info(request, 'No changes detected.')
        return redirect('products:opening_balance')

    # GET request
    company_id = request.GET.get('company')
    company = Company.objects.get(id=company_id) if company_id else None

    # Get products
    if company:
        products = Product.objects.filter(company=company, is_active=True).select_related('company')
    else:
        products = Product.objects.filter(is_active=True).select_related('company')

    products = products.order_by('display_order', 'product_name')

    # Build a lookup of existing OB quantities per product
    ob_movements = StockMovement.objects.filter(
        movement_type='opening_balance',
        product__in=products,
    ).values('product_id').annotate(
        ob_qty=models.Max('quantity'),  # latest/highest — there should be only one per product
    )
    ob_lookup = {item['product_id']: item['ob_qty'] for item in ob_movements}

    # Annotate products with their OB qty for template use
    products = list(products)
    for p in products:
        p.ob_qty = ob_lookup.get(p.id, None)

    # Find the existing OB date (from any OB movement reference)
    existing_ob_date = ''
    first_ob = StockMovement.objects.filter(
        movement_type='opening_balance',
    ).order_by('created_at').first()
    if first_ob and first_ob.reference_number:
        # Parse date from ref like "OB-20251225"
        ref_date = first_ob.reference_number.replace('OB-', '')
        if len(ref_date) == 8 and ref_date.isdigit():
            existing_ob_date = f'{ref_date[:4]}-{ref_date[4:6]}-{ref_date[6:8]}'

    companies = Company.objects.filter(is_active=True)

    context = {
        'products': products,
        'companies': companies,
        'selected_company': company,
        'existing_ob_date': existing_ob_date,
    }
    return render(request, 'products/opening_balance.html', context)


@login_required
def product_status_adjustment(request):
    """Create status adjustment request (requires approval)
    
    Anyone can create requests - approval is required from admin/distributor.
    """
    
    if request.method == 'POST':
        import json
        from products.models import ProductStatusAdjustmentItem
        
        status_type = request.POST.get('status_type')
        reason = request.POST.get('reason', '').strip()
        reference_number = request.POST.get('reference_number', '').strip()
        stock_action = request.POST.get('stock_action', 'move_to_non_resaleable')
        items_json = request.POST.get('items', '[]')
        
        # Validation
        if not all([status_type, reason]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('products:product_status_adjustment')
        
        # Validate stock action based on status type
        if status_type in ['damaged', 'expired']:
            # Damaged/expired can ONLY use "Move to Non-Resaleable"
            if stock_action != 'move_to_non_resaleable':
                messages.error(request, 'Damaged and expired items can only use "Move to Non-Resaleable" action.')
                return redirect('products:product_status_adjustment')
        else:
            # Other status types CANNOT use "Move to Non-Resaleable"
            if stock_action == 'move_to_non_resaleable':
                messages.error(request, 'Only damaged and expired items can use "Move to Non-Resaleable" action.')
                return redirect('products:product_status_adjustment')
        
        # Parse items
        try:
            items = json.loads(items_json)
            if not items:
                messages.error(request, 'Please add at least one product to the adjustment.')
                return redirect('products:product_status_adjustment')
        except json.JSONDecodeError:
            messages.error(request, 'Invalid items data.')
            return redirect('products:product_status_adjustment')
        
        # Validate items
        validated_items = []
        for item in items:
            try:
                product_id = int(item.get('product_id'))
                quantity = int(item.get('quantity'))
                
                if quantity <= 0:
                    raise ValueError("Quantity must be positive")
                
                product = get_object_or_404(Product, id=product_id)
                
                # Check stock (only if not record_only)
                if stock_action != 'record_only' and product.quantity_in_stock < quantity:
                    messages.error(request, f'Insufficient resaleable stock for {product.product_name}. Available: {product.quantity_in_stock}')
                    return redirect('products:product_status_adjustment')
                
                validated_items.append({
                    'product': product,
                    'quantity': quantity
                })
            except (ValueError, TypeError):
                messages.error(request, f'Invalid quantity for product.')
                return redirect('products:product_status_adjustment')
        
        # Create pending adjustment
        adjustment = ProductStatusAdjustment.objects.create(
            status_type=status_type,
            reason=reason,
            reference_number=reference_number,
            stock_action=stock_action,
            approval_status='pending',
            stock_updated=False,
            adjusted_by=request.user
        )
        
        # Create adjustment items
        for item_data in validated_items:
            ProductStatusAdjustmentItem.objects.create(
                adjustment=adjustment,
                product=item_data['product'],
                quantity=item_data['quantity'],
                previous_resaleable=item_data['product'].quantity_in_stock,
                previous_non_resaleable=item_data['product'].non_resaleable_stock
            )
        
        messages.success(request, f'Adjustment {adjustment.adjustment_number} created with {len(validated_items)} items and pending manager approval.')
        return redirect('products:product_status_history')
    
    # GET request
    products = Product.objects.filter(is_active=True).select_related('company').order_by('display_order', 'product_name')
    companies = Company.objects.filter(is_active=True)
    
    context = {
        'products': products,
        'companies': companies,
        'status_choices': ProductStatusAdjustment.STATUS_CHOICES,
    }
    return render(request, 'products/product_status_adjustment.html', context)


@login_required
def product_status_history(request):
    """View history of product status adjustments
    
    Staff can see all adjustments, sales reps see only their own.
    """
    
    from datetime import timedelta
    from django.db.models import Sum, Count
    import pytz
    from django.conf import settings
    
    # Get timezone-aware today
    local_tz = pytz.timezone(settings.TIME_ZONE)
    today = timezone.now().astimezone(local_tz).date()
    
    # Date filter parameter
    date_filter = request.GET.get('date', 'all')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    product_id = request.GET.get('product')
    status_type = request.GET.get('status_type')
    approval_status = request.GET.get('approval_status')
    
    adjustments = ProductStatusAdjustment.objects.select_related('product', 'adjusted_by', 'approved_by').prefetch_related('items').order_by('-adjustment_date')
    
    # Sales reps see only their own adjustments
    if request.user.user_type == 'sales_rep':
        adjustments = adjustments.filter(adjusted_by=request.user)
    
    # Apply date filter shortcuts
    if date_filter == 'today':
        adjustments = adjustments.filter(adjustment_date__date=today)
    elif date_filter == 'yesterday':
        yesterday = today - timedelta(days=1)
        adjustments = adjustments.filter(adjustment_date__date=yesterday)
    elif date_filter == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        adjustments = adjustments.filter(adjustment_date__date__gte=start_of_week)
    elif date_filter == 'this_month':
        adjustments = adjustments.filter(adjustment_date__year=today.year, adjustment_date__month=today.month)
    elif date_filter == 'all':
        pass  # No date filtering
    
    # Custom date range
    if from_date:
        adjustments = adjustments.filter(adjustment_date__date__gte=from_date)
    if to_date:
        adjustments = adjustments.filter(adjustment_date__date__lte=to_date)
    if product_id:
        adjustments = adjustments.filter(product_id=product_id)
    if status_type:
        adjustments = adjustments.filter(status_type=status_type)
    if approval_status:
        adjustments = adjustments.filter(approval_status=approval_status)
    
    products = Product.objects.filter(is_active=True).order_by('product_name')
    
    # Calculate statistics
    total_adjustments = adjustments.count()
    pending_approvals = adjustments.filter(approval_status='pending').count()
    stock_updated_count = adjustments.filter(stock_updated=True).count()
    total_units = adjustments.aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    context = {
        'adjustments': adjustments,
        'products': products,
        'status_choices': ProductStatusAdjustment.STATUS_CHOICES,
        'date_filter': date_filter,
        'from_date': from_date,
        'to_date': to_date,
        'selected_product_id': int(product_id) if product_id else None,
        'selected_status_type': status_type,
        'selected_approval_status': approval_status,
        'total_adjustments': total_adjustments,
        'pending_approvals': pending_approvals,
        'stock_updated_count': stock_updated_count,
        'total_units': total_units,
    }
    return render(request, 'products/product_status_history.html', context)


@login_required
def product_status_detail(request, adjustment_id):
    """View details of a specific status adjustment
    
    Staff can view all adjustments, sales reps can view only their own.
    """
    
    adjustment = get_object_or_404(
        ProductStatusAdjustment.objects.select_related('product', 'adjusted_by', 'approved_by'),
        id=adjustment_id
    )
    
    # Sales reps can only view their own adjustments
    if request.user.user_type == 'sales_rep' and adjustment.adjusted_by != request.user:
        messages.error(request, 'You can only view your own status adjustments.')
        return redirect('products:product_status_history')
    
    # Get related stock movement if exists
    stock_movement = None
    if adjustment.stock_updated:
        stock_movement = StockMovement.objects.filter(
            reference_number=f'ADJ-{adjustment.id}'
        ).first()
    
    context = {
        'adjustment': adjustment,
        'stock_movement': stock_movement,
    }
    return render(request, 'products/product_status_detail.html', context)


@login_required
def product_status_delete(request, adjustment_id):
    """Delete a status adjustment record"""
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Access denied. Only admin and distributor can delete status adjustments.')
        return redirect('dashboard:home')
    
    adjustment = get_object_or_404(ProductStatusAdjustment, id=adjustment_id)
    
    if request.method == 'POST':
        adjustment_number = adjustment.adjustment_number
        status_type = adjustment.get_status_type_display()
        adjustment_date = adjustment.adjustment_date
        
        # Get descriptive name for deletion message
        if adjustment.product:
            description = f'{adjustment.product.product_name} ({status_type})'
        else:
            description = f'{adjustment.total_items} items ({status_type})'
        
        adjustment.delete()
        
        messages.success(
            request,
            f'Status adjustment {adjustment_number} for {description} on {adjustment_date.strftime("%Y-%m-%d %H:%M")} has been deleted.'
        )
        return redirect('products:product_status_history')
    
    context = {'adjustment': adjustment}
    return render(request, 'products/product_status_delete.html', context)


@login_required
def approve_status_adjustment(request, adjustment_id):
    """Approve status adjustment and update stock based on stock_action"""
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Only managers can approve adjustments.')
        return redirect('products:product_status_history')
    
    adjustment = get_object_or_404(ProductStatusAdjustment, id=adjustment_id)
    
    if adjustment.approval_status != 'pending':
        messages.warning(request, 'This adjustment has already been processed.')
        return redirect('products:product_status_detail', adjustment_id=adjustment_id)
    
    from django.utils import timezone
    from products.models import ProductStatusAdjustmentItem
    
    try:
        with transaction.atomic():
            # Get items (new multi-item or legacy single-item)
            items = adjustment.items.all() if hasattr(adjustment, 'items') and adjustment.items.exists() else None
            
            from products.models import FIFOCostLayer
            if items:
                # Multi-item adjustment
                total_processed = 0
                stock_changes = []
                
                for item in items:
                    product = item.product
                    previous_resaleable = product.quantity_in_stock
                    previous_non_resaleable = product.non_resaleable_stock
                    
                    if adjustment.stock_action == 'move_to_non_resaleable':
                        # Validate stock
                        if product.quantity_in_stock < item.quantity:
                            messages.error(request, f'Insufficient resaleable stock for {product.product_name}. Available: {product.quantity_in_stock}')
                            return redirect('products:product_status_detail', adjustment_id=adjustment_id)
                        
                        # Transfer stock
                        product.quantity_in_stock -= item.quantity
                        product.non_resaleable_stock += item.quantity
                        product.save()
                        
                        # Consume FIFO layers (resaleable stock leaving)
                        cost_per_unit = product.cost_after_foc if product.cost_after_foc else Decimal('0')
                        if item.quantity > 0:
                            avg_cost, _ = FIFOCostLayer.consume_fifo(product, item.quantity)
                            if avg_cost > 0:
                                cost_per_unit = avg_cost
                        
                        # Create movement OUT of resaleable
                        StockMovement.objects.create(
                            product=product,
                            movement_type='non_resaleable_in',
                            stock_type='resaleable',
                            quantity=-item.quantity,
                            previous_quantity=previous_resaleable,
                            new_quantity=product.quantity_in_stock,
                            reference_number=adjustment.adjustment_number,
                            notes=f'Moved to non-resaleable: {adjustment.get_status_type_display()} - {adjustment.reason}',
                            created_by=request.user,
                            unit_cost=cost_per_unit,
                            total_cost=cost_per_unit * item.quantity,
                        )
                        
                        # Create movement INTO non-resaleable
                        StockMovement.objects.create(
                            product=product,
                            movement_type='non_resaleable_in',
                            stock_type='non_resaleable',
                            quantity=item.quantity,
                            previous_quantity=previous_non_resaleable,
                            new_quantity=product.non_resaleable_stock,
                            reference_number=adjustment.adjustment_number,
                            notes=f'Received from resaleable: {adjustment.get_status_type_display()} - {adjustment.reason}',
                            created_by=request.user,
                            unit_cost=cost_per_unit,
                            total_cost=cost_per_unit * item.quantity,
                        )
                        
                        stock_changes.append(f'{product.product_name}: R{previous_resaleable}→{product.quantity_in_stock}, NR{previous_non_resaleable}→{product.non_resaleable_stock}')
                        
                    elif adjustment.stock_action == 'reduce_completely':
                        # Validate stock
                        if product.quantity_in_stock < item.quantity:
                            messages.error(request, f'Insufficient resaleable stock for {product.product_name}. Available: {product.quantity_in_stock}')
                            return redirect('products:product_status_detail', adjustment_id=adjustment_id)
                        
                        product.quantity_in_stock -= item.quantity
                        product.save()
                        
                        # Consume FIFO layers (stock written off)
                        cost_per_unit = product.cost_after_foc if product.cost_after_foc else Decimal('0')
                        if item.quantity > 0:
                            avg_cost, _ = FIFOCostLayer.consume_fifo(product, item.quantity)
                            if avg_cost > 0:
                                cost_per_unit = avg_cost
                        
                        # Create stock movement
                        StockMovement.objects.create(
                            product=product,
                            movement_type='status_adjustment',
                            stock_type='resaleable',
                            quantity=-item.quantity,
                            previous_quantity=previous_resaleable,
                            new_quantity=product.quantity_in_stock,
                            reference_number=adjustment.adjustment_number,
                            notes=f'{adjustment.get_status_type_display()}: {adjustment.reason}',
                            created_by=request.user,
                            unit_cost=cost_per_unit,
                            total_cost=cost_per_unit * item.quantity,
                        )
                        
                        stock_changes.append(f'{product.product_name}: {previous_resaleable}→{product.quantity_in_stock}')
                    
                    # Update item tracking
                    item.stock_updated = (adjustment.stock_action != 'record_only')
                    item.previous_resaleable = previous_resaleable
                    item.new_resaleable = product.quantity_in_stock
                    item.previous_non_resaleable = previous_non_resaleable
                    item.new_non_resaleable = product.non_resaleable_stock
                    item.save()
                    
                    total_processed += 1
                
                if adjustment.stock_action == 'record_only':
                    success_msg = f'Adjustment {adjustment.adjustment_number} approved (record only, no stock changes) for {total_processed} items.'
                else:
                    success_msg = f'Adjustment {adjustment.adjustment_number} approved for {total_processed} items. ' + '; '.join(stock_changes[:3])
                    if len(stock_changes) > 3:
                        success_msg += f' and {len(stock_changes) - 3} more...'
                        
            else:
                # Legacy single-item adjustment
                product = adjustment.product
                previous_resaleable = product.quantity_in_stock
                previous_non_resaleable = product.non_resaleable_stock
                cost_per_unit = product.cost_after_foc if product.cost_after_foc else Decimal('0')
                
                if adjustment.stock_action == 'move_to_non_resaleable':
                    if product.quantity_in_stock < adjustment.quantity:
                        messages.error(request, f'Insufficient resaleable stock. Available: {product.quantity_in_stock}')
                        return redirect('products:product_status_detail', adjustment_id=adjustment_id)
                    
                    product.quantity_in_stock -= adjustment.quantity
                    product.non_resaleable_stock += adjustment.quantity
                    product.save()
                    
                    # Consume FIFO layers (resaleable stock leaving)
                    if adjustment.quantity > 0:
                        avg_cost, _ = FIFOCostLayer.consume_fifo(product, adjustment.quantity)
                        if avg_cost > 0:
                            cost_per_unit = avg_cost
                    
                    StockMovement.objects.create(
                        product=product,
                        movement_type='non_resaleable_in',
                        stock_type='resaleable',
                        quantity=-adjustment.quantity,
                        previous_quantity=previous_resaleable,
                        new_quantity=product.quantity_in_stock,
                        reference_number=adjustment.adjustment_number,
                        notes=f'Moved to non-resaleable: {adjustment.get_status_type_display()} - {adjustment.reason}',
                        created_by=request.user,
                        unit_cost=cost_per_unit,
                        total_cost=cost_per_unit * adjustment.quantity,
                    )
                    
                    StockMovement.objects.create(
                        product=product,
                        movement_type='non_resaleable_in',
                        stock_type='non_resaleable',
                        quantity=adjustment.quantity,
                        previous_quantity=previous_non_resaleable,
                        new_quantity=product.non_resaleable_stock,
                        reference_number=adjustment.adjustment_number,
                        notes=f'Received from resaleable: {adjustment.get_status_type_display()} - {adjustment.reason}',
                        created_by=request.user,
                        unit_cost=cost_per_unit,
                        total_cost=cost_per_unit * adjustment.quantity,
                    )
                    
                    success_msg = f'Adjustment {adjustment.adjustment_number} approved. Moved {adjustment.quantity} units to non-resaleable stock. Resaleable: {previous_resaleable} → {product.quantity_in_stock}, Non-resaleable: {previous_non_resaleable} → {product.non_resaleable_stock}'
                    
                elif adjustment.stock_action == 'reduce_completely':
                    if product.quantity_in_stock < adjustment.quantity:
                        messages.error(request, f'Insufficient resaleable stock. Available: {product.quantity_in_stock}')
                        return redirect('products:product_status_detail', adjustment_id=adjustment_id)
                    
                    product.quantity_in_stock -= adjustment.quantity
                    product.save()
                    
                    # Consume FIFO layers (stock written off)
                    if adjustment.quantity > 0:
                        avg_cost, _ = FIFOCostLayer.consume_fifo(product, adjustment.quantity)
                        if avg_cost > 0:
                            cost_per_unit = avg_cost
                    
                    StockMovement.objects.create(
                        product=product,
                        movement_type='status_adjustment',
                        stock_type='resaleable',
                        quantity=-adjustment.quantity,
                        previous_quantity=previous_resaleable,
                        new_quantity=product.quantity_in_stock,
                        reference_number=adjustment.adjustment_number,
                        notes=f'{adjustment.get_status_type_display()}: {adjustment.reason}',
                        created_by=request.user,
                        unit_cost=cost_per_unit,
                        total_cost=cost_per_unit * adjustment.quantity,
                    )
                    
                    success_msg = f'Adjustment {adjustment.adjustment_number} approved. Stock reduced: {previous_resaleable} → {product.quantity_in_stock}'
                    
                else:  # record_only
                    success_msg = f'Adjustment {adjustment.adjustment_number} approved (record only, no stock changes).'
                
                adjustment.previous_stock = previous_resaleable
                adjustment.new_stock = product.quantity_in_stock
            
            # Update adjustment
            adjustment.approval_status = 'approved'
            adjustment.approved_by = request.user
            adjustment.approved_at = timezone.now()
            adjustment.stock_updated = (adjustment.stock_action != 'record_only')
            adjustment.save()
            
            messages.success(request, success_msg)
    except Exception as e:
        messages.error(request, f'Error approving adjustment: {str(e)}')
    
    return redirect('products:product_status_detail', adjustment_id=adjustment_id)


@login_required
def reject_status_adjustment(request, adjustment_id):
    """Reject status adjustment"""
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Only managers can reject adjustments.')
        return redirect('products:product_status_history')
    
    adjustment = get_object_or_404(ProductStatusAdjustment, id=adjustment_id)
    
    if adjustment.approval_status != 'pending':
        messages.warning(request, 'This adjustment has already been processed.')
        return redirect('products:product_status_detail', adjustment_id=adjustment_id)
    
    from django.utils import timezone
    
    adjustment.approval_status = 'rejected'
    adjustment.approved_by = request.user
    adjustment.approved_at = timezone.now()
    adjustment.save()
    
    messages.warning(request, f'Adjustment {adjustment.adjustment_number} rejected.')
    return redirect('products:product_status_detail', adjustment_id=adjustment_id)


@login_required
def non_resaleable_inventory_list(request):
    """List all products with non-resaleable stock"""
    if request.user.user_type == 'sales_rep':
        messages.error(request, 'Access denied. Only admin and distributor can view non-resaleable inventory.')
        return redirect('dashboard:home')
    
    # Get products with non-resaleable stock
    products_with_non_resaleable = Product.objects.filter(
        non_resaleable_stock__gt=0,
        is_active=True
    ).select_related('company').order_by('display_order', 'product_name')
    
    # Add calculated non_resaleable_value to each product
    for product in products_with_non_resaleable:
        product.non_resaleable_value = product.non_resaleable_stock * product.cost_after_foc
    
    # Calculate total non-resaleable value
    total_non_resaleable_qty = sum(p.non_resaleable_stock for p in products_with_non_resaleable)
    total_non_resaleable_value = sum(p.non_resaleable_value for p in products_with_non_resaleable)
    
    context = {
        'products': products_with_non_resaleable,
        'total_non_resaleable_qty': total_non_resaleable_qty,
        'total_non_resaleable_value': total_non_resaleable_value,
    }
    return render(request, 'products/non_resaleable_inventory.html', context)


@login_required
def dispose_non_resaleable_stock(request):
    """Dispose/write-off non-resaleable stock permanently"""
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied. Only admin and distributor can dispose non-resaleable stock.')
        return redirect('products:non_resaleable_inventory_list')
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 0))
        disposal_reason = request.POST.get('disposal_reason', '')
        
        if not product_id or quantity <= 0:
            messages.error(request, 'Invalid product or quantity.')
            return redirect('products:non_resaleable_inventory_list')
        
        product = get_object_or_404(Product, id=product_id)
        
        if product.non_resaleable_stock < quantity:
            messages.error(request, f'Cannot dispose {quantity} units. Only {product.non_resaleable_stock} non-resaleable units available.')
            return redirect('products:non_resaleable_inventory_list')
        
        try:
            with transaction.atomic():
                previous_non_resaleable = product.non_resaleable_stock
                product.non_resaleable_stock -= quantity
                product.save()
                
                # Generate disposal reference number: DISP-2026-0001
                from django.utils import timezone
                current_year = timezone.now().year
                prefix = f"DISP-{current_year}-"
                
                # Find last disposal for current year
                last_disposal = StockMovement.objects.filter(
                    movement_type='non_resaleable_out',
                    reference_number__startswith=prefix
                ).order_by('-reference_number').first()
                
                if last_disposal:
                    # Extract sequence number from last disposal
                    last_num = int(last_disposal.reference_number.split('-')[-1])
                    new_num = last_num + 1
                else:
                    # First disposal of the year
                    new_num = 1
                
                disposal_ref = f"{prefix}{new_num:04d}"  # Format: DISP-2026-0001
                
                # Create stock movement for disposal
                cost_per_unit = product.cost_after_foc if product.cost_after_foc else Decimal('0')
                StockMovement.objects.create(
                    product=product,
                    movement_type='non_resaleable_out',
                    stock_type='non_resaleable',
                    quantity=-quantity,
                    previous_quantity=previous_non_resaleable,
                    new_quantity=product.non_resaleable_stock,
                    reference_number=disposal_ref,
                    notes=f'Disposal: {disposal_reason}',
                    created_by=request.user,
                    unit_cost=cost_per_unit,
                    total_cost=cost_per_unit * quantity,
                )
                
                messages.success(request, f'Disposed {quantity} units of {product.product_name}. Disposal ref: {disposal_ref}')
        except Exception as e:
            messages.error(request, f'Error disposing stock: {str(e)}')
        
        return redirect('products:non_resaleable_inventory_list')
    
    # GET request - show disposal form
    products = Product.objects.filter(
        non_resaleable_stock__gt=0,
        is_active=True
    ).select_related('company').order_by('display_order', 'product_name')
    
    context = {'products': products}
    return render(request, 'products/dispose_non_resaleable.html', context)


@login_required
def recover_non_resaleable_stock(request):
    """Move non-resaleable stock back to resaleable (e.g. items incorrectly classified or repaired)."""
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('products:non_resaleable_inventory_list')

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 0))
        reason = request.POST.get('reason', '').strip()

        if not product_id or quantity <= 0:
            messages.error(request, 'Invalid product or quantity.')
            return redirect('products:non_resaleable_inventory_list')

        product = get_object_or_404(Product, id=product_id)

        if product.non_resaleable_stock < quantity:
            messages.error(
                request,
                f'Cannot recover {quantity} units. Only {product.non_resaleable_stock} non-resaleable units available.'
            )
            return redirect('products:non_resaleable_inventory_list')

        try:
            with transaction.atomic():
                prev_non_res = product.non_resaleable_stock
                prev_res = product.quantity_in_stock

                product.non_resaleable_stock -= quantity
                product.quantity_in_stock += quantity
                product.save()

                from django.utils import timezone
                current_year = timezone.now().year
                prefix = f"RCV-{current_year}-"
                last = StockMovement.objects.filter(
                    movement_type='non_resaleable_recovered',
                    reference_number__startswith=prefix
                ).order_by('-reference_number').first()
                new_num = (int(last.reference_number.split('-')[-1]) + 1) if last else 1
                ref = f"{prefix}{new_num:04d}"

                cost_per_unit = product.cost_after_foc if product.cost_after_foc else Decimal('0')

                StockMovement.objects.create(
                    product=product,
                    movement_type='non_resaleable_recovered',
                    stock_type='non_resaleable',
                    quantity=-quantity,
                    previous_quantity=prev_non_res,
                    new_quantity=product.non_resaleable_stock,
                    reference_number=ref,
                    notes=f'Recovered to resaleable: {reason}',
                    created_by=request.user,
                    unit_cost=cost_per_unit,
                    total_cost=cost_per_unit * quantity,
                )
                StockMovement.objects.create(
                    product=product,
                    movement_type='non_resaleable_recovered',
                    stock_type='resaleable',
                    quantity=quantity,
                    previous_quantity=prev_res,
                    new_quantity=product.quantity_in_stock,
                    reference_number=ref,
                    notes=f'Recovered from non-resaleable: {reason}',
                    created_by=request.user,
                    unit_cost=cost_per_unit,
                    total_cost=cost_per_unit * quantity,
                )

                messages.success(
                    request,
                    f'Recovered {quantity} units of {product.product_name} to resaleable stock. Ref: {ref}'
                )
        except Exception as e:
            messages.error(request, f'Error recovering stock: {str(e)}')

    return redirect('products:non_resaleable_inventory_list')


@login_required
def product_usage_history(request):
    """Show comprehensive transaction history for a product - all stock movements"""
    from sales.models import ReturnItem
    
    # Get filter parameters
    product_id = request.GET.get('product')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    transaction_type = request.GET.get('transaction_type', 'all')
    
    # Get products for dropdown (ordered by display_order)
    products = Product.objects.filter(is_active=True).select_related('company').order_by('display_order', 'product_name')
    
    # If no product selected, show product selector
    if not product_id:
        context = {
            'products': products,
            'selected_product': None,
        }
        return render(request, 'products/product_usage_history.html', context)
    
    # Get selected product
    product = get_object_or_404(Product.objects.select_related('company'), pk=product_id)
    
    # Collect all transactions for this product
    transactions = []
    
    # 1. Stock Movements (Opening Balance, Adjustments, Damages, etc.)
    # Exclude 'sale', 'return', and 'status_adjustment' types since they're shown via their specific models.
    # Also exclude cancellation reversal adjustments to avoid double-counting cancelled bill/return transactions.
    stock_movements = StockMovement.objects.filter(product=product).exclude(
        movement_type__in=['sale', 'return', 'status_adjustment']
    ).exclude(
        movement_type='adjustment',
        reference_number__endswith='-CANCEL'
    ).exclude(
        movement_type='adjustment',
        notes__contains='cancelled - Stock reversal'
    ).select_related('created_by', 'stock_count')
    if date_from:
        stock_movements = stock_movements.filter(created_at__gte=datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
        stock_movements = stock_movements.filter(created_at__lt=date_to_obj)
    
    for movement in stock_movements:
        trans_type = movement.movement_type
        if transaction_type == 'all' or transaction_type == trans_type:
            # Extract reference ID from reference number for specific transaction types
            reference_id = None
            if movement.reference_number:
                if movement.movement_type == 'purchase' and movement.reference_number.startswith('GRN-'):
                    from products.models import Purchase
                    try:
                        grn = Purchase.objects.filter(grn_number=movement.reference_number).first()
                        if grn:
                            reference_id = grn.id
                    except:
                        pass
                elif movement.movement_type == 'exchange' and movement.reference_number.startswith('EXC-'):
                    from sales.models import ItemExchange
                    try:
                        exchange = ItemExchange.objects.filter(exchange_number=movement.reference_number).first()
                        if exchange:
                            reference_id = exchange.id
                    except:
                        pass
            
            transactions.append({
                'date': movement.created_at,
                'type': movement.get_movement_type_display(),
                'type_code': movement.movement_type,
                'quantity_in': movement.quantity if movement.quantity > 0 else 0,
                'quantity_out': abs(movement.quantity) if movement.quantity < 0 else 0,
                'foc_quantity': 0,
                'balance': movement.new_quantity,
                'reference': movement.reference_number or '-',
                'reference_id': reference_id,
                'notes': movement.notes or '-',
                'user': movement.created_by.username if movement.created_by else 'System',
            })
    
    # 2. Sales (from BillItems) — exclude cancelled bills (their stock was already reversed)
    bill_items = BillItem.objects.filter(product=product).exclude(
        bill__bill_status='cancelled'
    ).select_related('bill', 'bill__shop', 'bill__sales_rep')
    if date_from:
        bill_items = bill_items.filter(bill__bill_date__gte=datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
        bill_items = bill_items.filter(bill__bill_date__lt=date_to_obj)
    
    if transaction_type == 'all' or transaction_type == 'sale':
        for item in bill_items:
            transactions.append({
                'date': item.bill.bill_date,
                'type': 'Sale',
                'type_code': 'sale',
                'quantity_in': 0,
                'quantity_out': float(item.quantity),
                'foc_quantity': float(item.foc_quantity),
                'balance': '-',  # We'll calculate running balance later
                'reference': item.bill.bill_number,
                'reference_id': item.bill.id,
                'notes': f"{item.bill.shop.shop_name if item.bill.shop else 'No Shop'} - Rs.{item.line_total}",
                'user': item.bill.sales_rep.username,
                'shop': item.bill.shop.shop_name if item.bill.shop else 'No Shop',
                'unit_price': float(item.unit_price),
                'value': float(item.line_total),
            })
    
    # 3. Returns (from ReturnItems) — exclude cancelled returns (their stock was already reversed)
    return_items = ReturnItem.objects.filter(product=product).exclude(
        return_ref__settlement_status='cancelled'
    ).select_related('return_ref__bill__shop')
    if date_from:
        return_items = return_items.filter(return_ref__return_date__gte=datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
        return_items = return_items.filter(return_ref__return_date__lt=date_to_obj)
    
    if transaction_type == 'all' or transaction_type == 'return':
        for item in return_items:
            # Get user safely
            user = 'System'
            if hasattr(item.return_ref, 'created_by') and item.return_ref.created_by:
                user = item.return_ref.created_by.username
            
            # Get shop name safely
            shop_name = 'Shop'
            if item.return_ref.bill and item.return_ref.bill.shop:
                shop_name = item.return_ref.bill.shop.shop_name
            
            transactions.append({
                'date': item.return_ref.return_date,
                'type': 'Return from Shop',
                'type_code': 'return',
                'quantity_in': float(item.quantity),
                'quantity_out': 0,
                'foc_quantity': float(item.foc_quantity) if hasattr(item, 'foc_quantity') else 0,
                'balance': '-',
                'reference': item.return_ref.return_number,
                'reference_id': item.return_ref.id,
                'notes': f"Return from {shop_name} - {item.return_ref.return_reason if hasattr(item.return_ref, 'return_reason') else 'Return'}",
                'user': user,
            })
    
    # 4. Product Status Adjustments (Damaged/Used items)
    # Query both legacy (product field) and new system (through items)
    from products.models import ProductStatusAdjustmentItem
    adjustment_ids = set()
    
    # Get adjustments from legacy product field
    legacy_adjustments = ProductStatusAdjustment.objects.filter(product=product).values_list('id', flat=True)
    adjustment_ids.update(legacy_adjustments)
    
    # Get adjustments from items relationship
    item_adjustments = ProductStatusAdjustmentItem.objects.filter(product=product).values_list('adjustment_id', flat=True)
    adjustment_ids.update(item_adjustments)
    
    # Get all adjustments and apply filters
    status_adjustments = ProductStatusAdjustment.objects.filter(id__in=adjustment_ids).select_related('adjusted_by')
    if date_from:
        status_adjustments = status_adjustments.filter(adjustment_date__gte=datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
        status_adjustments = status_adjustments.filter(adjustment_date__lt=date_to_obj)
    
    if transaction_type == 'all' or transaction_type == 'status_adjustment':
        for adj in status_adjustments:
            # Get quantity for this specific product (support multi-item adjustments)
            adj_quantity = adj.quantity  # Legacy field
            if adj.items.exists():
                product_item = adj.items.filter(product=product).first()
                if product_item:
                    adj_quantity = product_item.quantity
            
            transactions.append({
                'date': adj.adjustment_date,
                'type': f'{adj.get_status_type_display()} - Status Change',
                'type_code': 'status_adjustment',
                'quantity_in': 0,
                'quantity_out': adj_quantity,
                'foc_quantity': 0,
                'balance': '-',
                'reference': adj.adjustment_number,
                'reference_id': adj.id,
                'notes': adj.reason or '-',
                'user': adj.adjusted_by.username if adj.adjusted_by else 'System',
            })
    
    # Sort all transactions by date (newest first)
    transactions.sort(key=lambda x: x['date'], reverse=True)
    
    # Calculate summary
    total_in = sum(t['quantity_in'] for t in transactions)
    total_out = sum(t['quantity_out'] for t in transactions)
    total_foc = sum(t['foc_quantity'] for t in transactions)
    # FOC items also go out of stock
    total_out_with_foc = total_out + total_foc
    total_value = sum(t.get('value', 0) for t in transactions)
    
    context = {
        'products': products,
        'selected_product': product_id,
        'product': product,
        'transactions': transactions[:200],  # Limit to 200 recent transactions
        'total_transactions': len(transactions),
        'date_from': date_from,
        'date_to': date_to,
        'transaction_type': transaction_type,
        'summary': {
            'total_in': total_in,
            'total_out': total_out_with_foc,  # Include FOC in total out
            'total_foc': total_foc,
            'total_value': total_value,
            'current_stock': product.quantity_in_stock,
            'calculated_stock': total_in - total_out_with_foc,  # What stock should be
        },
        'transaction_types': [
            ('all', 'All Transactions'),
            ('opening_balance', 'Opening Balance'),
            ('purchase', 'Stock Received'),
            ('sale', 'Sales'),
            ('return', 'Returns'),
            ('adjustment', 'Stock Adjustments'),
            ('damage', 'Damages'),
            ('foc_out', 'FOC Given'),
            ('status_adjustment', 'Status Changes'),
        ],
    }
    return render(request, 'products/product_usage_history.html', context)


# =============================================================================
# ACTIVATE FROM GLOBAL CATALOG
# =============================================================================

@login_required
def activate_catalog(request):
    """
    Browse the global product catalog and activate products into this
    distributor's inventory. Only admin/office users can activate.
    """
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied. Only admin/office users can activate products.')
        return redirect('products:list')

    from catalog.models import GlobalProduct, GlobalCompany, GlobalCategory

    # Get all active global products
    global_products = GlobalProduct.objects.select_related('company', 'category').filter(is_active=True)

    # Get IDs of already-activated global products in this tenant
    activated_ids = set(
        Product.objects.filter(global_product__isnull=False)
        .values_list('global_product_id', flat=True)
    )

    # Filters
    company_id = request.GET.get('company')
    category_id = request.GET.get('category')
    search = request.GET.get('q', '').strip()
    show_activated = request.GET.get('activated') == '1'

    if company_id:
        global_products = global_products.filter(company_id=company_id)
    if category_id:
        global_products = global_products.filter(category_id=category_id)
    if search:
        global_products = global_products.filter(
            models.Q(product_name__icontains=search) |
            models.Q(product_code__icontains=search) |
            models.Q(company__company_name__icontains=search)
        )

    # Annotate each product with activation status
    products_with_status = []
    for gp in global_products.order_by('display_order', 'product_name'):
        products_with_status.append({
            'product': gp,
            'is_activated': gp.pk in activated_ids,
        })

    if not show_activated:
        products_with_status = [p for p in products_with_status if not p['is_activated']]

    total_catalog = GlobalProduct.objects.filter(is_active=True).count()
    activated_count = len(activated_ids)

    context = {
        'products_with_status': products_with_status,
        'companies': GlobalCompany.objects.filter(is_active=True),
        'categories': GlobalCategory.objects.filter(is_active=True),
        'activated_count': activated_count,
        'total_catalog': total_catalog,
        'remaining_count': total_catalog - activated_count,
        'current_company': company_id,
        'current_category': category_id,
        'current_search': search,
        'show_activated': show_activated,
    }
    return render(request, 'products/activate_catalog.html', context)


@login_required
@transaction.atomic
def activate_product(request, global_pk):
    """
    Activate a global catalog product into this distributor's inventory.
    Creates a local Product with the global_product FK linked, and
    auto-creates local Company/Category if they don't exist yet.
    """
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('products:list')

    from catalog.models import GlobalProduct

    global_product = get_object_or_404(GlobalProduct.objects.select_related('company', 'category'), pk=global_pk)

    # Check if already activated
    existing = Product.objects.filter(global_product=global_product).first()
    if existing:
        messages.warning(request, f'"{global_product.product_name}" is already activated as "{existing.product_name}".')
        return redirect('products:activate_catalog')

    if request.method == 'POST':
        # Get or create local Company matching the global one
        local_company, _ = Company.objects.get_or_create(
            company_code=global_product.company.company_code,
            defaults={
                'company_name': global_product.company.company_name,
                'contact_person': global_product.company.contact_person or 'N/A',
                'phone_number': global_product.company.phone_number or 'N/A',
                'email': global_product.company.email or 'na@na.com',
                'address': global_product.company.address or 'N/A',
                'city': global_product.company.city or '',
                'country': global_product.company.country or 'Sri Lanka',
                'tagline': global_product.company.tagline or '',
                'description': global_product.company.description or '',
                'website': global_product.company.website or '',
                'is_active': True,
            }
        )

        # Get or create local Category matching the global one
        local_category = None
        if global_product.category:
            local_category, _ = Category.objects.get_or_create(
                name=global_product.category.name,
                defaults={
                    'description': global_product.category.description or '',
                    'is_active': True,
                }
            )

        # Read distributor-specific fields from the form (defaults come from global catalog)
        discount_pct = Decimal(request.POST.get('discount_percentage', str(global_product.discount_percentage)))
        company_discount_pct = Decimal(request.POST.get('company_discount_percentage', str(global_product.company_discount_percentage)))
        minimum_stock = int(request.POST.get('minimum_stock_level', '50'))
        company_foc_buy = int(request.POST.get('company_foc_buy', str(global_product.company_foc_buy)))
        company_foc_free = int(request.POST.get('company_foc_free', str(global_product.company_foc_free)))
        shop_foc_buy = int(request.POST.get('shop_foc_buy', str(global_product.shop_foc_buy)))
        shop_foc_free = int(request.POST.get('shop_foc_free', str(global_product.shop_foc_free)))

        # Create the local Product
        product = Product.objects.create(
            global_product=global_product,
            product_code=global_product.product_code,
            product_name=global_product.product_name,
            sinhala_name=global_product.sinhala_name or '',
            description=global_product.description or '',
            company=local_company,
            category=local_category,
            size=global_product.size,
            marked_price=global_product.marked_price,
            bottles_per_pack=global_product.bottles_per_pack,
            barcode=global_product.barcode or '',
            display_order=global_product.display_order,
            quantity_in_stock=0,
            non_resaleable_stock=0,
            minimum_stock_level=minimum_stock,
            discount_percentage=discount_pct,
            company_discount_percentage=company_discount_pct,
            company_foc_buy=company_foc_buy,
            company_foc_free=company_foc_free,
            shop_foc_buy=shop_foc_buy,
            shop_foc_free=shop_foc_free,
            is_active=True,
        )

        messages.success(request, f'Product "{product.product_name}" activated successfully! Stock starts at 0 — use purchases/opening balance to add stock.')
        return redirect('products:activate_catalog')

    # GET: Show form with pre-filled catalog data and editable distributor fields
    context = {
        'global_product': global_product,
    }
    return render(request, 'products/activate_product.html', context)


@login_required
@transaction.atomic
def bulk_activate_products(request):
    """
    Activate multiple global catalog products at once with default settings.
    """
    if request.user.user_type not in ('admin', 'office'):
        messages.error(request, 'Access denied.')
        return redirect('products:list')

    if request.method != 'POST':
        return redirect('products:activate_catalog')

    from catalog.models import GlobalProduct

    selected_ids = request.POST.getlist('selected_products')
    if not selected_ids:
        messages.warning(request, 'No products selected.')
        return redirect('products:activate_catalog')

    activated_count = 0
    skipped_count = 0

    for gp_id in selected_ids:
        try:
            global_product = GlobalProduct.objects.select_related('company', 'category').get(pk=gp_id)

            # Skip if already activated
            if Product.objects.filter(global_product=global_product).exists():
                skipped_count += 1
                continue

            # Get or create local Company
            local_company, _ = Company.objects.get_or_create(
                company_code=global_product.company.company_code,
                defaults={
                    'company_name': global_product.company.company_name,
                    'contact_person': global_product.company.contact_person or 'N/A',
                    'phone_number': global_product.company.phone_number or 'N/A',
                    'email': global_product.company.email or 'na@na.com',
                    'address': global_product.company.address or 'N/A',
                    'city': global_product.company.city or '',
                    'country': global_product.company.country or 'Sri Lanka',
                    'is_active': True,
                }
            )

            # Get or create local Category
            local_category = None
            if global_product.category:
                local_category, _ = Category.objects.get_or_create(
                    name=global_product.category.name,
                    defaults={
                        'description': global_product.category.description or '',
                        'is_active': True,
                    }
                )

            Product.objects.create(
                global_product=global_product,
                product_code=global_product.product_code,
                product_name=global_product.product_name,
                sinhala_name=global_product.sinhala_name or '',
                description=global_product.description or '',
                company=local_company,
                category=local_category,
                size=global_product.size,
                marked_price=global_product.marked_price,
                bottles_per_pack=global_product.bottles_per_pack,
                barcode=global_product.barcode or '',
                display_order=global_product.display_order,
                quantity_in_stock=0,
                non_resaleable_stock=0,
                minimum_stock_level=50,
                discount_percentage=Decimal('10.00'),
                company_discount_percentage=Decimal('23.00'),
                company_foc_buy=12,
                company_foc_free=1,
                shop_foc_buy=12,
                shop_foc_free=1,
                is_active=True,
            )
            activated_count += 1
        except Exception as e:
            messages.error(request, f'Error activating product ID {gp_id}: {str(e)}')

    if activated_count > 0:
        messages.success(request, f'{activated_count} product(s) activated successfully!')
    if skipped_count > 0:
        messages.info(request, f'{skipped_count} product(s) were already activated (skipped).')

    return redirect('products:activate_catalog')
