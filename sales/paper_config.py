"""
World-Class Paper Size Specifications and Receipt Optimization Utilities

This module provides comprehensive paper size configurations and receipt optimization
functionality for thermal and standard printers, matching industry best practices
from leading POS systems (Square, Toast, Shopify, Clover).
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PaperSizeSpecs:
    """Complete specifications for a paper size"""
    # Identifiers
    code: str
    display_name: str
    category: str  # 'thermal' or 'standard'
    
    # Dimensions
    width_mm: float
    width_inch: float
    printable_width_mm: float
    
    # Character specifications
    chars_per_line_normal: int  # 12 CPI
    chars_per_line_condensed: int  # 16 CPI
    
    # Printer specifications
    escpos_width_dots: Optional[int]  # For thermal printers
    dpi: int  # Dots per inch
    
    # Optimal font sizes (in points)
    font_header_min: int
    font_header_max: int
    font_header_optimal: int
    font_body_min: int
    font_body_max: int
    font_body_optimal: int
    font_footer_min: int
    font_footer_max: int
    font_footer_optimal: int
    
    # Logo specifications (in pixels)
    logo_max_width: int
    logo_max_height: int
    
    # QR Code / Barcode specifications
    qr_code_size: int
    barcode_width: int
    barcode_height: int
    
    # Margins (in mm)
    margin_top: int
    margin_bottom: int
    margin_left: int
    margin_right: int
    
    # Print settings
    optimal_density: int  # 0-100
    feed_lines_small: int  # For receipts < 10 items
    feed_lines_medium: int  # For receipts 10-20 items
    feed_lines_large: int  # For receipts > 20 items
    
    # Layout proportions (percentage)
    header_proportion: float  # 0.20 = 20%
    body_proportion: float
    footer_proportion: float


class PaperSizeConfig:
    """
    Paper size configuration manager with industry-standard specifications.
    
    Provides detailed specifications for all supported paper sizes, matching
    commercial POS system standards.
    """
    
    PAPER_SIZES = {
        'thermal_2inch': PaperSizeSpecs(
            code='thermal_2inch',
            display_name='Thermal 2" (50.8mm)',
            category='thermal',
            width_mm=50.8,
            width_inch=2.0,
            printable_width_mm=48,
            chars_per_line_normal=32,
            chars_per_line_condensed=40,
            escpos_width_dots=384,
            dpi=203,
            font_header_min=10,
            font_header_max=14,
            font_header_optimal=12,
            font_body_min=7,
            font_body_max=10,
            font_body_optimal=8,
            font_footer_min=6,
            font_footer_max=9,
            font_footer_optimal=7,
            logo_max_width=150,
            logo_max_height=80,
            qr_code_size=100,
            barcode_width=150,
            barcode_height=50,
            margin_top=2,
            margin_bottom=5,
            margin_left=2,
            margin_right=2,
            optimal_density=55,
            feed_lines_small=2,
            feed_lines_medium=3,
            feed_lines_large=4,
            header_proportion=0.25,
            body_proportion=0.55,
            footer_proportion=0.20,
        ),
        'thermal_48mm': PaperSizeSpecs(
            code='thermal_48mm',
            display_name='Thermal 48mm',
            category='thermal',
            width_mm=48,
            width_inch=1.89,
            printable_width_mm=44,
            chars_per_line_normal=28,
            chars_per_line_condensed=36,
            escpos_width_dots=384,
            dpi=203,
            font_header_min=9,
            font_header_max=13,
            font_header_optimal=11,
            font_body_min=7,
            font_body_max=9,
            font_body_optimal=8,
            font_footer_min=6,
            font_footer_max=8,
            font_footer_optimal=7,
            logo_max_width=140,
            logo_max_height=70,
            qr_code_size=90,
            barcode_width=140,
            barcode_height=45,
            margin_top=2,
            margin_bottom=5,
            margin_left=2,
            margin_right=2,
            optimal_density=55,
            feed_lines_small=2,
            feed_lines_medium=3,
            feed_lines_large=4,
            header_proportion=0.25,
            body_proportion=0.55,
            footer_proportion=0.20,
        ),
        'thermal_58mm': PaperSizeSpecs(
            code='thermal_58mm',
            display_name='Thermal 58mm',
            category='thermal',
            width_mm=58,
            width_inch=2.28,
            printable_width_mm=54,
            chars_per_line_normal=32,
            chars_per_line_condensed=42,
            escpos_width_dots=384,
            dpi=203,
            font_header_min=11,
            font_header_max=15,
            font_header_optimal=13,
            font_body_min=8,
            font_body_max=11,
            font_body_optimal=9,
            font_footer_min=7,
            font_footer_max=10,
            font_footer_optimal=8,
            logo_max_width=180,
            logo_max_height=90,
            qr_code_size=110,
            barcode_width=170,
            barcode_height=55,
            margin_top=2,
            margin_bottom=5,
            margin_left=2,
            margin_right=2,
            optimal_density=55,
            feed_lines_small=2,
            feed_lines_medium=3,
            feed_lines_large=4,
            header_proportion=0.25,
            body_proportion=0.55,
            footer_proportion=0.20,
        ),
        'thermal_3inch': PaperSizeSpecs(
            code='thermal_3inch',
            display_name='Thermal 3" (76.2mm)',
            category='thermal',
            width_mm=76.2,
            width_inch=3.0,
            printable_width_mm=72,
            chars_per_line_normal=48,
            chars_per_line_condensed=56,
            escpos_width_dots=576,
            dpi=203,
            font_header_min=13,
            font_header_max=17,
            font_header_optimal=15,
            font_body_min=9,
            font_body_max=13,
            font_body_optimal=11,
            font_footer_min=8,
            font_footer_max=11,
            font_footer_optimal=9,
            logo_max_width=240,
            logo_max_height=110,
            qr_code_size=140,
            barcode_width=220,
            barcode_height=65,
            margin_top=3,
            margin_bottom=5,
            margin_left=3,
            margin_right=3,
            optimal_density=55,
            feed_lines_small=3,
            feed_lines_medium=4,
            feed_lines_large=5,
            header_proportion=0.22,
            body_proportion=0.58,
            footer_proportion=0.20,
        ),
        'thermal_80mm': PaperSizeSpecs(
            code='thermal_80mm',
            display_name='Thermal 80mm',
            category='thermal',
            width_mm=80,
            width_inch=3.15,
            printable_width_mm=76,
            chars_per_line_normal=48,
            chars_per_line_condensed=60,
            escpos_width_dots=576,
            dpi=203,
            font_header_min=13,
            font_header_max=18,
            font_header_optimal=16,
            font_body_min=9,
            font_body_max=13,
            font_body_optimal=11,
            font_footer_min=8,
            font_footer_max=11,
            font_footer_optimal=9,
            logo_max_width=260,
            logo_max_height=120,
            qr_code_size=150,
            barcode_width=240,
            barcode_height=70,
            margin_top=3,
            margin_bottom=5,
            margin_left=3,
            margin_right=3,
            optimal_density=55,
            feed_lines_small=3,
            feed_lines_medium=4,
            feed_lines_large=5,
            header_proportion=0.22,
            body_proportion=0.58,
            footer_proportion=0.20,
        ),
        'thermal_4inch': PaperSizeSpecs(
            code='thermal_4inch',
            display_name='Thermal 4" (101.6mm)',
            category='thermal',
            width_mm=101.6,
            width_inch=4.0,
            printable_width_mm=96,
            chars_per_line_normal=64,
            chars_per_line_condensed=80,
            escpos_width_dots=832,
            dpi=203,
            font_header_min=15,
            font_header_max=20,
            font_header_optimal=18,
            font_body_min=10,
            font_body_max=14,
            font_body_optimal=12,
            font_footer_min=9,
            font_footer_max=12,
            font_footer_optimal=10,
            logo_max_width=340,
            logo_max_height=140,
            qr_code_size=180,
            barcode_width=280,
            barcode_height=80,
            margin_top=3,
            margin_bottom=5,
            margin_left=4,
            margin_right=4,
            optimal_density=55,
            feed_lines_small=3,
            feed_lines_medium=4,
            feed_lines_large=5,
            header_proportion=0.20,
            body_proportion=0.60,
            footer_proportion=0.20,
        ),
        'a4': PaperSizeSpecs(
            code='a4',
            display_name='A4 Paper (210mm)',
            category='standard',
            width_mm=210,
            width_inch=8.27,
            printable_width_mm=190,
            chars_per_line_normal=80,
            chars_per_line_condensed=95,
            escpos_width_dots=None,
            dpi=300,
            font_header_min=16,
            font_header_max=24,
            font_header_optimal=20,
            font_body_min=10,
            font_body_max=14,
            font_body_optimal=12,
            font_footer_min=9,
            font_footer_max=12,
            font_footer_optimal=10,
            logo_max_width=450,
            logo_max_height=180,
            qr_code_size=200,
            barcode_width=350,
            barcode_height=100,
            margin_top=10,
            margin_bottom=10,
            margin_left=10,
            margin_right=10,
            optimal_density=60,
            feed_lines_small=0,
            feed_lines_medium=0,
            feed_lines_large=0,
            header_proportion=0.18,
            body_proportion=0.64,
            footer_proportion=0.18,
        ),
        'a5': PaperSizeSpecs(
            code='a5',
            display_name='A5 Paper (148mm)',
            category='standard',
            width_mm=148,
            width_inch=5.83,
            printable_width_mm=132,
            chars_per_line_normal=55,
            chars_per_line_condensed=65,
            escpos_width_dots=None,
            dpi=300,
            font_header_min=14,
            font_header_max=20,
            font_header_optimal=17,
            font_body_min=9,
            font_body_max=13,
            font_body_optimal=11,
            font_footer_min=8,
            font_footer_max=11,
            font_footer_optimal=9,
            logo_max_width=350,
            logo_max_height=140,
            qr_code_size=160,
            barcode_width=280,
            barcode_height=80,
            margin_top=8,
            margin_bottom=8,
            margin_left=8,
            margin_right=8,
            optimal_density=60,
            feed_lines_small=0,
            feed_lines_medium=0,
            feed_lines_large=0,
            header_proportion=0.20,
            body_proportion=0.62,
            footer_proportion=0.18,
        ),
        'letter': PaperSizeSpecs(
            code='letter',
            display_name='Letter Size (8.5")',
            category='standard',
            width_mm=215.9,
            width_inch=8.5,
            printable_width_mm=196,
            chars_per_line_normal=82,
            chars_per_line_condensed=98,
            escpos_width_dots=None,
            dpi=300,
            font_header_min=16,
            font_header_max=24,
            font_header_optimal=20,
            font_body_min=10,
            font_body_max=14,
            font_body_optimal=12,
            font_footer_min=9,
            font_footer_max=12,
            font_footer_optimal=10,
            logo_max_width=460,
            logo_max_height=185,
            qr_code_size=210,
            barcode_width=360,
            barcode_height=105,
            margin_top=10,
            margin_bottom=10,
            margin_left=10,
            margin_right=10,
            optimal_density=60,
            feed_lines_small=0,
            feed_lines_medium=0,
            feed_lines_large=0,
            header_proportion=0.18,
            body_proportion=0.64,
            footer_proportion=0.18,
        ),
    }
    
    # Django model choices
    PAPER_SIZE_CHOICES = tuple(
        (code, specs.display_name)
        for code, specs in PAPER_SIZES.items()
    )
    
    @classmethod
    def get_specs(cls, paper_size_code: str) -> Optional[PaperSizeSpecs]:
        """Get specifications for a paper size"""
        return cls.PAPER_SIZES.get(paper_size_code)
    
    @classmethod
    def get_all_thermal_sizes(cls) -> Dict[str, PaperSizeSpecs]:
        """Get all thermal paper sizes"""
        return {
            code: specs
            for code, specs in cls.PAPER_SIZES.items()
            if specs.category == 'thermal'
        }
    
    @classmethod
    def get_all_standard_sizes(cls) -> Dict[str, PaperSizeSpecs]:
        """Get all standard paper sizes"""
        return {
            code: specs
            for code, specs in cls.PAPER_SIZES.items()
            if specs.category == 'standard'
        }
    
    @classmethod
    def is_thermal(cls, paper_size_code: str) -> bool:
        """Check if paper size is thermal"""
        specs = cls.get_specs(paper_size_code)
        return specs.category == 'thermal' if specs else False
    
    @classmethod
    def get_optimal_fonts(cls, paper_size_code: str) -> Dict[str, int]:
        """Get optimal font sizes for a paper size"""
        specs = cls.get_specs(paper_size_code)
        if not specs:
            return {'header': 14, 'body': 10, 'footer': 8}
        
        return {
            'header': specs.font_header_optimal,
            'body': specs.font_body_optimal,
            'footer': specs.font_footer_optimal,
        }
    
    @classmethod
    def get_font_ranges(cls, paper_size_code: str) -> Dict[str, Tuple[int, int]]:
        """Get font size ranges for a paper size"""
        specs = cls.get_specs(paper_size_code)
        if not specs:
            return {
                'header': (12, 18),
                'body': (8, 12),
                'footer': (7, 10),
            }
        
        return {
            'header': (specs.font_header_min, specs.font_header_max),
            'body': (specs.font_body_min, specs.font_body_max),
            'footer': (specs.font_footer_min, specs.font_footer_max),
        }
    
    @classmethod
    def get_logo_size(cls, paper_size_code: str) -> Tuple[int, int]:
        """Get maximum logo size (width, height) in pixels"""
        specs = cls.get_specs(paper_size_code)
        if not specs:
            return (220, 100)
        return (specs.logo_max_width, specs.logo_max_height)
    
    @classmethod
    def get_char_limit(cls, paper_size_code: str, condensed: bool = False) -> int:
        """Get character limit per line"""
        specs = cls.get_specs(paper_size_code)
        if not specs:
            return 48
        return specs.chars_per_line_condensed if condensed else specs.chars_per_line_normal
    
    @classmethod
    def get_feed_lines(cls, paper_size_code: str, item_count: int) -> int:
        """Get optimal feed lines based on receipt size"""
        specs = cls.get_specs(paper_size_code)
        if not specs:
            return 3
        
        if item_count < 10:
            return specs.feed_lines_small
        elif item_count <= 20:
            return specs.feed_lines_medium
        else:
            return specs.feed_lines_large
    
    @classmethod
    def get_margins(cls, paper_size_code: str) -> Dict[str, int]:
        """Get optimal margins in mm"""
        specs = cls.get_specs(paper_size_code)
        if not specs:
            return {'top': 5, 'bottom': 5, 'left': 5, 'right': 5}
        
        return {
            'top': specs.margin_top,
            'bottom': specs.margin_bottom,
            'left': specs.margin_left,
            'right': specs.margin_right,
        }
    
    @classmethod
    def validate_font_size(cls, paper_size_code: str, font_type: str, font_size: int) -> bool:
        """Validate if font size is within acceptable range"""
        ranges = cls.get_font_ranges(paper_size_code)
        if font_type not in ranges:
            return True
        
        min_size, max_size = ranges[font_type]
        return min_size <= font_size <= max_size
    
    @classmethod
    def get_css_page_size(cls, paper_size_code: str) -> str:
        """Generate CSS @page size declaration"""
        specs = cls.get_specs(paper_size_code)
        if not specs:
            return "80mm auto"
        
        if specs.category == 'thermal':
            return f"{specs.width_mm}mm auto"
        else:
            return specs.code.upper()  # 'A4', 'A5', or custom
    
    @classmethod
    def get_css_margins(cls, paper_size_code: str) -> str:
        """Generate CSS margin declaration"""
        margins = cls.get_margins(paper_size_code)
        return f"{margins['top']}mm {margins['right']}mm {margins['bottom']}mm {margins['left']}mm"
    
    @classmethod
    def get_thermal_width_css(cls, paper_size_code: str) -> str:
        """Get max-width CSS for thermal receipts"""
        specs = cls.get_specs(paper_size_code)
        if not specs or specs.category != 'thermal':
            return "80mm"
        return f"{specs.width_mm}mm"
