"""
Flask Application for GROUP FOOD & EXPENSE SPLITTER.
Provides modern web interface and RESTful APIs for managing groups,
members, item allocations, bill calculations, and CSV/PDF exports.
"""

import os
import csv
import io
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
import database

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "group-splitter-secret-key-2026")

# Custom Jinja2 filter for currency formatting (Indian Rupee ₹)
@app.template_filter('currency')
def currency_filter(value):
    try:
        val = float(value)
        return f"₹{val:,.2f}"
    except (ValueError, TypeError):
        return f"₹{value}"


# ==========================================
# Web Page Routes
# ==========================================

@app.route("/")
def index():
    """Home page: welcome banner, quick start, and recent groups list."""
    groups = database.get_all_groups()
    return render_template("index.html", groups=groups)


@app.route("/dashboard")
def dashboard():
    """Dashboard view listing all saved groups and overall statistics."""
    groups = database.get_all_groups()
    total_spent = sum(g["total_bill"] for g in groups)
    total_groups = len(groups)
    total_people = sum(g["member_count"] for g in groups)
    return render_template(
        "dashboard.html",
        groups=groups,
        total_spent=total_spent,
        total_groups=total_groups,
        total_people=total_people
    )


@app.route("/group/<int:group_id>")
def group_detail(group_id):
    """Group management page: members, items, allocations, and live bill preview."""
    group = database.get_group(group_id)
    if not group:
        return redirect(url_for("dashboard"))
    members = database.get_members(group_id)
    items = database.get_items_with_allocations(group_id)
    summary = database.calculate_group_summary(group_id)
    return render_template("group.html", group=group, members=members, items=items, summary=summary)


@app.route("/summary/<int:group_id>")
def group_summary_view(group_id):
    """Comprehensive final bill summary for the group and each individual."""
    summary = database.calculate_group_summary(group_id)
    if not summary:
        return redirect(url_for("dashboard"))
    return render_template("summary.html", summary=summary)


@app.route("/group/<int:group_id>/print")
def print_invoice(group_id):
    """Printer-friendly / PDF-ready bill receipt."""
    summary = database.calculate_group_summary(group_id)
    if not summary:
        return redirect(url_for("dashboard"))
    return render_template("summary.html", summary=summary, is_print_mode=True)


@app.route("/group/<int:group_id>/export/csv")
def export_csv(group_id):
    """Exports group bill details as a downloadable CSV file."""
    summary = database.calculate_group_summary(group_id)
    if not summary:
        return "Group not found", 404

    group = summary["group"]
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Header & Group Info
    writer.writerow(["GROUP FOOD & EXPENSE SPLITTER - BILL INVOICE"])
    writer.writerow(["Group Name", group["name"]])
    writer.writerow(["Date Generated", group.get("updated_at", group.get("created_at", ""))])
    writer.writerow(["Total Bill (INR)", f"Rs. {summary['total_group_bill']:.2f}"])
    writer.writerow(["Total Food Cost", f"Rs. {summary['total_food_cost']:.2f}"])
    writer.writerow(["Total Drinks Cost", f"Rs. {summary['total_drinks_cost']:.2f}"])
    writer.writerow([])

    # 2. Category Breakdown
    writer.writerow(["CATEGORY BREAKDOWN"])
    writer.writerow(["Category", "Total Amount (INR)", "Item Count"])
    for cat, total in summary["category_totals"].items():
        writer.writerow([cat, f"{total:.2f}", summary["category_counts"].get(cat, 0)])
    writer.writerow([])

    # 3. Individual Member Summary
    writer.writerow(["INDIVIDUAL FINAL PAYABLE SUMMARY"])
    writer.writerow(["Member Name", "Individual Items (INR)", "Shared Items (INR)", "Total Payable (INR)"])
    for m in summary["member_summaries"]:
        writer.writerow([
            m["name"],
            f"{m['individual_total']:.2f}",
            f"{m['shared_total']:.2f}",
            f"{m['total_payable']:.2f}"
        ])
    writer.writerow([])

    # 4. Detailed Consumed Items per Member
    writer.writerow(["DETAILED ITEM BREAKDOWN PER MEMBER"])
    writer.writerow(["Member Name", "Item Name", "Category", "Item Total Cost", "Split Type", "Member Share Amount", "Shared With"])
    for m in summary["member_summaries"]:
        if not m["items"]:
            writer.writerow([m["name"], "No items allocated", "-", "-", "-", "0.00", "-"])
        for it in m["items"]:
            writer.writerow([
                m["name"],
                it["name"],
                it["category"],
                f"{it['item_total_price']:.2f}",
                it["split_type"],
                f"{it['share_amount']:.2f}",
                it.get("shared_with", "")
            ])

    filename = f"Expense_Bill_{group['name'].replace(' ', '_')}.csv"
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


# ==========================================
# REST API Endpoints
# ==========================================

