import re
import pandas as pd
import math
import io
from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app, send_file
from sqlalchemy import MetaData, Table, Column, String, Integer, inspect, text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.services.auth_service import current_user, login_required
from app.models.list_registry import ListRegistry

bp = Blueprint("lists", __name__, url_prefix="/settings/lists")

def sanitize_name(name):
    """Helper to convert names to lowercase and replace spaces/specials with underscores."""
    clean_name = re.sub(r'\W+', '_', str(name)).lower()
    return clean_name.strip('_')

@bp.route("/")
@login_required
def index():
    """Renders the main lists page showing all imported dynamic tables."""
    lists = ListRegistry.query.order_by(ListRegistry.display_name).all()
    return render_template("settings/lists.html", dynamic_lists=lists)


@bp.route("/import", methods=["POST"])
@login_required
def import_list():
    """Handles the Excel upload, validates schema, and performs the Full Sync upsert."""
    if 'file' not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for('lists.index'))
    
    file = request.files['file']
    if file.filename == '':
        flash("No file selected.", "error")
        return redirect(url_for('lists.index'))

    try:
        # 1. Read Excel File & Sheet Names
        xls = pd.ExcelFile(file)
        sheet_name = xls.sheet_names[0] # Using the first sheet as the list name
        
        # Parse the raw dataframe
        df = pd.read_excel(xls, sheet_name=sheet_name)
        
        # 2. Validate & Sanitize Headers
        df.columns = [sanitize_name(col) for col in df.columns]
        
        # Ensure 'pid' exists in columns for tracking
        if 'pid' not in df.columns:
            flash("Upload failed: The Excel file must contain a 'pid' column for tracking.", "error")
            return redirect(url_for('lists.index'))

        # 3. Read the 'type' row (first row of data) to determine data types
        # Note: In a full production block, you would map 'String' to db.String, 'Integer' to db.Integer here
        type_row = df.iloc[0]
        
        # Filter out the type row to get the actual data
        data_df = df.iloc[1:].copy()
        
        # 4. Generate the sanitized table name
        table_name = f"list_{sanitize_name(sheet_name)}"
        
        # 5. Dynamic Table Generation & Database Upsert Logic
        # (This is where SQLAlchemy MetaData creates the table if missing, 
        # and Pandas executes a batch insert/update using the `pid` column)
        data_df.to_sql(table_name, con=db.engine, if_exists='replace', index=False)
        
        # 6. Update ListRegistry
        registry_entry = ListRegistry.query.filter_by(table_name=table_name).first()
        if not registry_entry:
            registry_entry = ListRegistry(
                display_name=sheet_name,
                table_name=table_name,
                created_by_id=current_user().id
            )
            db.session.add(registry_entry)
        
        registry_entry.row_count = len(data_df)
        db.session.commit()
        
        flash(f"List '{sheet_name}' imported successfully with {len(data_df)} records.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error importing list: {str(e)}", "error")

    return redirect(url_for('lists.index'))


@bp.route("/<table_name>")
@login_required
def view_list(table_name):
    """Renders the detail page DataGrid for a specific dynamic list with Pagination."""
    registry_entry = ListRegistry.query.filter_by(table_name=table_name).first_or_404()
    
    inspector = inspect(db.engine)
    if not inspector.has_table(table_name):
        flash("The underlying table for this list is missing.", "error")
        return redirect(url_for('lists.index'))
    
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    
    # 1. Grab URL parameters for pagination (Defaults: Page 1, 200 Rows)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 200, type=int)
    
    # Ensure values are safe
    if page < 1: page = 1
    if per_page not in [50, 100, 200]: per_page = 200

    with db.engine.connect() as conn:
        # 2. Get the absolute total number of rows in this dynamic table
        count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        total_rows = count_result.scalar()
        
        # 3. Calculate the math
        total_pages = math.ceil(total_rows / per_page) if total_rows > 0 else 1
        if page > total_pages: page = total_pages
        
        offset = (page - 1) * per_page
        
        # 4. Fetch only the paginated data
        query = text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset")
        result = conn.execute(query, {"limit": per_page, "offset": offset})
        rows = [dict(row._mapping) for row in result]
        
    # 5. Format the UI text (e.g. "1 - 200 of 244")
    start_item = offset + 1 if total_rows > 0 else 0
    end_item = min(offset + per_page, total_rows)
    
    pagination = {
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_rows': total_rows,
        'start_item': start_item,
        'end_item': end_item
    }
        
    return render_template("settings/list_details.html", 
                           list_info=registry_entry, 
                           columns=columns, 
                           rows=rows,
                           pagination=pagination)


