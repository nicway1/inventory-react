#!/usr/bin/env python3
"""
Barcode Generator for Asset Labels
Generates barcodes and printable labels for assets with serial numbers and company information.
"""

import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from flask import render_template_string
import os

class AssetBarcodeGenerator:
    """Generate barcodes and labels for assets"""
    
    def __init__(self):
        self.barcode_format = 'code128'  # Using Code 128 format for alphanumeric support
        # Label size: 5cm x 9cm (portrait orientation)
        # At ~150 DPI: 5cm = 295px, 9cm = 531px
        self.label_width = 295
        self.label_height = 531
    
    def generate_barcode_image(self, serial_number):
        """
        Generate a barcode image for the given serial number
        
        Args:
            serial_number (str): The serial number to encode
            
        Returns:
            PIL.Image: Barcode image
        """
        try:
            # Create barcode
            barcode_class = barcode.get_barcode_class(self.barcode_format)
            barcode_instance = barcode_class(serial_number, writer=ImageWriter())
            
            # Generate barcode image in memory
            buffer = io.BytesIO()
            barcode_instance.write(buffer, options={
                'module_width': 0.2,
                'module_height': 15.0,
                'quiet_zone': 6.5,
                'font_size': 10,
                'text_distance': 5.0,
                'background': 'white',
                'foreground': 'black',
            })
            buffer.seek(0)
            
            return Image.open(buffer)
            
        except Exception as e:
            logger.info("Error generating barcode for {serial_number}: {str(e)}")
            return None
    
    def generate_asset_label(self, asset):
        """
        Generate a complete asset label with barcode, serial number, asset tag, and company info

        Args:
            asset: Asset object with serial_num, asset_tag, company, etc.

        Returns:
            PIL.Image: Complete label image
        """
        try:
            # Generate barcode using serial number
            barcode_image = self.generate_barcode_image(asset.serial_num)
            if not barcode_image:
                return None

            # Create label canvas
            label = Image.new('RGB', (self.label_width, self.label_height), 'white')
            draw = ImageDraw.Draw(label)

            # Try to load fonts, fall back to default if not available
            try:
                # Try different font paths for different systems
                font_paths = [
                    "/System/Library/Fonts/Arial.ttf",  # macOS
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux alt
                    "C:/Windows/Fonts/arial.ttf",  # Windows
                ]
                title_font = None
                for font_path in font_paths:
                    try:
                        title_font = ImageFont.truetype(font_path, 18)
                        text_font = ImageFont.truetype(font_path, 14)
                        label_font = ImageFont.truetype(font_path, 12)
                        break
                    except:
                        continue

                if not title_font:
                    raise Exception("No font found")
            except:
                # Fallback to default font
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
                label_font = ImageFont.load_default()

            # Calculate positions
            y_offset = 12

            # Add company name at the top
            company_name = "Unknown Company"
            if hasattr(asset, 'company') and asset.company:
                company_name = asset.company.grouped_display_name
            elif hasattr(asset, 'customer') and asset.customer:
                company_name = asset.customer

            # Truncate company name if too long for label width
            max_chars = 25  # Approximate max chars for 295px width
            if len(company_name) > max_chars:
                company_name = company_name[:max_chars-3] + "..."

            # Draw company name (centered)
            company_bbox = draw.textbbox((0, 0), company_name, font=title_font)
            company_width = company_bbox[2] - company_bbox[0]
            draw.text(((self.label_width - company_width) // 2, y_offset),
                     company_name, fill='black', font=title_font)
            y_offset += 28

            # Draw a thin separator line
            draw.line([(20, y_offset), (self.label_width - 20, y_offset)], fill='gray', width=1)
            y_offset += 10

            # Add Asset Tag (if exists)
            if asset.asset_tag:
                asset_tag_text = f"Asset Tag: {asset.asset_tag}"
                tag_bbox = draw.textbbox((0, 0), asset_tag_text, font=text_font)
                tag_width = tag_bbox[2] - tag_bbox[0]
                draw.text(((self.label_width - tag_width) // 2, y_offset),
                         asset_tag_text, fill='black', font=text_font)
                y_offset += 22

            # Add Serial Number text
            serial_text = f"S/N: {asset.serial_num}"
            serial_bbox = draw.textbbox((0, 0), serial_text, font=text_font)
            serial_width = serial_bbox[2] - serial_bbox[0]
            draw.text(((self.label_width - serial_width) // 2, y_offset),
                     serial_text, fill='black', font=text_font)
            y_offset += 25

            # Add barcode (fit within label width with padding)
            barcode_width = self.label_width - 30  # 15px padding on each side
            barcode_height = 60
            barcode_resized = barcode_image.resize((barcode_width, barcode_height))
            barcode_x = (self.label_width - barcode_width) // 2
            label.paste(barcode_resized, (barcode_x, y_offset))
            y_offset += barcode_height + 10

            # Add product name at bottom if space allows
            if hasattr(asset, 'name') and asset.name and y_offset < self.label_height - 25:
                product_name = asset.name[:28] + "..." if len(asset.name) > 28 else asset.name
                name_bbox = draw.textbbox((0, 0), product_name, font=label_font)
                name_width = name_bbox[2] - name_bbox[0]
                draw.text(((self.label_width - name_width) // 2, y_offset),
                         product_name, fill='gray', font=label_font)

            # Add border
            draw.rectangle([0, 0, self.label_width-1, self.label_height-1],
                          outline='black', width=2)

            return label

        except Exception as e:
            print(f"Error generating asset label: {str(e)}")
            return None
    
    def generate_barcode_base64(self, serial_number):
        """
        Generate a barcode and return as base64 string for web display
        
        Args:
            serial_number (str): The serial number to encode
            
        Returns:
            str: Base64 encoded image data
        """
        try:
            barcode_image = self.generate_barcode_image(serial_number)
            if not barcode_image:
                return None
            
            # Convert to base64
            buffer = io.BytesIO()
            barcode_image.save(buffer, format='PNG')
            buffer.seek(0)
            
            img_data = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_data}"
            
        except Exception as e:
            logger.info("Error generating base64 barcode: {str(e)}")
            return None
    
    def generate_label_base64(self, asset):
        """
        Generate a complete asset label and return as base64 string for web display
        
        Args:
            asset: Asset object
            
        Returns:
            str: Base64 encoded image data
        """
        try:
            label_image = self.generate_asset_label(asset)
            if not label_image:
                return None
            
            # Convert to base64
            buffer = io.BytesIO()
            label_image.save(buffer, format='PNG')
            buffer.seek(0)
            
            img_data = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_data}"
            
        except Exception as e:
            logger.info("Error generating base64 label: {str(e)}")
            return None
    
    def save_label_to_file(self, asset, filepath):
        """
        Generate and save asset label to file
        
        Args:
            asset: Asset object
            filepath (str): Path to save the image file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            label_image = self.generate_asset_label(asset)
            if not label_image:
                return False
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            label_image.save(filepath, format='PNG')
            return True
            
        except Exception as e:
            logger.info("Error saving label to file: {str(e)}")
            return False

# Global instance
barcode_generator = AssetBarcodeGenerator() 