@app.route("/api/groups", methods=["GET", "POST"])
def api_groups():
    if request.method == "POST":
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        notes = data.get("notes", "").strip()
        members = data.get("members", [])  # Optional list of initial member names

        if not name:
            return jsonify({"success": False, "error": "Group name is required."}), 400

        group_id = database.create_group(name, notes)

        # Add initial members if provided
        if isinstance(members, list):
            for m_name in members:
                if str(m_name).strip():
                    database.add_member(group_id, str(m_name).strip())

        return jsonify({"success": True, "group_id": group_id, "message": "Group created successfully!"})

    groups = database.get_all_groups()
    return jsonify({"success": True, "groups": groups})


@app.route("/api/groups/<int:group_id>", methods=["GET", "PUT", "DELETE"])
def api_group_detail(group_id):
    if request.method == "GET":
        summary = database.calculate_group_summary(group_id)
        if not summary:
            return jsonify({"success": False, "error": "Group not found."}), 404
        return jsonify({"success": True, "summary": summary})

    elif request.method == "PUT":
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        notes = data.get("notes", "").strip()
        if not name:
            return jsonify({"success": False, "error": "Group name cannot be empty."}), 400
        database.update_group(group_id, name, notes)
        return jsonify({"success": True, "message": "Group updated successfully."})

    elif request.method == "DELETE":
        database.delete_group(group_id)
        return jsonify({"success": True, "message": "Group deleted successfully."})


@app.route("/api/groups/<int:group_id>/clear", methods=["POST"])
def api_clear_group(group_id):
    """Clears all food items and allocations in a group, keeping the members."""
    database.clear_group_expenses(group_id)
    return jsonify({"success": True, "message": "All expenses cleared for this group."})


@app.route("/api/groups/<int:group_id>/members", methods=["POST"])
def api_add_member(group_id):
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "error": "Member name cannot be empty."}), 400

    member_id = database.add_member(group_id, name)
    return jsonify({"success": True, "member_id": member_id, "name": name, "message": f"Added '{name}' to group."})


@app.route("/api/members/<int:member_id>", methods=["DELETE"])
def api_delete_member(member_id):
    database.delete_member(member_id)
    return jsonify({"success": True, "message": "Member removed."})


@app.route("/api/groups/<int:group_id>/items", methods=["GET", "POST"])
def api_group_items(group_id):
    if request.method == "GET":
        items = database.get_items_with_allocations(group_id)
        return jsonify({"success": True, "items": items})

    elif request.method == "POST":
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        category = data.get("category", "Other")
        quantity = data.get("quantity", 1)
        price_per_item = data.get("price_per_item", 0)
        split_type = data.get("split_type", "single")
        member_shares = data.get("member_shares", [])

        # Validations
        if not name:
            return jsonify({"success": False, "error": "Item name is required."}), 400
        if category not in ("Veg", "Non-Veg", "Drinks", "Other"):
            return jsonify({"success": False, "error": "Invalid category."}), 400

        try:
            quantity = float(quantity)
            price_per_item = float(price_per_item)
            if quantity <= 0 or price_per_item < 0:
                return jsonify({"success": False, "error": "Quantity must be > 0 and price cannot be negative."}), 400
        except ValueError:
            return jsonify({"success": False, "error": "Quantity and price must be valid numbers."}), 400

        if not member_shares:
            return jsonify({"success": False, "error": "Please assign this item to at least one person."}), 400

        item_id = database.add_food_item(
            group_id=group_id,
            name=name,
            category=category,
            quantity=quantity,
            price_per_item=price_per_item,
            split_type=split_type,
            member_shares=member_shares
        )
        return jsonify({"success": True, "item_id": item_id, "message": f"Added '{name}' successfully."})


@app.route("/api/items/<int:item_id>", methods=["GET", "PUT", "DELETE"])
def api_item_action(item_id):
    if request.method == "GET":
        item = database.get_item_with_allocations(item_id)
        if not item:
            return jsonify({"success": False, "error": "Item not found."}), 404
        return jsonify({"success": True, "item": item})

    elif request.method == "DELETE":
        database.delete_food_item(item_id)
        return jsonify({"success": True, "message": "Item deleted."})

    elif request.method == "PUT":
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        category = data.get("category", "Other")
        quantity = data.get("quantity", 1)
        price_per_item = data.get("price_per_item", 0)
        split_type = data.get("split_type", "single")
        member_shares = data.get("member_shares", [])

        if not name:
            return jsonify({"success": False, "error": "Item name is required."}), 400

        try:
            quantity = float(quantity)
            price_per_item = float(price_per_item)
            if quantity <= 0 or price_per_item < 0:
                return jsonify({"success": False, "error": "Quantity must be > 0 and price cannot be negative."}), 400
        except ValueError:
            return jsonify({"success": False, "error": "Quantity and price must be valid numbers."}), 400

        if not member_shares:
            return jsonify({"success": False, "error": "Please assign this item to at least one person."}), 400

        database.update_food_item(
            item_id=item_id,
            name=name,
            category=category,
            quantity=quantity,
            price_per_item=price_per_item,
            split_type=split_type,
            member_shares=member_shares
        )
        return jsonify({"success": True, "message": f"Updated '{name}'."})


# ==========================================
# Run application
# ==========================================

if __name__ == "__main__":
    database.init_db()
    print("Group Food & Expense Splitter running on http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
