def show_menu():
    """Displays the main menu options to the user."""
    print("\n" + "=" * 35)
    print("    PERSONAL EXPENSE CALCULATOR")
    print("=" * 35)
    print("1. Add Expense")
    print("2. View All Expenses")
    print("3. Calculate Total Spending")
    print("4. Exit")
    print("=" * 35)


def add_expense(expenses):
    """Prompts the user to enter an expense item and amount, then saves it."""
    item = input("Enter expense description (e.g., Coffee, Groceries): ").strip()
    if not item:
        print("Error: Expense description cannot be empty!")
        return

    try:
        amount = float(input("Enter amount ($): "))
        if amount <= 0:
            print("Error: Amount must be greater than zero.")
            return
        
        # Save expense as a dictionary inside the list
        expenses.append({"item": item, "amount": amount})
        print(f"Success: Added '{item}' for ${amount:.2f}")
    except ValueError:
        print("Error: Please enter a valid numeric amount.")


def view_expenses(expenses):
    """Displays all recorded expenses in a neat table format."""
    if not expenses:
        print("\nNo expenses recorded yet.")
        return

    print("\n--- All Expenses ---")
    print(f"{'#':<4} {'Description':<20} {'Amount':>10}")
    print("-" * 36)
    for i, expense in enumerate(expenses, start=1):
        print(f"{i:<4} {expense['item']:<20} ${expense['amount']:>9.2f}")


def calculate_total(expenses):
    """Calculates and displays the sum of all expenses."""
    if not expenses:
        print("\nNo expenses recorded yet. Total spending is $0.00.")
        return

    total = sum(expense["amount"] for expense in expenses)
    print(f"\nTotal Spending: ${total:.2f} (across {len(expenses)} items)")


def main():
    """Main application loop."""
    expenses = []  # List to hold all expense dictionaries

    while True:
        show_menu()
        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            add_expense(expenses)
        elif choice == "2":
            view_expenses(expenses)
        elif choice == "3":
            calculate_total(expenses)
        elif choice == "4":
            print("\nThank you for using Personal Expense Calculator. Goodbye!")
            break
        else:
            print("Invalid choice! Please choose an option between 1 and 4.")


if __name__ == "__main__":
    main()
