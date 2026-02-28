"""
Purchase Order (PO) Views
Manages the creation and tracking of purchase orders from suppliers
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import HttpResponse
from django.conf import settings
from decimal import Decimal
import io
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, KeepTogether
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from .models import PurchaseOrder, PurchaseOrderItem, Product, Company, Purchase
from business.models import DistributorProfile


@login_required
def po_list(request):
    """List all purchase orders with filters and stats"""
    
    # Access control
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied. Purchase orders are only accessible to admin and office staff.')
        return redirect('dashboard:home')
    
    # Get all POs
    pos = PurchaseOrder.objects.select_related('company', 'created_by').all()
    
    # Apply filters
    status_filter = request.GET.get('status', '')
    company_filter = request.GET.get('company', '')
    
    if status_filter:
        pos = pos.filter(status=status_filter)
    if company_filter:
        pos = pos.filter(company_id=company_filter)
    
    # Calculate stats
    stats = {
        'total_pos': PurchaseOrder.objects.count(),
        'total_value': PurchaseOrder.objects.aggregate(Sum('total'))['total__sum'] or 0,
        'draft': PurchaseOrder.objects.filter(status='draft').count(),
        'ordered': PurchaseOrder.objects.filter(status='ordered').count(),
    }
    
    # Get companies for filter
    companies = Company.objects.filter(is_active=True).order_by('company_name')
    
    context = {
        'pos': pos,
        'stats': stats,
        'companies': companies,
        'status_filter': status_filter,
        'company_filter': company_filter,
    }
    
    return render(request, 'products/po_list.html', context)


@login_required
def create_po(request):
    """Create a new purchase order"""
    
    # Access control
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        try:
            # Get basic PO data
            company_id = request.POST.get('company')
            order_date = request.POST.get('order_date')
            expected_delivery_date = request.POST.get('expected_delivery_date') or None
            notes = request.POST.get('notes', '')
            
            # Validate company
            company = get_object_or_404(Company, id=company_id)
            
            # Create PO
            po = PurchaseOrder.objects.create(
                company=company,
                order_date=order_date,
                expected_delivery_date=expected_delivery_date,
                notes=notes,
                created_by=request.user,
                status='draft'
            )
            
            # Process line items - iterate through all products
            products = Product.objects.filter(is_active=True)
            items_created = 0
            
            for product in products:
                # Get quantities for this product
                packs = int(request.POST.get(f'packs_{product.id}', 0) or 0)
                loose = int(request.POST.get(f'loose_{product.id}', 0) or 0)
                foc_bottles = int(request.POST.get(f'foc_{product.id}', 0) or 0)
                unit_price = request.POST.get(f'price_{product.id}', 0)
                discount_percentage = request.POST.get(f'discount_{product.id}', 0)
                
                # Skip if no quantity entered
                if packs == 0 and loose == 0:
                    continue
                
                # Calculate total bottles
                total_bottles = (packs * product.bottles_per_pack) + loose
                
                # Create PO item (save method will calculate totals)
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product=product,
                    packs=packs,
                    loose_bottles=loose,
                    bottles_per_pack=product.bottles_per_pack,
                    total_bottles=total_bottles,
                    foc_bottles=foc_bottles,
                    unit_price=Decimal(unit_price) if unit_price else Decimal('0'),
                    discount_percentage=Decimal(discount_percentage) if discount_percentage else Decimal('0'),
                    value_before_discount=0,  # Will be calculated in save()
                    discount_amount=0,
                    line_total=0
                )
                items_created += 1
            
            if items_created == 0:
                messages.warning(request, 'No items added to purchase order. Please enter quantities for at least one product.')
                po.delete()
                companies = Company.objects.filter(is_active=True).order_by('company_name')
                products = Product.objects.filter(is_active=True).select_related('company').order_by('product_name')
                context = {
                    'companies': companies,
                    'products': products,
                }
                return render(request, 'products/create_po.html', context)
            
            # Calculate PO totals
            po.calculate_totals()
            
            messages.success(request, f'Purchase order {po.po_number} created successfully!')
            return redirect('products:po_detail', pk=po.pk)
            
        except Exception as e:
            messages.error(request, f'Error creating purchase order: {str(e)}')
    
    # GET request - show form
    companies = Company.objects.filter(is_active=True).order_by('company_name')
    products = Product.objects.filter(is_active=True).select_related('company', 'category').order_by('display_order', 'size', 'marked_price', 'product_name')
    
    context = {
        'companies': companies,
        'products': products,
    }
    
    return render(request, 'products/create_po.html', context)


@login_required
def po_detail(request, pk):
    """View purchase order details"""
    
    # Access control
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    po = get_object_or_404(PurchaseOrder.objects.select_related('company', 'created_by'), pk=pk)
    items = po.items.select_related('product').order_by('product__display_order', 'product__size', 'product__marked_price', 'product__product_name')
    grns = po.grns.all()  # All GRNs created from this PO
    
    # Calculate summary
    summary = {
        'total_items': items.count(),
        'total_packs': sum(item.packs for item in items),
        'total_loose': sum(item.loose_bottles for item in items),
        'total_bottles': sum(item.total_bottles for item in items),
        'total_foc': sum(item.foc_bottles for item in items),
        'total_received': sum(item.received_quantity for item in items),
        'total_foc_received': sum(item.received_foc for item in items),
        'subtotal': sum(item.value_before_discount for item in items),
        'total_discount': sum(item.discount_amount for item in items),
        'grand_total': po.total,
    }
    
    context = {
        'po': po,
        'items': items,
        'grns': grns,
        'summary': summary,
    }
    
    return render(request, 'products/po_detail.html', context)


@login_required
def mark_po_ordered(request, pk):
    """Mark PO as ordered (sent to supplier)"""
    
    # Access control
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    if po.status != 'draft':
        messages.warning(request, f'PO {po.po_number} is not in draft status.')
        return redirect('products:po_detail', pk=pk)
    
    po.status = 'ordered'
    po.save()
    
    messages.success(request, f'PO {po.po_number} marked as ordered!')
    return redirect('products:po_detail', pk=pk)


@login_required
def cancel_po(request, pk):
    """Cancel a purchase order"""
    
    # Access control
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    if po.status == 'received':
        messages.error(request, f'Cannot cancel PO {po.po_number} - already received.')
        return redirect('products:po_detail', pk=pk)
    
    po.status = 'cancelled'
    po.save()
    
    messages.success(request, f'PO {po.po_number} cancelled.')
    return redirect('products:po_detail', pk=pk)


@login_required
def create_grn_from_po(request, pk):
    """Create a GRN from a purchase order"""
    
    # Access control
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    if po.status == 'cancelled':
        messages.error(request, f'Cannot create GRN from cancelled PO {po.po_number}.')
        return redirect('products:po_detail', pk=pk)
    
    # Redirect to create GRN page with PO pre-filled
    return redirect(f"{request.scheme}://{request.get_host()}/products/purchases/create/?po_id={po.pk}")


@login_required
def edit_po(request, pk):
    """Edit an existing purchase order (only draft status)"""
    
    # Access control
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    po = get_object_or_404(PurchaseOrder.objects.select_related('company'), pk=pk)
    
    # Only draft POs can be edited
    if po.status != 'draft':
        messages.error(request, f'Cannot edit PO {po.po_number}. Only draft purchase orders can be edited.')
        return redirect('products:po_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            # Update basic PO data
            company_id = request.POST.get('company')
            order_date = request.POST.get('order_date')
            expected_delivery_date = request.POST.get('expected_delivery_date') or None
            notes = request.POST.get('notes', '')
            
            # Validate company
            company = get_object_or_404(Company, id=company_id)
            
            # Update PO
            po.company = company
            po.order_date = order_date
            po.expected_delivery_date = expected_delivery_date
            po.notes = notes
            po.save()
            
            # Delete existing items
            po.items.all().delete()
            
            # Process line items - iterate through all products
            products = Product.objects.filter(is_active=True)
            items_created = 0
            
            for product in products:
                # Get quantities for this product
                packs = int(request.POST.get(f'packs_{product.id}', 0) or 0)
                loose = int(request.POST.get(f'loose_{product.id}', 0) or 0)
                foc_bottles = int(request.POST.get(f'foc_{product.id}', 0) or 0)
                unit_price = request.POST.get(f'price_{product.id}', 0)
                discount_percentage = request.POST.get(f'discount_{product.id}', 0)
                
                # Skip if no quantity entered
                if packs == 0 and loose == 0:
                    continue
                
                # Calculate total bottles
                total_bottles = (packs * product.bottles_per_pack) + loose
                
                # Create PO item (save method will calculate totals)
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product=product,
                    packs=packs,
                    loose_bottles=loose,
                    bottles_per_pack=product.bottles_per_pack,
                    total_bottles=total_bottles,
                    foc_bottles=foc_bottles,
                    unit_price=Decimal(unit_price) if unit_price else Decimal('0'),
                    discount_percentage=Decimal(discount_percentage) if discount_percentage else Decimal('0'),
                    value_before_discount=0,  # Will be calculated in save()
                    discount_amount=0,
                    line_total=0
                )
                items_created += 1
            
            if items_created == 0:
                messages.warning(request, 'No items in purchase order. Please add at least one product.')
                return redirect('products:edit_po', pk=pk)
            
            # Calculate PO totals
            po.calculate_totals()
            
            messages.success(request, f'Purchase order {po.po_number} updated successfully!')
            return redirect('products:po_detail', pk=po.pk)
            
        except Exception as e:
            messages.error(request, f'Error updating purchase order: {str(e)}')
    
    # GET request - show form with existing data
    companies = Company.objects.filter(is_active=True).order_by('company_name')
    products = Product.objects.filter(is_active=True).select_related('company', 'category').order_by('display_order', 'size', 'marked_price', 'product_name')
    
    # Build existing items dictionary for pre-filling form
    existing_items = {}
    for item in po.items.select_related('product').all():
        existing_items[item.product.id] = {
            'packs': item.packs,
            'loose': item.loose_bottles,
            'foc': item.foc_bottles,
            'price': item.unit_price,
            'discount': item.discount_percentage
        }
    
    context = {
        'companies': companies,
        'products': products,
        'po': po,
        'existing_items': existing_items,
        'is_edit': True,
    }
    
    return render(request, 'products/edit_po.html', context)


@login_required
def print_po_pdf(request, pk):
    """Generate world-class PDF for Purchase Order with company logos and professional formatting"""
    
    # Access control
    if request.user.user_type not in ['admin', 'office']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
    
    po = get_object_or_404(PurchaseOrder.objects.select_related('company', 'created_by'), pk=pk)
    items = po.items.select_related('product').order_by('product__display_order', 'product__size', 'product__marked_price', 'product__product_name')
    business = DistributorProfile.get_active()
    
    # Custom canvas for page numbers and watermark
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
                self.draw_page_number(num_pages)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def draw_page_number(self, page_count):
            # Page number footer
            self.saveState()
            self.setFont("Helvetica", 9)
            self.setFillColor(colors.HexColor('#7f8c8d'))
            page_num = f"Page {self._pageNumber} of {page_count}"
            self.drawCentredString(A4[0] / 2, 10*mm, page_num)
            
            # Watermark for draft status
            if po.status == 'draft':
                self.saveState()
                self.setFont("Helvetica-Bold", 60)
                self.setFillColor(colors.HexColor('#ecf0f1'), alpha=0.3)
                self.translate(A4[0] / 2, A4[1] / 2)
                self.rotate(45)
                self.drawCentredString(0, 0, "DRAFT")
                self.restoreState()
            
            # Footer line
            self.setStrokeColor(colors.HexColor('#bdc3c7'))
            self.setLineWidth(0.5)
            self.line(15*mm, 15*mm, A4[0] - 15*mm, 15*mm)
            
            # Generated timestamp
            from django.utils import timezone
            timestamp = timezone.now().strftime('%B %d, %Y at %I:%M %p')
            self.drawString(15*mm, 8*mm, f"Generated: {timestamp}")
            self.drawRightString(A4[0] - 15*mm, 8*mm, f"{business.business_name}")
            
            self.restoreState()
    
    # Create PDF
    buffer = io.BytesIO()
    
    # Set meaningful document title
    pdf_title = f"Purchase Order - {po.po_number} - {po.company.company_name}"
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        title=pdf_title,
        bottomMargin=20*mm
    )
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=26,
        textColor=colors.HexColor('#8e44ad'),
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=30
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.white,
        backColor=colors.HexColor('#8e44ad'),
        spaceAfter=10,
        spaceBefore=10,
        leftIndent=10,
        rightIndent=10,
        fontName='Helvetica-Bold',
        leading=20
    )
    
    normal_bold = ParagraphStyle(
        'NormalBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9
    )
    
    small_normal = ParagraphStyle(
        'SmallNormal',
        parent=styles['Normal'],
        fontSize=8
    )
    
    small_right = ParagraphStyle(
        'SmallRight',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_RIGHT
    )
    
    # Helper function to safely load images
    def get_image(image_field, default_width=55*mm, default_height=28*mm):
        """Safely load image with error handling"""
        if image_field:
            try:
                if hasattr(image_field, 'path') and os.path.exists(image_field.path):
                    img = Image(image_field.path, width=default_width, height=default_height, kind='proportional')
                    return img
            except Exception as e:
                print(f"Error loading image: {e}")
        return None
    
    # ========== HEADER SECTION ==========
    header_data = []
    header_row = []
    
    # Our Business Logo
    our_logo = get_image(business.logo)
    if our_logo:
        header_row.append(our_logo)
    else:
        header_row.append(Paragraph(f"<b>{business.business_name}</b>", ParagraphStyle('LogoFallback', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#8e44ad'))))
    
    # Title in middle
    title_content = [
        Paragraph("PURCHASE ORDER", title_style),
        Paragraph(f"PO #: {po.po_number}", subtitle_style)
    ]
    header_row.append(title_content)
    
    # Supplier Logo
    company_logo = get_image(po.company.logo)
    if company_logo:
        header_row.append(company_logo)
    else:
        header_row.append(Paragraph(f"<b>{po.company.company_name}</b>", ParagraphStyle('LogoFallback', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#8e44ad'))))
    
    header_data.append(header_row)
    
    header_table = Table(header_data, colWidths=[60*mm, 60*mm, 60*mm])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(header_table)
    
    # Decorative line
    line_data = [['']]
    line_table = Table(line_data, colWidths=[180*mm])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor('#8e44ad')),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#bdc3c7')),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 6*mm))
    
    # ========== BUSINESS AND SUPPLIER DETAILS ==========
    details_data = []
    
    # Headers
    details_data.append([
        Paragraph("FROM: BUYER", heading_style),
        Paragraph("TO: SUPPLIER", heading_style)
    ])
    
    # Our business details
    our_details = f"""
    <b><font size=11 color='#2c3e50'>{business.business_name}</font></b><br/>
    {business.address_line1 or ''}<br/>
    """
    if business.address_line2:
        our_details += f"{business.address_line2}<br/>"
    our_details += f"{business.city or ''}, {business.postal_code or ''}<br/>"
    our_details += f"{business.country or 'Sri Lanka'}<br/>"
    our_details += f"<br/><b>Contact:</b> {business.primary_phone or 'N/A'}<br/>"
    if business.secondary_phone:
        our_details += f"{business.secondary_phone}<br/>"
    our_details += f"<b>Email:</b> {business.primary_email or 'N/A'}<br/>"
    if business.tax_id:
        our_details += f"<b>Tax ID:</b> {business.tax_id}<br/>"
    if business.business_registration_number:
        our_details += f"<b>Reg #:</b> {business.business_registration_number}<br/>"
    
    # Supplier details
    supplier_details = f"""
    <b><font size=11 color='#2c3e50'>{po.company.company_name}</font></b><br/>
    {po.company.address}<br/>
    """
    if po.company.city:
        supplier_details += f"{po.company.city}, "
    supplier_details += f"{po.company.country}<br/>"
    supplier_details += f"<br/><b>Contact Person:</b> {po.company.contact_person}<br/>"
    supplier_details += f"<b>Phone:</b> {po.company.phone_number}<br/>"
    if po.company.secondary_phone:
        supplier_details += f"{po.company.secondary_phone}<br/>"
    supplier_details += f"<b>Email:</b> {po.company.email}<br/>"
    if po.company.tax_id:
        supplier_details += f"<b>Tax ID:</b> {po.company.tax_id}<br/>"
    if po.company.registration_number:
        supplier_details += f"<b>Reg #:</b> {po.company.registration_number}<br/>"
    
    details_data.append([
        Paragraph(our_details, small_normal),
        Paragraph(supplier_details, small_normal)
    ])
    
    details_table = Table(details_data, colWidths=[90*mm, 90*mm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8e44ad')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('INNERGRID', (0, 1), (-1, -1), 0.5, colors.HexColor('#ecf0f1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 6*mm))
    
    # ========== PO INFORMATION ==========
    po_info_data = [
        [Paragraph("ORDER INFORMATION", heading_style), "", "", ""]
    ]
    
    po_info_data.append([
        Paragraph("<b>Order Date:</b>", small_normal),
        Paragraph(str(po.order_date.strftime('%B %d, %Y')), small_normal),
        Paragraph("<b>Expected Delivery:</b>", small_normal),
        Paragraph(str(po.expected_delivery_date.strftime('%B %d, %Y')) if po.expected_delivery_date else 'To Be Determined', small_normal)
    ])
    
    status_color = {'draft': 'orange', 'ordered': 'green', 'received': 'blue', 'cancelled': 'red'}.get(po.status, 'gray')
    
    po_info_data.append([
        Paragraph("<b>Status:</b>", small_normal),
        Paragraph(f"<font color='{status_color}'><b>{po.status.upper()}</b></font>", small_normal),
        Paragraph("<b>Created By:</b>", small_normal),
        Paragraph(po.created_by.get_full_name() if po.created_by else 'N/A', small_normal)
    ])
    
    # Calculate summary stats
    total_items = items.count()
    total_bottles = sum(item.total_bottles for item in items)
    total_foc = sum(item.foc_bottles for item in items)
    
    po_info_data.append([
        Paragraph("<b>Total Line Items:</b>", small_normal),
        Paragraph(f"<b>{total_items}</b>", small_normal),
        Paragraph("<b>Total Bottles:</b>", small_normal),
        Paragraph(f"<b>{total_bottles:,}</b> + {total_foc:,} FOC", small_normal)
    ])
    
    po_info_table = Table(po_info_data, colWidths=[45*mm, 45*mm, 45*mm, 45*mm])
    po_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8e44ad')),
        ('SPAN', (0, 0), (-1, 0)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('GRID', (0, 1), (-1, -1), 0.5, colors.HexColor('#ecf0f1')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(po_info_table)
    elements.append(Spacer(1, 8*mm))
    
    # ========== ITEMS TABLE WITH GROUPING ==========
    # Header table to match items table width (10+52+15+15+18+12+22+15+25 = 184mm)
    items_header_table = Table([[Paragraph("ORDER ITEMS", heading_style)]], colWidths=[184*mm])
    items_header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#8e44ad')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
    ]))
    elements.append(items_header_table)
    elements.append(Spacer(1, 3*mm))
    
    # Group items by size and price
    from itertools import groupby
    
    grouped_items = []
    for size, size_items in groupby(items, key=lambda x: x.product.size):
        for price, price_items in groupby(list(size_items), key=lambda x: x.product.marked_price):
            grouped_items.append({
                'size': size,
                'price': price,
                'items': list(price_items)
            })
    
    items_data = [[
        Paragraph("<b>#</b>", ParagraphStyle('TableHeader', parent=small_normal, fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER)),
        Paragraph("<b>Product Name</b>", ParagraphStyle('TableHeader', parent=small_normal, fontName='Helvetica-Bold', fontSize=8)),
        Paragraph("<b>Packs</b>", ParagraphStyle('TableHeader', parent=small_normal, fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER)),
        Paragraph("<b>Loose</b>", ParagraphStyle('TableHeader', parent=small_normal, fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER)),
        Paragraph("<b>Total<br/>Bottles</b>", ParagraphStyle('TableHeader', parent=small_normal, fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER)),
        Paragraph("<b>FOC</b>", ParagraphStyle('TableHeader', parent=small_normal, fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER)),
        Paragraph("<b>Unit<br/>Price</b>", ParagraphStyle('TableHeader', parent=small_normal, fontName='Helvetica-Bold', fontSize=8, alignment=TA_RIGHT)),
        Paragraph("<b>Disc<br/>%</b>", ParagraphStyle('TableHeader', parent=small_normal, fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER)),
        Paragraph("<b>Line Total</b>", ParagraphStyle('TableHeader', parent=small_normal, fontName='Helvetica-Bold', fontSize=8, alignment=TA_RIGHT))
    ]]
    
    idx = 1
    table_styles = [
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('PADDING', (0, 0), (-1, 0), 6),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (2, 0), (5, 0), 'CENTER'),
        ('ALIGN', (6, 0), (6, 0), 'RIGHT'),
        ('ALIGN', (7, 0), (7, 0), 'CENTER'),
        ('ALIGN', (8, 0), (8, 0), 'RIGHT'),
    ]
    
    current_row = 1
    
    for group in grouped_items:
        # Group header
        group_header = [
            Paragraph(f"<b>{group['size']} - Rs. {group['price']:,.2f}</b>", ParagraphStyle('GroupHeader', parent=small_normal, fontName='Helvetica-Bold', textColor=colors.HexColor('#8e44ad'))),
            '', '', '', '', '', '', '', ''
        ]
        items_data.append(group_header)
        
        # Style for group header row
        table_styles.extend([
            ('SPAN', (0, current_row), (-1, current_row)),
            ('BACKGROUND', (0, current_row), (-1, current_row), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, current_row), (-1, current_row), colors.HexColor('#8e44ad')),
            ('FONTNAME', (0, current_row), (-1, current_row), 'Helvetica-Bold'),
            ('PADDING', (0, current_row), (-1, current_row), 5),
        ])
        current_row += 1
        
        # Group items
        for item in group['items']:
            items_data.append([
                Paragraph(str(idx), small_normal),
                Paragraph(item.product.product_name, small_normal),
                Paragraph(str(item.packs), small_normal),
                Paragraph(str(item.loose_bottles), small_normal),
                Paragraph(f"<b>{item.total_bottles:,}</b>", small_normal),
                Paragraph(str(item.foc_bottles) if item.foc_bottles else '-', small_normal),
                Paragraph(f"Rs. {item.unit_price:,.2f}", small_right),
                Paragraph(f"{item.discount_percentage:.1f}%", small_normal),
                Paragraph(f"<b>Rs. {item.line_total:,.2f}</b>", small_right)
            ])
            
            # Styles for data rows
            table_styles.extend([
                ('ALIGN', (0, current_row), (0, current_row), 'CENTER'),
                ('ALIGN', (2, current_row), (5, current_row), 'CENTER'),
                ('ALIGN', (6, current_row), (6, current_row), 'RIGHT'),
                ('ALIGN', (7, current_row), (7, current_row), 'CENTER'),
                ('ALIGN', (8, current_row), (8, current_row), 'RIGHT'),
            ])
            
            idx += 1
            current_row += 1
    
    items_table = Table(items_data, colWidths=[
        10*mm, 52*mm, 15*mm, 15*mm, 18*mm, 12*mm, 22*mm, 15*mm, 25*mm
    ])
    
    # Apply all table styles
    table_styles.extend([
        # General styles
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('PADDING', (0, 1), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('GRID', (0, 1), (-1, -1), 0.5, colors.HexColor('#ecf0f1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ])
    
    items_table.setStyle(TableStyle(table_styles))
    elements.append(items_table)
    elements.append(Spacer(1, 8*mm))
    
    # ========== FINANCIAL SUMMARY ==========
    label_bold = ParagraphStyle(
        'LabelBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        alignment=TA_LEFT
    )
    
    right_bold = ParagraphStyle(
        'RightBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        alignment=TA_RIGHT
    )
    
    summary_data = [
        ['', '', Paragraph("<b>Subtotal:</b>", label_bold), Paragraph(f"<b>Rs. {po.subtotal:,.2f}</b>", right_bold)],
        ['', '', Paragraph("<b>Discount:</b>", label_bold), Paragraph(f"<b>Rs. {po.discount:,.2f}</b>", right_bold)],
        ['', '', Paragraph("<b>GRAND TOTAL:</b>", ParagraphStyle('GrandTotal', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor('#8e44ad'), fontName='Helvetica-Bold', alignment=TA_LEFT)), 
         Paragraph(f"<b><font size=14 color='#8e44ad'>Rs. {po.total:,.2f}</font></b>", ParagraphStyle('GrandTotalValue', parent=styles['Normal'], fontSize=14, alignment=TA_RIGHT))],
    ]
    
    summary_table = Table(summary_data, colWidths=[50*mm, 60*mm, 30*mm, 40*mm])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (-2, 0), (-2, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (-2, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (-2, 0), (-1, -1), 'Helvetica-Bold'),
        ('PADDING', (-2, 0), (-1, -1), 8),
        ('BOX', (-2, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('LINEABOVE', (-2, -1), (-1, -1), 2, colors.HexColor('#8e44ad')),
        ('LINEBELOW', (-2, -1), (-1, -1), 2, colors.HexColor('#8e44ad')),
        ('TOPPADDING', (-2, -1), (-1, -1), 10),
        ('BOTTOMPADDING', (-2, -1), (-1, -1), 10),
        ('BACKGROUND', (-2, -1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (-2, 0), (-1, -2), 0.5, colors.HexColor('#ecf0f1')),
    ]))
    
    elements.append(summary_table)
    
    # ========== NOTES ==========
    if po.notes:
        elements.append(Spacer(1, 8*mm))
        elements.append(Paragraph("NOTES & SPECIAL INSTRUCTIONS", heading_style))
        elements.append(Spacer(1, 2*mm))
        notes_para = Paragraph(po.notes, ParagraphStyle('Notes', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#34495e')))
        notes_table = Table([[notes_para]], colWidths=[180*mm])
        notes_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(notes_table)
    
    # ========== TERMS & CONDITIONS ==========
    elements.append(Spacer(1, 8*mm))
    # Header table to match terms table width (180mm)
    terms_header_table = Table([[Paragraph("TERMS & CONDITIONS", heading_style)]], colWidths=[180*mm])
    terms_header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#8e44ad')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
    ]))
    elements.append(terms_header_table)
    elements.append(Spacer(1, 2*mm))
    
    terms = """
    1. This Purchase Order is subject to our standard terms and conditions.<br/>
    2. All goods must be delivered to the address specified above.<br/>
    3. Delivery must be made on or before the expected delivery date.<br/>
    4. All items must match the specifications outlined in this purchase order.<br/>
    5. FOC (Free of Charge) items are separate from purchased quantities.<br/>
    6. Payment terms as per existing agreement between parties.<br/>
    7. Any discrepancies must be reported within 24 hours of delivery.<br/>
    8. Damaged or expired goods will not be accepted.
    """
    
    terms_para = Paragraph(terms, ParagraphStyle('Terms', parent=styles['Normal'], fontSize=7, leading=10, textColor=colors.HexColor('#7f8c8d')))
    terms_table = Table([[terms_para]], colWidths=[180*mm])
    terms_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(terms_table)
    
    # ========== SIGNATURES ==========
    elements.append(Spacer(1, 15*mm))
    
    sig_style = ParagraphStyle('Signature', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)
    
    footer_data = [
        [
            Paragraph(f"<b>AUTHORIZED BY</b><br/><br/><br/>_______________________<br/>{po.created_by.get_full_name() if po.created_by else 'N/A'}<br/><font size=8>{business.business_name}</font>", sig_style),
            Paragraph(f"<b>ACCEPTED BY</b><br/><br/><br/>_______________________<br/>Authorized Signature<br/><font size=8>{po.company.company_name}</font>", sig_style)
        ]
    ]
    
    footer_table = Table(footer_data, colWidths=[90*mm, 90*mm])
    footer_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ecf0f1')),
    ]))
    elements.append(footer_table)
    
    # Build PDF with custom canvas
    doc.build(elements, canvasmaker=NumberedCanvas)
    
    # Get PDF from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Return as HTTP response
    response = HttpResponse(content_type='application/pdf')
    # Clean company name for filename (remove special characters)
    company_name_clean = ''.join(c if c.isalnum() or c in (' ', '-') else '_' for c in po.company.company_name)
    filename = f"PO_{po.po_number}_{company_name_clean}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    response.write(pdf)
    
    return response

