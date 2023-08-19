from flask import Flask, render_template, request, redirect, url_for, flash
import os
import pandas as pd
from werkzeug.utils import secure_filename


from scipy.optimize import newton

def xnpv(rate, cashflows):
    """Calculate NPV for a series of cashflows."""
    return sum([cf/(1+rate)**((t-cashflows[0][0]).days/365.0) for (t, cf) in cashflows])

def xirr_newton(cashflows, guess=0.1):
    """Calculate XIRR using the Newton-Raphson method."""
    try:
        return newton(lambda r: xnpv(r, cashflows), guess)
    except:
        return None



app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "secret_key"  # This is for flashing error/success messages


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def calculate_xirr_from_files(files, portfolio_value):
    all_dataframes = []
    
    # Directory where uploaded files are saved
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), app.config['UPLOAD_FOLDER'])
    
    for file in files:
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)

        data = pd.read_excel(file_path, skiprows=14)
        
        # Convert 'Trade Date' to datetime type
        data['Trade Date'] = pd.to_datetime(data['Trade Date'])
        
        data['Amount'] = data['Quantity'] * data['Price']
        data['Cash Flow'] = data.apply(lambda x: -x['Amount'] if x['Trade Type'] == 'buy' else x['Amount'], axis=1)
        all_dataframes.append(data[["Trade Date", "Cash Flow"]])
    
    # Combine all dataframes
    all_data = pd.concat(all_dataframes, axis=0)
    
    # Add the portfolio value to the transactions
    transactions = list(zip(all_data["Trade Date"].dt.to_pydatetime(), all_data["Cash Flow"]))
    transactions.append((pd.Timestamp.now(), float(portfolio_value)))
    
    # Calculate XIRR using the method you prefer (for now, let's use the brute-force method)
    #xirr_value = xirr_bruteforce_fixed(transactions)
    xirr_value = xirr_newton(transactions)

    
    return xirr_value

    # Your XIRR calculation code here using the uploaded files and portfolio value
    # Return the XIRR result


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # check if the post request has the files part
        if 'files' not in request.files:
            flash('No files part')
            return redirect(request.url)
        files = request.files.getlist('files')
        portfolio_value = request.form.get('portfolio_value')
        if not files or not portfolio_value:
            flash('No files or portfolio value provided')
            return redirect(request.url)
        for file in files:
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        xirr_value = calculate_xirr_from_files(files, portfolio_value)
        if xirr_value is None:
            flash('Unable to calculate XIRR using the Newton-Raphson method. Please try again or use a different set of data.')
        else:
            flash(f'Calculated XIRR: {xirr_value:.2%}')

              
        # For now, we'll just redirect to the index page
        return redirect(url_for('index'))
    
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
