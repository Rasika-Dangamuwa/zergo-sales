"""
Receipt Optimization Engine

Dynamically optimizes receipt layout, fonts, logos, and content based on selected
paper size, matching world-class POS system standards.
"""

from typing import Dict, List, Optional, Any
from .paper_config import PaperSizeConfig, PaperSizeSpecs


class ReceiptOptimizer:
    """
    World-class receipt optimization engine.
    
    Automatically adjusts receipt layout, fonts, logos, and content to perfectly
    fit the selected paper size, preventing overflow and ensuring professional output.
    """
    
    def __init__(self, paper_size_code: str):
        """
        Initialize optimizer for specific paper size.
        
        Args:
            paper_size_code: Paper size code (e.g., 'thermal_80mm', 'a4')
        """
        self.paper_size_code = paper_size_code
        self.specs = PaperSizeConfig.get_specs(paper_size_code)
        
        if not self.specs:
            # Fallback to 80mm if invalid paper size
            self.paper_size_code = 'thermal_80mm'
            self.specs = PaperSizeConfig.get_specs('thermal_80mm')
    
    def get_optimized_settings(self, item_count: int = 10) -> Dict[str, Any]:
        """
        Get complete optimized settings for a receipt.
        
        Args:
            item_count: Number of line items in receipt
        
        Returns:
            Dictionary with all optimized settings
        """
        return {
            'paper_size': {
                'code': self.specs.code,
                'name': self.specs.display_name,
                'category': self.specs.category,
                'width_mm': self.specs.width_mm,
                'width_inch': self.specs.width_inch,
                'printable_mm': self.specs.printable_width_mm,
                'chars_per_line': self.specs.chars_per_line_normal,
            },
            'fonts': self.get_font_sizes(),
            'logo': self.get_logo_config(),
            'qr_barcode': self.get_qr_barcode_config(),
            'margins': self.get_margin_config(),
            'layout': self.get_layout_config(),
            'print_settings': self.get_print_settings(item_count),
            'css': self.generate_css(),
            'character_limits': self.get_character_limits(),
        }
    
    def get_font_sizes(self) -> Dict[str, Dict[str, int]]:
        """Get optimized font sizes with min/max ranges"""
        return {
            'header': {
                'optimal': self.specs.font_header_optimal,
                'min': self.specs.font_header_min,
                'max': self.specs.font_header_max,
            },
            'body': {
                'optimal': self.specs.font_body_optimal,
                'min': self.specs.font_body_min,
                'max': self.specs.font_body_max,
            },
            'footer': {
                'optimal': self.specs.font_footer_optimal,
                'min': self.specs.font_footer_min,
                'max': self.specs.font_footer_max,
            },
        }
    
    def get_logo_config(self) -> Dict[str, int]:
        """Get optimal logo configuration"""
        return {
            'max_width': self.specs.logo_max_width,
            'max_height': self.specs.logo_max_height,
            'max_width_mm': int(self.specs.printable_width_mm * 0.7),  # 70% of printable width
        }
    
    def get_qr_barcode_config(self) -> Dict[str, int]:
        """Get optimal QR code and barcode sizing"""
        return {
            'qr_size': self.specs.qr_code_size,
            'barcode_width': self.specs.barcode_width,
            'barcode_height': self.specs.barcode_height,
        }
    
    def get_margin_config(self) -> Dict[str, int]:
        """Get optimal margins"""
        return {
            'top': self.specs.margin_top,
            'bottom': self.specs.margin_bottom,
            'left': self.specs.margin_left,
            'right': self.specs.margin_right,
        }
    
    def get_layout_config(self) -> Dict[str, Any]:
        """Get layout proportions and spacing"""
        return {
            'header_proportion': self.specs.header_proportion,
            'body_proportion': self.specs.body_proportion,
            'footer_proportion': self.specs.footer_proportion,
            'is_thermal': self.specs.category == 'thermal',
            'is_narrow': self.specs.width_mm < 70,  # < 70mm is narrow
        }
    
    def get_print_settings(self, item_count: int) -> Dict[str, Any]:
        """Get optimal print settings"""
        settings = {
            'density': self.specs.optimal_density,
            'feed_lines': PaperSizeConfig.get_feed_lines(self.paper_size_code, item_count),
        }
        
        if self.specs.category == 'thermal':
            settings['cut_after_print'] = True
            settings['escpos_width'] = self.specs.escpos_width_dots
        
        return settings
    
    def get_character_limits(self) -> Dict[str, int]:
        """Get character limits for different line types"""
        normal = self.specs.chars_per_line_normal
        condensed = self.specs.chars_per_line_condensed
        
        return {
            'normal': normal,
            'condensed': condensed,
            'company_name': normal - 4,  # Account for borders/padding
            'line_item_name': int(normal * 0.6),  # 60% for product name
            'line_item_price': int(normal * 0.3),  # 30% for price
            'address_line': normal - 2,
        }
    
    def generate_css(self) -> str:
        """Generate optimized CSS for this paper size"""
        margins = self.get_margin_config()
        fonts = self.get_font_sizes()
        
        css = f"""
/* Optimized for {self.specs.display_name} */
@page {{
    size: {PaperSizeConfig.get_css_page_size(self.paper_size_code)};
    margin: {margins['top']}mm {margins['right']}mm {margins['bottom']}mm {margins['left']}mm;
}}

body {{
    font-family: 'Courier New', monospace;
    font-size: {fonts['body']['optimal']}pt;
    line-height: 1.3;
    max-width: {self.specs.printable_width_mm}mm;
    margin: 0 auto;
}}

.thermal-receipt {{
    width: 100%;
    max-width: {self.specs.width_mm}mm;
    margin: 0 auto;
    font-size: {fonts['body']['optimal']}pt;
}}

.thermal-header,
.receipt-header {{
    font-size: {fonts['header']['optimal']}pt;
    font-weight: bold;
    text-align: center;
}}

.company-name {{
    font-size: {fonts['header']['optimal']}pt;
    font-weight: bold;
}}

.company-logo {{
    max-width: {self.specs.logo_max_width}px;
    max-height: {self.specs.logo_max_height}px;
    width: auto;
    height: auto;
    display: block;
    margin: 0 auto;
}}

.line-item {{
    font-size: {fonts['body']['optimal']}pt;
}}

.footer-text,
.thermal-footer {{
    font-size: {fonts['footer']['optimal']}pt;
    text-align: center;
}}

.qr-code {{
    width: {self.specs.qr_code_size}px;
    height: {self.specs.qr_code_size}px;
}}

.barcode {{
    width: {self.specs.barcode_width}px;
    height: {self.specs.barcode_height}px;
}}

/* Character width optimization */
.full-width {{
    max-width: {self.specs.chars_per_line_normal}ch;
}}
"""
        
        return css.strip()
    
    def wrap_text(self, text: str, max_chars: Optional[int] = None, line_type: str = 'normal') -> List[str]:
        """
        Wrap text to fit within character limit.
        
        Args:
            text: Text to wrap
            max_chars: Maximum characters per line (None = use optimal for paper)
            line_type: Type of line ('normal', 'company_name', 'address_line', etc.)
        
        Returns:
            List of wrapped lines
        """
        if max_chars is None:
            limits = self.get_character_limits()
            max_chars = limits.get(line_type, limits['normal'])
        
        if len(text) <= max_chars:
            return [text]
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            space_length = 1 if current_line else 0
            
            if current_length + space_length + word_length <= max_chars:
                current_line.append(word)
                current_length += space_length + word_length
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def truncate_text(self, text: str, max_chars: Optional[int] = None, line_type: str = 'normal', ellipsis: bool = True) -> str:
        """
        Truncate text to fit within character limit.
        
        Args:
            text: Text to truncate
            max_chars: Maximum characters (None = use optimal for paper)
            line_type: Type of line
            ellipsis: Add '...' if truncated
        
        Returns:
            Truncated text
        """
        if max_chars is None:
            limits = self.get_character_limits()
            max_chars = limits.get(line_type, limits['normal'])
        
        if len(text) <= max_chars:
            return text
        
        if ellipsis and max_chars > 3:
            return text[:max_chars-3] + '...'
        
        return text[:max_chars]
    
    def format_line_item(self, name: str, quantity: int, price: float, total: float) -> str:
        """
        Format a line item to fit perfectly within paper width.
        
        Args:
            name: Product name
            quantity: Quantity
            price: Unit price
            total: Total price
        
        Returns:
            Formatted line string
        """
        limits = self.get_character_limits()
        total_chars = limits['normal']
        
        # Format prices
        price_str = f"Rs.{price:,.2f}"
        total_str = f"Rs.{total:,.2f}"
        qty_str = f"{quantity}x"
        
        # Calculate space for name
        right_side = f" {qty_str} @ {price_str} = {total_str}"
        name_space = total_chars - len(right_side)
        
        # Truncate name if needed
        if len(name) > name_space:
            name = name[:name_space-3] + '...'
        else:
            name = name.ljust(name_space)
        
        return name + right_side
    
    def format_total_line(self, label: str, amount: float) -> str:
        """
        Format a total/summary line (e.g., "Total:", "Tax:", etc.)
        
        Args:
            label: Line label
            amount: Amount value
        
        Returns:
            Formatted line string
        """
        limits = self.get_character_limits()
        total_chars = limits['normal']
        
        amount_str = f"Rs.{amount:,.2f}"
        space_between = total_chars - len(label) - len(amount_str)
        
        # At minimum, have 2 spaces
        if space_between < 2:
            space_between = 2
            # Truncate label if needed
            max_label = total_chars - len(amount_str) - 2
            if len(label) > max_label:
                label = label[:max_label]
        
        return label + (' ' * space_between) + amount_str
    
    def validate_content_fits(self, content_height_mm: float) -> Dict[str, Any]:
        """
        Validate if content will fit on the receipt.
        
        Args:
            content_height_mm: Estimated content height in millimeters
        
        Returns:
            Validation result with fit status and recommendations
        """
        # Thermal receipts are continuous, so height is flexible
        if self.specs.category == 'thermal':
            return {
                'fits': True,
                'has_warnings': False,
                'warnings': [],
                'recommendations': [],
            }
        
        # For standard paper, check if content fits
        # Assuming A4 = 297mm, A5 = 210mm, Letter = 279mm
        paper_heights = {
            'a4': 297,
            'a5': 210,
            'letter': 279,
        }
        
        paper_height = paper_heights.get(self.paper_size_code, 297)
        margins = self.get_margin_config()
        available_height = paper_height - margins['top'] - margins['bottom']
        
        fits = content_height_mm <= available_height
        overflow = max(0, content_height_mm - available_height)
        
        warnings = []
        recommendations = []
        
        if not fits:
            warnings.append(f"Content ({content_height_mm:.0f}mm) exceeds available height ({available_height:.0f}mm)")
            warnings.append(f"Content will overflow by approximately {overflow:.0f}mm")
            recommendations.append("Reduce font sizes")
            recommendations.append("Remove optional sections (logo, QR code, etc.)")
            recommendations.append("Consider using a larger paper size")
        
        return {
            'fits': fits,
            'has_warnings': len(warnings) > 0,
            'warnings': warnings,
            'recommendations': recommendations,
            'available_height_mm': available_height,
            'content_height_mm': content_height_mm,
            'overflow_mm': overflow,
        }
    
    def get_escpos_commands(self) -> Dict[str, str]:
        """
        Generate ESC/POS commands for thermal printers.
        
        Returns:
            Dictionary of ESC/POS command sequences
        """
        if self.specs.category != 'thermal':
            return {}
        
        return {
            'init': '\\x1B\\x40',  # Initialize printer
            'align_left': '\\x1B\\x61\\x00',
            'align_center': '\\x1B\\x61\\x01',
            'align_right': '\\x1B\\x61\\x02',
            'bold_on': '\\x1B\\x45\\x01',
            'bold_off': '\\x1B\\x45\\x00',
            'double_height': '\\x1B\\x21\\x10',
            'double_width': '\\x1B\\x21\\x20',
            'double_both': '\\x1B\\x21\\x30',
            'normal_size': '\\x1B\\x21\\x00',
            'feed_lines': f'\\x1B\\x64\\x{self.specs.feed_lines_medium:02X}',
            'cut_full': '\\x1D\\x56\\x00',
            'cut_partial': '\\x1D\\x56\\x01',
            'set_width': f'\\x1D\\x57\\x{self.specs.escpos_width_dots:04X}',
        }
    
    def get_template_context(self, item_count: int = 10) -> Dict[str, Any]:
        """
        Get optimized context for rendering templates.
        
        Args:
            item_count: Number of line items
        
        Returns:
            Template context dictionary
        """
        settings = self.get_optimized_settings(item_count)
        
        return {
            'optimizer': self,
            'paper_size': settings['paper_size'],
            'fonts': settings['fonts'],
            'logo_config': settings['logo'],
            'qr_config': settings['qr_barcode'],
            'margins': settings['margins'],
            'layout': settings['layout'],
            'print_settings': settings['print_settings'],
            'char_limits': settings['character_limits'],
            'css': settings['css'],
            'is_thermal': self.specs.category == 'thermal',
            'is_narrow': self.specs.width_mm < 70,
        }


# Convenience function for views
def get_optimized_receipt_context(paper_size_code: str, item_count: int = 10) -> Dict[str, Any]:
    """
    Get optimized receipt context for a specific paper size.
    
    Usage in views:
        context.update(get_optimized_receipt_context('thermal_80mm', len(items)))
    
    Args:
        paper_size_code: Paper size code
        item_count: Number of line items in receipt
    
    Returns:
        Optimized template context
    """
    optimizer = ReceiptOptimizer(paper_size_code)
    return optimizer.get_template_context(item_count)
