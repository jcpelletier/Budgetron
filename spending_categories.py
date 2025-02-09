import pandas as pd
import matplotlib.pyplot as plt
import sys

# Ensure stdout supports UTF-8 (Windows workaround)
sys.stdout.reconfigure(encoding='utf-8')

def load_mappings(classification_csv):
    """Load category mappings from the classification CSV."""
    mappings = {}
    df = pd.read_csv(classification_csv)
    for column in df.columns:
        for keyword in df[column].dropna():
            mappings[keyword.lower()] = column  # Map each keyword to its category
    return mappings

def categorize_transaction(description, mappings):
    """Categorize a transaction based on the description and mappings."""
    description = description.lower()
    for key, category in mappings.items():
        if key in description:
            return category
    return 'Other'

def main(source_csv, classification_csv, output_image):
    # Load the source CSV
    transactions = pd.read_csv(source_csv)
    transactions['date'] = pd.to_datetime(transactions['date'], errors='coerce')
    transactions['amount'] = transactions['amount'].replace(r'[\$,]', '', regex=True).astype(float)

    # Load the category mappings
    mappings = load_mappings(classification_csv)

    # Categorize transactions
    transactions['category'] = transactions['description'].apply(lambda desc: categorize_transaction(desc, mappings))

    # Print transactions categorized as "Other"
    other_transactions = transactions[transactions['category'] == 'Other']

    if not other_transactions.empty:
        output_text = "Transactions categorized as 'Other':\n"
        output_text += other_transactions[['date', 'description', 'amount']].to_string(index=False)

        print(output_text)  # Print to console

        # Save to a text file
        with open("other_transactions.txt", "w", encoding="utf-8") as file:
            file.write(output_text + "\n")
    else:
        print("No transactions categorized as 'Other'.")
        with open("other_transactions.txt", "w", encoding="utf-8") as file:
            file.write("No transactions categorized as 'Other'.\n")

    # Exclude payments or balance-related transactions
    filtered_transactions = transactions[~transactions['description'].str.contains('payment|interest charge', case=False, na=False)]

    # Calculate gross spending (ignore negative amounts)
    gross_spending = filtered_transactions[filtered_transactions['amount'] > 0]['amount'].sum()

    # Define the time period
    start_date = filtered_transactions['date'].min().strftime('%B %d, %Y')
    end_date = filtered_transactions['date'].max().strftime('%B %d, %Y')
    title_text = f"${gross_spending:,.2f} spent over {start_date} to {end_date}"

    # Aggregate spending by category
    spending_by_category = filtered_transactions.groupby('category')['amount'].sum().sort_values(ascending=False)

    # Plot the spending by category
    plt.figure(figsize=(12, 6))
    bars = spending_by_category.plot(kind='bar', color='skyblue', figsize=(12, 6))
    plt.suptitle(title_text, fontsize=12, y=0.96)
    plt.xlabel(' ', fontsize=14)  # Remove the label text for the x-axis
    plt.ylabel('Total Spending ($)', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Annotate each bar with the corresponding dollar amount
    for bar in bars.patches:
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 5,
            f"${bar.get_height():,.2f}",
            ha='center',
            va='bottom',
            fontsize=10
        )

    plt.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust layout to avoid overlap

    # Save the chart as an image
    plt.savefig(output_image)
    print(f"Chart saved to {output_image}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <source_csv> <classification_csv> <output_image>")
        sys.exit(1)

    source_csv = sys.argv[1]
    classification_csv = sys.argv[2]
    output_image = sys.argv[3]

    main(source_csv, classification_csv, output_image)
