from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from utils.data_loader import SnipeITDataLoader
from utils.auth_decorators import admin_required
import os
import time
from werkzeug.utils import secure_filename
import pandas as pd

data_loader_bp = Blueprint('data_loader', __name__, url_prefix='/data-loader')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@data_loader_bp.route('/', methods=['GET', 'POST'])
@admin_required
def import_data():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded')
            return redirect(request.url)
            
        file = request.files['file']
        import_type = request.form.get('import_type')
        
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            try:
                # Save file with unique name to prevent conflicts
                filename = f"{int(time.time())}_{secure_filename(file.filename)}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # Read the CSV file for preview
                df = pd.read_csv(filepath)
                preview_data = []
                
                # Process each row for preview
                for index, row in df.iterrows():
                    # Clean NaN values
                    row_data = {k: ('' if pd.isna(v) else str(v).strip()) for k, v in row.items()}
                    
                    # Format product information
                    product_parts = []
                    if row_data.get('MODEL'):
                        product_parts.append(row_data['MODEL'])
                    if row_data.get('CPU TYPE'):
                        product_parts.append(row_data['CPU TYPE'])
                    if row_data.get('MEMORY'):
                        product_parts.append(f"{row_data['MEMORY']} RAM")
                    if row_data.get('HARDDRIVE'):
                        product_parts.append(row_data['HARDDRIVE'])
                    
                    # Create a clean product string
                    product_string = ' '.join([part for part in product_parts if part])
                    
                    preview_data.append({
                        'row_number': index + 2,
                        'basic_info': {
                            'Hardware Type': row_data.get('HARDWARE TYPE', '').upper() or 'APPLE',
                            'Product': product_string
                        }
                    })
                
                # Store preview data and file info in session
                session['preview_data'] = preview_data
                session['import_filepath'] = filepath
                session['import_type'] = import_type
                
                return render_template(
                    'data_loader/preview.html',
                    preview_data=preview_data,
                    filename=filename,
                    import_type=import_type,
                    total_rows=len(preview_data)
                )
                
            except Exception as e:
                flash(f'Error processing file: {str(e)}')
                if os.path.exists(filepath):
                    os.remove(filepath)
                return redirect(request.url)
                
        else:
            flash('Invalid file type. Please upload a CSV file.')
            return redirect(request.url)
            
    return render_template('data_loader/import.html')

@data_loader_bp.route('/confirm-import', methods=['POST'])
@admin_required
def confirm_import():
    try:
        file_path = request.form.get('file_path')
        import_type = request.form.get('import_type')
        
        if not file_path or not os.path.exists(file_path):
            flash('Original file no longer exists. Please upload again.')
            return redirect(url_for('data_loader.import_data'))
            
        # Process the actual import
        loader = SnipeITDataLoader()
        
        # Choose import method based on type
        if import_type == 'assets':
            results = loader.import_assets(file_path, dry_run=False)
        else:
            results = loader.import_accessories(file_path, dry_run=False)
        
        # Clean up the temporary file
        os.remove(file_path)
        
        # Add a flash message for feedback
        if results['successful'] > 0:
            flash(f'Successfully imported {results["successful"]} items.')
        if results['failed'] > 0:
            flash(f'Failed to import {results["failed"]} items.')
        
        return render_template(
            'data_loader/results.html',
            results=results,
            dry_run=False,
            import_complete=True
        )
        
    except Exception as e:
        print(f"Import error: {str(e)}")  # Add debug print
        flash(f'Error during import: {str(e)}')
        return redirect(url_for('data_loader.import_data')) 