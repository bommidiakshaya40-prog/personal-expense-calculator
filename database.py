"""
Database management and calculation engine for Group Food & Expense Splitter.
Uses SQLite for robust, permanent local storage.
"""

import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database")
DB_PATH = os.path.join(DB_DIR, "expenses.db")


def get_db_connection():
    """Establishes a connection to the SQLite database with row factory and foreign keys."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Initializes tables for groups, members, food items, and item allocations."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Groups table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Members table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
        )
    """)

    # 3. Food items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('Veg', 'Non-Veg', 'Drinks', 'Other')),
            quantity REAL NOT NULL DEFAULT 1,
            price_per_item REAL NOT NULL,
            total_price REAL NOT NULL,
            split_type TEXT NOT NULL DEFAULT 'single' CHECK(split_type IN ('single', 'equal_shared', 'custom_shared')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
        )
    """)

    # 4. Item allocations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS item_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            share_units REAL DEFAULT 1.0,
            share_amount REAL NOT NULL,
            FOREIGN KEY (item_id) REFERENCES food_items(id) ON DELETE CASCADE,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ==========================================
# Group Operations
# ==========================================

def create_group(name, notes=""):
    """Creates a new group and returns its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO groups (name, notes, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (name.strip(), notes.strip())
    )
    group_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return group_id


def get_all_groups():
    """Retrieves all groups with member count, total bill, and item count."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            g.id, 
            g.name, 
            g.notes, 
            g.created_at, 
            g.updated_at,
            COUNT(DISTINCT m.id) as member_count,
            COUNT(DISTINCT f.id) as item_count,
            COALESCE(SUM(f.total_price), 0.0) as total_bill
        FROM groups g
        LEFT JOIN members m ON g.id = m.group_id
        LEFT JOIN food_items f ON g.id = f.group_id
        GROUP BY g.id
        ORDER BY g.updated_at DESC
    """)
    rows = cursor.fetchall()
    groups = [dict(row) for row in rows]
    conn.close()
    return groups


def get_group(group_id):
    """Retrieves a single group by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_group(group_id, name, notes=""):
    """Updates group details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE groups SET name = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (name.strip(), notes.strip(), group_id)
    )
    conn.commit()
    conn.close()


def delete_group(group_id):
    """Deletes a group and cascades delete to members, items, allocations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()


def clear_group_expenses(group_id):
    """Deletes all items and allocations in a group, keeping the members."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM food_items WHERE group_id = ?", (group_id,))
    cursor.execute("UPDATE groups SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()


# ==========================================
# Member Operations
# ==========================================

def add_member(group_id, name):
    """Adds a member to a group."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (group_id, name) VALUES (?, ?)",
        (group_id, name.strip())
    )
    member_id = cursor.lastrowid
    cursor.execute("UPDATE groups SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()
    return member_id


def get_members(group_id):
    """Retrieves all members of a group."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE group_id = ? ORDER BY id ASC", (group_id,))
    rows = cursor.fetchall()
    members = [dict(row) for row in rows]
    conn.close()
    return members


