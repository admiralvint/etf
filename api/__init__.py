import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, jsonify, send_from_directory
from io import BytesIO
import base64
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend

import azure.functions as func
from flask import Flask, render_template, request, send_from_directory
import os

app = Flask(__name__, static_folder='static', template_folder='templates')

# Import your existing etfapp functions
from . import etfapp  # Import your existing etfapp functions

def calculate_investment(initial_amount, monthly_contribution, annual_return, dividend_yield, years):
    months = years * 12
    monthly_return = (1 + annual_return) ** (1/12) - 1
    
    # 1. Total return with dividends reinvested
    total_with_dividends = initial_amount
    for _ in range(months):
        total_with_dividends *= (1 + monthly_return)
        total_with_dividends += monthly_contribution
    total_with_dividends *= (1 + dividend_yield) ** years

    # 2. Total return without dividends reinvested
    total_without_dividends = initial_amount
    dividends_received = 0
    for year in range(years):
        for _ in range(12):
            total_without_dividends *= (1 + monthly_return)
            total_without_dividends += monthly_contribution
        dividends = total_without_dividends * dividend_yield
        dividends_received += dividends

    # 3. Dividends received over the time period
    # (Already calculated in the loop above)

    # 4. Difference between with and without dividends reinvested
    difference = total_with_dividends - total_without_dividends

    return total_with_dividends, total_without_dividends, dividends_received, difference

def generate_graph(initial_amount, monthly_contribution, annual_return, dividend_yield, years):
    months = years * 12
    monthly_return = (1 + annual_return) ** (1/12) - 1
    
    option1 = [initial_amount]
    option2 = [initial_amount]
    
    for month in range(1, months + 1):
        option1.append(option1[-1] * (1 + monthly_return) + monthly_contribution)
        option2.append(option2[-1] + monthly_contribution)
    
    option1 = np.array(option1) * ((1 + dividend_yield) ** (np.arange(months + 1) / 12))
    
    plt.figure(figsize=(10, 6))
    plt.plot(range(months + 1), option1, label='Total Return')
    plt.plot(range(months + 1), option2, label='Contributions Only')
    plt.xlabel('Months')
    plt.ylabel('Investment Value')
    plt.title('Investment Growth Over Time')
    plt.legend()
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return image_base64

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        stocks = []
        for i in range(1, 4):  # Check for up to 3 stocks
            if f'stock_name_{i}' in request.form:
                try:
                    stock_name = request.form[f'stock_name_{i}']
                    initial_amount = float(request.form[f'initial_amount_{i}'].replace(',', '.'))
                    monthly_contribution = float(request.form[f'monthly_contribution_{i}'].replace(',', '.'))
                    annual_return = float(request.form[f'annual_return_{i}'].replace(',', '.'))
                    dividend_yield = float(request.form[f'dividend_yield_{i}'].replace(',', '.'))
                    years = int(request.form[f'years_{i}'])
                    
                    results = calculate_investment(initial_amount, monthly_contribution, annual_return/100, dividend_yield/100, years)
                    graph = generate_graph(initial_amount, monthly_contribution, annual_return/100, dividend_yield/100, years)
                    
                    stock = {
                        'name': stock_name,
                        'initial_amount': initial_amount,
                        'monthly_contribution': monthly_contribution,
                        'annual_return': annual_return,
                        'dividend_yield': dividend_yield,
                        'years': years,
                        'results': results,
                        'graph': graph
                    }
                    stocks.append(stock)
                except ValueError as e:
                    return f"Error: Invalid input for {stock_name}. {str(e)}", 400
            else:
                break  # No more stocks to process
        
        if not stocks:
            return jsonify({"error": "No valid stock data submitted"}), 400
        
        return jsonify({"stocks": stocks})
    
    return render_template('index.html')

def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == 'POST':
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse("Invalid JSON", status_code=400)

        response = app.test_client().post('/', json=req_body)
        return func.HttpResponse(response.data, status_code=response.status_code, mimetype="application/json")
    else:
        return func.WsgiMiddleware(app.wsgi_app).handle(req)

if __name__ == '__main__':
    app.run(debug=False)