from django.db.models import Sum, Q
from decimal import Decimal
from datetime import datetime, timedelta, date
from .models import StockKeepingUnit, PurchaseOrderItem, Product, MonthlyStockCount
from sales.models import SaleItem  # Moved to sales app


class FlavorBalanceReport:
    """
    Calculate flavor balances using monthly count formula:
    Last Month End Count + This Month Received - This Month Billed = Current Balance
    """
    
    @staticmethod
    def get_balance_by_sku(sku, start_date=None, end_date=None):
        """
        Get flavor balance breakdown for a specific SKU using monthly count formula
        
        Args:
            sku: StockKeepingUnit instance
            start_date: Start of period (defaults to first day of current month)
            end_date: End of period (defaults to today)
            
        Returns:
            dict with SKU info and flavor balances
        """
        # Default to current month if not specified
        if not start_date:
            today = date.today()
            start_date = today.replace(day=1)
        if not end_date:
            end_date = date.today()
        
        # Get all products linked to this SKU
        products = Product.objects.filter(sku=sku, is_active=True)
        flavors = products.values_list('flavor', flat=True).distinct()
        
        flavor_data = []
        total_opening = 0
        total_received = 0
        total_sold = 0
        
        # Get last month's end date (opening balance date)
        opening_date = start_date - timedelta(days=1)
        
        for flavor in flavors:
            if not flavor:  # Skip null/empty flavors
                continue
            
            # Get the product for this flavor
            product = products.filter(flavor=flavor).first()
            
            # Get opening balance from last month's physical count
            last_count = MonthlyStockCount.objects.filter(
                product=product,
                count_date__lte=opening_date
            ).order_by('-count_date').first()
            
            opening_balance = last_count.physical_count if last_count else 0
            
            # Calculate received in this period
            received = PurchaseOrderItem.objects.filter(
                sku=sku,
                flavor=flavor,
                purchase_order__status__in=['received'],
                purchase_order__order_date__gte=start_date,
                purchase_order__order_date__lte=end_date
            ).aggregate(total=Sum('received_quantity'))['total'] or 0
            
            # Calculate sold in this period
            sold = SaleItem.objects.filter(
                product__sku=sku,
                product__flavor=flavor,
                sale__sale_status__in=['confirmed'],
                sale__sale_date__gte=start_date,
                sale__sale_date__lte=end_date
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            # Formula: Opening + Received - Sold = Closing Balance
            balance = opening_balance + received - sold
            
            flavor_data.append({
                'flavor': flavor,
                'product_id': product.id if product else None,
                'opening_balance': opening_balance,
                'received': received,
                'sold': sold,
                'balance': balance,
                'has_opening_count': last_count is not None,
                'is_low': balance < (sku.minimum_stock_level / len(flavors)) if flavors else False
            })
            
            total_opening += opening_balance
            total_received += received
            total_sold += sold
        
        # Sort by balance (lowest first)
        flavor_data.sort(key=lambda x: x['balance'])
        
        return {
            'sku': sku,
            'sku_code': sku.sku_code,
            'size': sku.size,
            'marked_price': sku.marked_price,
            'total_stock': sku.quantity_in_stock,
            'total_opening': total_opening,
            'total_received': total_received,
            'total_sold': total_sold,
            'calculated_stock': total_opening + total_received - total_sold,
            'stock_variance': sku.quantity_in_stock - (total_opening + total_received - total_sold),
            'flavors': flavor_data,
        }
    
    @staticmethod
    def get_all_balances(company=None, start_date=None, end_date=None):
        """
        Get flavor balances for all SKUs using monthly count formula
        
        Args:
            company: Optional Company instance to filter by
            start_date: Start of period (defaults to first day of current month)
            end_date: End of period (defaults to today)
            
        Returns:
            list of SKU balance dictionaries
        """
        # Default to current month if not specified
        if not start_date:
            today = date.today()
            start_date = today.replace(day=1)
        if not end_date:
            end_date = date.today()
        
        if company:
            skus = StockKeepingUnit.objects.filter(company=company, is_active=True)
        else:
            skus = StockKeepingUnit.objects.filter(is_active=True)
        
        results = []
        for sku in skus:
            balance_data = FlavorBalanceReport.get_balance_by_sku(sku, start_date, end_date)
            # Only include SKUs that have flavor tracking
            if balance_data['flavors']:
                results.append(balance_data)
        
        return results
    def get_low_stock_flavors(company=None, threshold_percentage=20):
        """
        Get flavors that are running low on stock
        
        Args:
            company: Optional Company instance
            threshold_percentage: Stock level below this % of minimum triggers alert
            
        Returns:
            list of low stock flavor items
        """
        all_balances = FlavorBalanceReport.get_all_balances(company)
        low_stock = []
        
        for sku_data in all_balances:
            sku = sku_data['sku']
            # Calculate threshold per flavor
            per_flavor_threshold = (sku.minimum_stock_level * threshold_percentage) / 100
            
            for flavor_data in sku_data['flavors']:
                if flavor_data['balance'] <= per_flavor_threshold:
                    low_stock.append({
                        'sku': sku,
                        'sku_code': sku_data['sku_code'],
                        'size': sku_data['size'],
                        'marked_price': sku_data['marked_price'],
                        'flavor': flavor_data['flavor'],
                        'balance': flavor_data['balance'],
                        'sold': flavor_data['sold'],
                        'threshold': per_flavor_threshold,
                        'suggested_order': max(50, flavor_data['sold'])  # Suggest based on sales
                    })
        
        # Sort by balance (most urgent first)
        low_stock.sort(key=lambda x: x['balance'])
        
        return low_stock
    
    @staticmethod
    def get_reorder_recommendations(company=None):
        """
        Get intelligent reorder recommendations based on sales velocity
        
        Args:
            company: Optional Company instance
            
        Returns:
            list of reorder recommendations
        """
        all_balances = FlavorBalanceReport.get_all_balances(company)
        recommendations = []
        
        for sku_data in all_balances:
            sku = sku_data['sku']
            
            for flavor_data in sku_data['flavors']:
                balance = flavor_data['balance']
                sold = flavor_data['sold']
                
                # Calculate suggested order quantity
                # If sold a lot, order more. If balance low, order urgently
                if sold > 0:
                    # Order enough for estimated next period based on sales
                    suggested_qty = max(sold, 50)  # Minimum 50 bottles
                    
                    # Adjust based on current balance
                    if balance < 20:
                        urgency = 'HIGH'
                        suggested_qty = int(suggested_qty * 1.5)  # Order extra
                    elif balance < 50:
                        urgency = 'MEDIUM'
                    else:
                        urgency = 'LOW'
                        suggested_qty = int(suggested_qty * 0.8)  # Order less
                    
                    recommendations.append({
                        'sku': sku,
                        'sku_code': sku_data['sku_code'],
                        'size': sku_data['size'],
                        'marked_price': sku_data['marked_price'],
                        'flavor': flavor_data['flavor'],
                        'current_balance': balance,
                        'total_sold': sold,
                        'urgency': urgency,
                        'suggested_order_qty': suggested_qty,
                    })
        
        # Sort by urgency (HIGH first) then by balance (lowest first)
        urgency_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        recommendations.sort(key=lambda x: (urgency_order[x['urgency']], x['current_balance']))
        
        return recommendations