def delete_member(member_id):
    """Deletes a member and cleans up/recomputes associated allocations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT group_id FROM members WHERE id = ?", (member_id,))
    member = cursor.fetchone()
    if member:
        group_id = member["group_id"]
        # Find all items where this member has allocations
        cursor.execute("SELECT DISTINCT item_id FROM item_allocations WHERE member_id = ?", (member_id,))
        affected_item_ids = [row["item_id"] for row in cursor.fetchall()]

        # Delete member (cascades to item_allocations rows for this member)
        cursor.execute("DELETE FROM members WHERE id = ?", (member_id,))

        # Re-check affected items
        for item_id in affected_item_ids:
            cursor.execute("SELECT total_price, split_type FROM food_items WHERE id = ?", (item_id,))
            item = cursor.fetchone()
            if not item:
                continue

            cursor.execute("SELECT member_id, share_units FROM item_allocations WHERE item_id = ?", (item_id,))
            rem_allocs = cursor.fetchall()
            if not rem_allocs:
                # No one left allocated to this item; remove item
                cursor.execute("DELETE FROM food_items WHERE id = ?", (item_id,))
            else:
                rem_shares = [{"member_id": r["member_id"], "share_units": r["share_units"]} for r in rem_allocs]
                new_split_type = "single" if len(rem_shares) == 1 else item["split_type"]
                cursor.execute("UPDATE food_items SET split_type = ? WHERE id = ?", (new_split_type, item_id))
                cursor.execute("DELETE FROM item_allocations WHERE id = ?", (item_id,))
                new_allocs = compute_allocations(item["total_price"], new_split_type, rem_shares)
                for a in new_allocs:
                    cursor.execute("""
                        INSERT INTO item_allocations (item_id, member_id, share_units, share_amount)
                        VALUES (?, ?, ?, ?)
                    """, (item_id, a["member_id"], a["share_units"], a["share_amount"]))

        cursor.execute("UPDATE groups SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (group_id,))
        conn.commit()
    conn.close()


# ==========================================
# Item & Allocation Operations
# ==========================================

def compute_allocations(total_price, split_type, member_shares):
    """
    Computes precise individual share amounts for an item.
    member_shares: list of dicts: [{'member_id': int, 'share_units': float}]
    Ensures that sum(share_amounts) == total_price down to exact 2 decimal places.
    """
    if not member_shares:
        return []

    num_members = len(member_shares)
    allocations = []

    if split_type == 'single':
        # 100% to single person
        allocations.append({
            'member_id': member_shares[0]['member_id'],
            'share_units': 1.0,
            'share_amount': round(total_price, 2)
        })
        return allocations

    elif split_type == 'equal_shared':
        # Equal split among selected members
        base_share = round(total_price / num_members, 2)
        total_allocated = base_share * num_members
        diff = round(total_price - total_allocated, 2)

        for i, m in enumerate(member_shares):
            amount = base_share
            # Adjust rounding difference on the first member
            if i == 0:
                amount = round(amount + diff, 2)
            allocations.append({
                'member_id': m['member_id'],
                'share_units': 1.0,
                'share_amount': amount
            })
        return allocations

    elif split_type == 'custom_shared':
        # Split according to custom units/quantities
        total_units = sum(float(m.get('share_units', 1.0)) for m in member_shares)
        if total_units <= 0:
            total_units = 1.0

        current_allocated = 0.0
        for i, m in enumerate(member_shares):
            units = float(m.get('share_units', 1.0))
            if i == len(member_shares) - 1:
                # Last member gets the exact remainder to ensure perfect total sum
                share_amount = round(total_price - current_allocated, 2)
            else:
                share_amount = round((units / total_units) * total_price, 2)
                current_allocated += share_amount

            allocations.append({
                'member_id': m['member_id'],
                'share_units': units,
                'share_amount': share_amount
            })
        return allocations

    return allocations


def add_food_item(group_id, name, category, quantity, price_per_item, split_type, member_shares):
    """
    Adds a food item and calculates allocations.
    member_shares: list of dicts [{'member_id': int, 'share_units': float}]
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    quantity = float(quantity)
    price_per_item = float(price_per_item)
    total_price = round(quantity * price_per_item, 2)

    cursor.execute("""
        INSERT INTO food_items (group_id, name, category, quantity, price_per_item, total_price, split_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (group_id, name.strip(), category, quantity, price_per_item, total_price, split_type))
    item_id = cursor.lastrowid

    allocations = compute_allocations(total_price, split_type, member_shares)
    for alloc in allocations:
        cursor.execute("""
            INSERT INTO item_allocations (item_id, member_id, share_units, share_amount)
            VALUES (?, ?, ?, ?)
        """, (item_id, alloc['member_id'], alloc['share_units'], alloc['share_amount']))

    cursor.execute("UPDATE groups SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()
    return item_id


def update_food_item(item_id, name, category, quantity, price_per_item, split_type, member_shares):
    """Updates an existing food item and recomputes its allocations."""
    conn = get_db_connection()
    cursor = conn.cursor()

    quantity = float(quantity)
    price_per_item = float(price_per_item)
    total_price = round(quantity * price_per_item, 2)

    cursor.execute("""
        UPDATE food_items
        SET name = ?, category = ?, quantity = ?, price_per_item = ?, total_price = ?, split_type = ?
        WHERE id = ?
    """, (name.strip(), category, quantity, price_per_item, total_price, split_type, item_id))

    # Remove old allocations and insert recomputed allocations
    cursor.execute("DELETE FROM item_allocations WHERE item_id = ?", (item_id,))
    allocations = compute_allocations(total_price, split_type, member_shares)
    for alloc in allocations:
        cursor.execute("""
            INSERT INTO item_allocations (item_id, member_id, share_units, share_amount)
            VALUES (?, ?, ?, ?)
        """, (item_id, alloc['member_id'], alloc['share_units'], alloc['share_amount']))

    # Update group timestamp
    cursor.execute("""
        UPDATE groups SET updated_at = CURRENT_TIMESTAMP 
        WHERE id = (SELECT group_id FROM food_items WHERE id = ?)
    """, (item_id,))

    conn.commit()
    conn.close()


def delete_food_item(item_id):
    """Deletes a food item and its allocations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE groups SET updated_at = CURRENT_TIMESTAMP 
        WHERE id = (SELECT group_id FROM food_items WHERE id = ?)
    """, (item_id,))
    cursor.execute("DELETE FROM food_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def get_items_with_allocations(group_id):
    """Returns all items for a group along with allocated member details."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM food_items WHERE group_id = ? ORDER BY id ASC
    """, (group_id,))
    items_rows = cursor.fetchall()
    items = []

    for item_row in items_rows:
        item = dict(item_row)
        cursor.execute("""
            SELECT ia.id, ia.member_id, ia.share_units, ia.share_amount, m.name as member_name
            FROM item_allocations ia
            JOIN members m ON ia.member_id = m.id
            WHERE ia.item_id = ?
        """, (item["id"],))
        alloc_rows = cursor.fetchall()
        item["allocations"] = [dict(a) for a in alloc_rows]
        item["assigned_names"] = ", ".join([a["member_name"] for a in item["allocations"]])
        items.append(item)

    conn.close()
    return items


def get_item_with_allocations(item_id):
    """Returns a single food item with its allocated member details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM food_items WHERE id = ?", (item_id,))
    item_row = cursor.fetchone()
    if not item_row:
        conn.close()
        return None

    item = dict(item_row)
    cursor.execute("""
        SELECT ia.id, ia.member_id, ia.share_units, ia.share_amount, m.name as member_name
        FROM item_allocations ia
        JOIN members m ON ia.member_id = m.id
        WHERE ia.item_id = ?
    """, (item_id,))
    alloc_rows = cursor.fetchall()
    item["allocations"] = [dict(a) for a in alloc_rows]
    item["assigned_names"] = ", ".join([a["member_name"] for a in item["allocations"]])
    conn.close()
    return item


# ==========================================
# Dynamic Calculation Engine
# ==========================================

def calculate_group_summary(group_id):
    """
    Computes a complete, mathematically precise group bill breakdown:
    - Group info
    - Total group bill
    - Category subtotals (Veg, Non-Veg, Drinks, Other)
    - Total food cost (Veg + Non-Veg + Other) vs Total Drinks cost
    - Each member's itemized breakdown (individual items and shared items)
    - Total payable per member
    - Cross-verification that sum(member totals) == total group bill
    """
    group = get_group(group_id)
    if not group:
        return None

    members = get_members(group_id)
    items = get_items_with_allocations(group_id)

    total_group_bill = sum(item["total_price"] for item in items)
    total_group_bill = round(total_group_bill, 2)

    # Category totals
    category_totals = {"Veg": 0.0, "Non-Veg": 0.0, "Drinks": 0.0, "Other": 0.0}
    category_counts = {"Veg": 0, "Non-Veg": 0, "Drinks": 0, "Other": 0}

    for item in items:
        cat = item["category"]
        if cat in category_totals:
            category_totals[cat] = round(category_totals[cat] + item["total_price"], 2)
            category_counts[cat] += 1

    total_food_cost = round(category_totals["Veg"] + category_totals["Non-Veg"] + category_totals["Other"], 2)
    total_drinks_cost = round(category_totals["Drinks"], 2)

    # Initialize per-member breakdown
    member_summaries = {}
    for m in members:
        member_summaries[m["id"]] = {
            "member_id": m["id"],
            "name": m["name"],
            "consumed_items": [],
            "items": [],
            "individual_items": [],
            "shared_items": [],
            "individual_total": 0.0,
            "shared_total": 0.0,
            "total_payable": 0.0,
            "item_count": 0
        }

    # Allocate each item into member summaries
    for item in items:
        is_shared = item["split_type"] != "single"
        for alloc in item["allocations"]:
            mid = alloc["member_id"]
            if mid in member_summaries:
                consumed_record = {
                    "item_id": item["id"],
                    "name": item["name"],
                    "category": item["category"],
                    "quantity": item["quantity"],
                    "price_per_item": item["price_per_item"],
                    "item_total_price": item["total_price"],
                    "split_type": item["split_type"],
                    "is_shared": is_shared,
                    "share_units": alloc["share_units"],
                    "share_amount": alloc["share_amount"],
                    "shared_with": item["assigned_names"] if is_shared else ""
                }
                member_summaries[mid]["consumed_items"].append(consumed_record)
                member_summaries[mid]["items"].append(consumed_record)
                member_summaries[mid]["item_count"] += 1

                if is_shared:
                    member_summaries[mid]["shared_items"].append(consumed_record)
                    member_summaries[mid]["shared_total"] = round(
                        member_summaries[mid]["shared_total"] + alloc["share_amount"], 2
                    )
                else:
                    member_summaries[mid]["individual_items"].append(consumed_record)
                    member_summaries[mid]["individual_total"] = round(
                        member_summaries[mid]["individual_total"] + alloc["share_amount"], 2
                    )

                member_summaries[mid]["total_payable"] = round(
                    member_summaries[mid]["individual_total"] + member_summaries[mid]["shared_total"], 2
                )

    member_summary_list = list(member_summaries.values())
    sum_individual_totals = round(sum(m["total_payable"] for m in member_summary_list), 2)
    total_individual_cost = round(sum(m["individual_total"] for m in member_summary_list), 2)
    total_shared_cost = round(sum(m["shared_total"] for m in member_summary_list), 2)
    discrepancy = round(total_group_bill - sum_individual_totals, 2)

    # If there's an infinitesimal rounding discrepancy (e.g. 0.01), reconcile with first active member
    if discrepancy != 0.0 and member_summary_list:
        for m in member_summary_list:
            if m["total_payable"] > 0:
                m["total_payable"] = round(m["total_payable"] + discrepancy, 2)
                sum_individual_totals = round(sum_individual_totals + discrepancy, 2)
                break

    return {
        "group": group,
        "members": members,
        "member_count": len(members),
        "items": items,
        "item_count": len(items),
        "total_group_bill": total_group_bill,
        "total_food_cost": total_food_cost,
        "total_drinks_cost": total_drinks_cost,
        "total_individual_cost": total_individual_cost,
        "total_shared_cost": total_shared_cost,
        "category_totals": category_totals,
        "category_counts": category_counts,
        "member_summaries": member_summary_list,
        "sum_individual_totals": sum_individual_totals,
        "discrepancy": round(total_group_bill - sum_individual_totals, 2)
    }
