from flask import Flask, render_template, request, send_file
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio
from faker import Faker
from datetime import datetime
import io

app = Flask(__name__)

# Generate dummy data
def simulate_data(n=1000):
    fake = Faker()
    np.random.seed(42)

    merchant_ids = [f"M10{i}" for i in range(5)]
    products = ['POS', 'QR', 'Online', 'PayBill', 'BuyGoods']
    data = []

    for _ in range(n):
        merchant = np.random.choice(merchant_ids)
        product = np.random.choice(products)
        date = fake.date_between(start_date="-6M", end_date="today")
        data.append({
            "MerchantId": merchant,
            "ProductName": product,
            "LogDate": date
        })

    df = pd.DataFrame(data)
    df['LogDate'] = pd.to_datetime(df['LogDate'])
    df['Month'] = df['LogDate'].dt.to_period('M').astype(str)
    return df

# Simulate data once
df = simulate_data()

@app.route('/', methods=['GET', 'POST'])
def matrix():
    merchants = sorted(df['MerchantId'].unique())
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    selected_merchant = request.form.get('merchant', '')

    filtered_df = df.copy()

    if start_date:
        filtered_df = filtered_df[filtered_df['LogDate'] >= pd.to_datetime(start_date)]
    if end_date:
        filtered_df = filtered_df[filtered_df['LogDate'] <= pd.to_datetime(end_date)]
    if selected_merchant:
        filtered_df = filtered_df[filtered_df['MerchantId'] == selected_merchant]

    # Group and pivot
    grouped = filtered_df.groupby(['MerchantId', 'Month'])['ProductName'].agg([
        ('UniqueProductsUsed', lambda x: x.nunique()),
        ('ProductList', lambda x: ', '.join(sorted(set(x))))
    ]).reset_index()

    value_matrix = grouped.pivot(index='MerchantId', columns='Month', values='UniqueProductsUsed').fillna(0)
    hover_matrix = grouped.pivot(index='MerchantId', columns='Month', values='ProductList').fillna('No products')

    # Build Plotly heatmap
    fig = px.imshow(value_matrix,
                    labels=dict(x="Month", y="Merchant", color="# Products"),
                    x=value_matrix.columns,
                    y=value_matrix.index,
                    color_continuous_scale='Viridis',
                    aspect='auto')

    fig.update_traces(
        customdata=hover_matrix.values,
        hovertemplate="<b>Merchant:</b> %{y}<br><b>Month:</b> %{x}<br><b>Products:</b> %{customdata}<extra></extra>"
    )

    fig.update_layout(title="Monthly Product Usage by Merchant")
    heatmap_html = pio.to_html(fig, full_html=False)

    # Table with tooltips
    table_html = build_tooltip_table(value_matrix, hover_matrix)

    # Note: The original code referenced 'matrix.html' or 'matrix1.html'.
    # Ensure your HTML file name matches what you intend to use.
    return render_template('matrix1.html', # Assuming matrix1.html is the target
                           plot=heatmap_html,
                           merchants=merchants,
                           selected_merchant=selected_merchant,
                           start_date=start_date,
                           end_date=end_date,
                           table=table_html)

@app.route('/download', methods=['POST'])
def download():
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    selected_merchant = request.form.get('merchant', '')

    filtered_df = df.copy()
    if start_date:
        filtered_df = filtered_df[filtered_df['LogDate'] >= pd.to_datetime(start_date)]
    if end_date:
        filtered_df = filtered_df[filtered_df['LogDate'] <= pd.to_datetime(end_date)]
    if selected_merchant:
        filtered_df = filtered_df[filtered_df['MerchantId'] == selected_merchant]

    grouped = filtered_df.groupby(['MerchantId', 'Month'])['ProductName'].nunique().reset_index()
    grouped.rename(columns={'ProductName': 'UniqueProductsUsed'}, inplace=True)
    pivot_df = grouped.pivot(index='MerchantId', columns='Month', values='UniqueProductsUsed').fillna(0)

    buffer = io.BytesIO()
    pivot_df.to_csv(buffer)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="merchant_product_matrix.csv", mimetype='text/csv')

# Helper: HTML table with hover tooltips
def build_tooltip_table(values_df, tooltip_df):
    html = '''
    <table class="table table-bordered table-striped">
        <thead>
            <tr><th>MerchantId</th>'''

    for col in values_df.columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'

    for idx in values_df.index:
        html += f'<tr><td><b>{idx}</b></td>'
        for col in values_df.columns:
            val = values_df.loc[idx, col]
            tip = tooltip_df.loc[idx, col]
            # Updated to use Bootstrap's data-bs-toggle and data-bs-title for tooltips
            # The .replace() is crucial to handle quotes within the tooltip text
            html += f"<td data-bs-toggle='tooltip' data-bs-placement='top' data-bs-title='{tip.replace('''', '&quot;')}'>{int(val)}</td>"
        html += '</tr>'
    html += '</tbody></table>'
    return html

if __name__ == '__main__':
    app.run(debug=True)

