import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

# Ensure stdout supports UTF-8 (Windows workaround)
sys.stdout.reconfigure(encoding='utf-8')

def graph_spending(csv_file, target_budget, output_path):
    try:
        # Read the CSV file
        transactions_df = pd.read_csv(csv_file)

        # Clean and preprocess the data
        transactions_df['date'] = pd.to_datetime(transactions_df['date'], errors='coerce')
        transactions_df['amount'] = transactions_df['amount'].replace(r'[\$,]', '', regex=True).astype(float)

        # Filter out negative amounts (payments or refunds)
        filtered_positive_spending = transactions_df[transactions_df['amount'] > 0]

        # Get the earliest transaction date and generate a 30-day range
        start_date = filtered_positive_spending['date'].min()
        if pd.isnull(start_date):
            print("Error: No valid dates found in the data.")
            return
        date_range = pd.date_range(start=start_date, periods=30)

        # Aggregate daily spending
        daily_spending = (
            filtered_positive_spending.groupby('date')['amount']
            .sum()
            .reindex(date_range, fill_value=0)
        )

        # Calculate the daily budget
        daily_budget = target_budget / len(date_range)

        # Plot the data
        plt.figure(figsize=(12, 6))
        plt.plot(daily_spending.index, daily_spending.cumsum(), label='Actual Spending', linewidth=2)
        plt.plot(daily_spending.index, [daily_budget * (i + 1) for i in range(len(date_range))],
                 label=f'Budget (${target_budget})', linestyle='--', linewidth=2, color='red')

        # Annotate total actual spending
        total_spending = daily_spending.sum()
        plt.annotate(f'Total: ${total_spending:.2f}', 
                     xy=(daily_spending.index[-1], daily_spending.cumsum().iloc[-1]), 
                     xytext=(-60, 10), 
                     textcoords='offset points', 
                     arrowprops=dict(arrowstyle='->', color='black'), 
                     fontsize=12, color='blue')

        # Customize plot appearance
        plt.title('Spending vs Budget', fontsize=16)
        plt.xlabel('Date', fontsize=14)
        plt.ylabel('Cumulative Spending ($)', fontsize=14)
        plt.legend(fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()

        # Save the plot to the output file
        plt.savefig(output_path, format='png')
        print(f"Plot saved to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python spending_plot.py <csv_file> <target_budget> <output_path>")
    else:
        csv_file = sys.argv[1]
        try:
            target_budget = float(sys.argv[2])
        except ValueError:
            print("Error: Target budget must be a numeric value.")
            sys.exit(1)

        output_path = sys.argv[3]

        if not os.path.exists(csv_file):
            print(f"Error: File '{csv_file}' not found.")
        else:
            graph_spending(csv_file, target_budget, output_path)