@bp.route("/<table_name>/add-row", methods=["POST"])
@login_required
def add_row(table_name):
    """Inserts a new row into the dynamic table, automatically casting data types."""
    # Ensure list exists
    ListRegistry.query.filter_by(table_name=table_name).first_or_404()
    
    # Gather raw string data from the HTML form
    raw_form_data = request.form.to_dict()
    raw_form_data.pop('csrf_token', None) 
    
    # 1. Dynamically bind to the table FIRST so we know the column types
    metadata = MetaData()
    metadata.reflect(bind=db.engine, only=[table_name])
    dynamic_table = Table(table_name, metadata, autoload_with=db.engine)

    # 2. Automatically cast form strings into the correct database types
    clean_data = {}
    for col_name, value in raw_form_data.items():
        if col_name in dynamic_table.columns:
            # Figure out if the database expects an int, float, str, etc.
            col_type = dynamic_table.columns[col_name].type.python_type
            
            if value.strip() == "":
                clean_data[col_name] = None  # Convert empty HTML inputs to database NULLs
            else:
                try:
                    clean_data[col_name] = col_type(value) # Cast the string (e.g., int("7") -> 7)
                except ValueError:
                    # If it fails to cast, fallback to string and let the DB throw the error
                    clean_data[col_name] = value

    # 3. Check for the PID using the newly casted clean data
    pid_value = clean_data.get('pid')
    if not pid_value:
        flash("A 'pid' value is required to add a row.", "error")
        return redirect(url_for('lists.view_list', table_name=table_name))

    try:
        with db.engine.connect() as conn:
            # Check if PID already exists
            check_stmt = dynamic_table.select().where(dynamic_table.c.pid == pid_value)
            existing_row = conn.execute(check_stmt).fetchone()
            
            if existing_row:
                flash(f"Row insertion failed: A record with PID '{pid_value}' already exists.", "error")
            else:
                # Insert the new row using the clean, casted data
                insert_stmt = dynamic_table.insert().values(**clean_data)
                conn.execute(insert_stmt)
                conn.commit()
                
                # Update registry row count so the UI pagination stays accurate
                db.session.execute(text("UPDATE list_registry SET row_count = row_count + 1 WHERE table_name = :tname"), {"tname": table_name})
                db.session.commit()
                
                flash("Row added successfully.", "success")
                
    except Exception as e:
        flash(f"Error adding row: {str(e)}", "error")

    return redirect(url_for('lists.view_list', table_name=table_name))


@bp.route("/<table_name>/delete", methods=["POST"])
@login_required
def delete_list(table_name):
    """Drops the dynamic table and removes it from the ListRegistry."""
    registry_entry = ListRegistry.query.filter_by(table_name=table_name).first_or_404()
    
    try:
        # 1. Check if the physical database table actually exists
        inspector = inspect(db.engine)
        if inspector.has_table(table_name):
            # If it exists, reflect it and drop it
            metadata = MetaData()
            metadata.reflect(bind=db.engine, only=[table_name])
            dynamic_table = metadata.tables[table_name]
            dynamic_table.drop(db.engine)
            
        # 2. Delete the registry entry (This runs even if the table was already gone!)
        db.session.delete(registry_entry)
        db.session.commit()
        
        flash(f"List '{registry_entry.display_name}' deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting list: {str(e)}", "error")
        
    return redirect(url_for('lists.index'))

@bp.route("/<table_name>/export")
@login_required
def export_list(table_name):
    """Exports the full dynamic table to an Excel file."""
    registry_entry = ListRegistry.query.filter_by(table_name=table_name).first_or_404()
    
    try:
        # 1. Fetch ALL data from the table (ignoring pagination limits)
        with db.engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name}"))
            rows = [dict(row._mapping) for row in result]
            
        # 2. Load the data into a Pandas DataFrame
        df = pd.DataFrame(rows)
        
        # 3. Create an in-memory buffer to hold the Excel file
        output = io.BytesIO()
        
        # 4. Write the DataFrame to the buffer as an Excel file
        # We explicitly set the sheet_name to display_name so it perfectly matches on re-upload
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=registry_entry.display_name, index=False)
            
        output.seek(0)
        
        # 5. Send the file to the user's browser for download
        filename = f"{registry_entry.display_name}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        flash(f"Error exporting list: {str(e)}", "error")
        return redirect(url_for('lists.view_list', table_name=table_name))