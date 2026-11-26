"""
Comprehensive Automated Test Suite for Group Food & Expense Splitter
Verifies backend APIs, SQLite database persistence, allocation algorithms,
mathematical accuracy, input validations, and CSV/PDF export.
"""

import app
import database

def run_tests():
    client = app.app.test_client()
    print("=" * 60)
    print("STARTING TEST SUITE: GROUP FOOD & EXPENSE SPLITTER")
    print("=" * 60)

    # 1. Test Home & Dashboard
    print("\n[1/10] Testing Home and Dashboard routes...")
    r_home = client.get('/')
    assert r_home.status_code == 200, f"Home failed with status {r_home.status_code}"
    r_dash = client.get('/dashboard')
    assert r_dash.status_code == 200, f"Dashboard failed with status {r_dash.status_code}"
    print("  -> Home and Dashboard returned 200 OK.")

    # 2. Test Input Validation on Group Creation
    print("\n[2/10] Testing Input Validations...")
    r_val1 = client.post('/api/groups', json={'name': '   ', 'notes': 'Empty name test'})
    assert r_val1.status_code == 400, "Should reject empty group name"
    print("  -> Empty group name rejected with 400.")

    # 3. Create Group with Members
    print("\n[3/10] Testing Group & Member Creation in SQLite...")
    r_grp = client.post('/api/groups', json={
        'name': 'Royal Feast Dinner',
        'notes': 'Saturday Night Party',
        'members': ['Person A', 'Person B', 'Person C', 'Person D']
    })
    assert r_grp.status_code == 200
    group_id = r_grp.get_json()['group_id']
    assert group_id > 0
    print(f"  -> Created group ID #{group_id} with 4 members.")

    members = database.get_members(group_id)
    assert len(members) == 4
    m_map = {m['name']: m['id'] for m in members}
    print(f"  -> SQLite confirmed members: {list(m_map.keys())}")

    # Add 5th member dynamically via API
    r_m5 = client.post(f'/api/groups/{group_id}/members', json={'name': 'Person E'})
    assert r_m5.status_code == 200
    m_map['Person E'] = r_m5.get_json()['member_id']
    print(f"  -> Added 5th member 'Person E' dynamically.")

    # 4. Add Items: Single Allocation
    print("\n[4/10] Testing Individual Item Allocation (Non-equal, consumption-based)...")
    # Person A: Veg Meals Rs. 120
    client.post(f'/api/groups/{group_id}/items', json={
        'name': 'Veg Meals', 'category': 'Veg', 'quantity': 1, 'price_per_item': 120.0,
        'split_type': 'single', 'member_shares': [{'member_id': m_map['Person A']}]
    })
    # Person B: Chicken Biryani Rs. 220
    client.post(f'/api/groups/{group_id}/items', json={
        'name': 'Chicken Biryani', 'category': 'Non-Veg', 'quantity': 1, 'price_per_item': 220.0,
        'split_type': 'single', 'member_shares': [{'member_id': m_map['Person B']}]
    })
    # Person C: Cold Water Bottle Rs. 20
    client.post(f'/api/groups/{group_id}/items', json={
        'name': 'Cold Water Bottle', 'category': 'Drinks', 'quantity': 1, 'price_per_item': 20.0,
        'split_type': 'single', 'member_shares': [{'member_id': m_map['Person C']}]
    })
    # Person D: Veg Meals Rs. 120
    client.post(f'/api/groups/{group_id}/items', json={
        'name': 'Veg Meals', 'category': 'Veg', 'quantity': 1, 'price_per_item': 120.0,
        'split_type': 'single', 'member_shares': [{'member_id': m_map['Person D']}]
    })
    print("  -> Added individual items for Person A, B, C, D.")

    # 5. Add Shared Items: Equal Split among Selected Members
    print("\n[5/10] Testing Shared Items (Divided ONLY among selected members)...")
    # Water bottle Rs. 30 shared ONLY by Person A, B, and C. Person D and E pay NOTHING.
    client.post(f'/api/groups/{group_id}/items', json={
        'name': 'Shared Mineral Water', 'category': 'Drinks', 'quantity': 1, 'price_per_item': 30.0,
        'split_type': 'equal_shared', 'member_shares': [
            {'member_id': m_map['Person A']},
            {'member_id': m_map['Person B']},
            {'member_id': m_map['Person C']}
        ]
    })
    print("  -> Added ₹30 Shared Water split equally among A, B, C (₹10 each). D and E excluded.")

    # 6. Add Custom Shared Item (e.g. Large Pizza shared by units: A had 2 units, B had 1 unit = Rs. 300)
    print("\n[6/10] Testing Custom Unit-Based Shared Item Allocation...")
    client.post(f'/api/groups/{group_id}/items', json={
        'name': 'Paneer Pizza (Shared by slices)', 'category': 'Veg', 'quantity': 1, 'price_per_item': 300.0,
        'split_type': 'custom_shared', 'member_shares': [
            {'member_id': m_map['Person A'], 'share_units': 2.0},  # 2/3 = 200
            {'member_id': m_map['Person B'], 'share_units': 1.0}   # 1/3 = 100
        ]
    })
    print("  -> Added ₹300 Pizza split 2:1 between Person A (₹200) and Person B (₹100).")

    # 7. Verification of Mathematical Accuracy
    print("\n[7/10] Verifying Bill Calculation Accuracy...")
    summary = database.calculate_group_summary(group_id)
    # Total Group Bill = 120 + 220 + 20 + 120 + 30 + 300 = 810.0
    assert summary['total_group_bill'] == 810.0, f"Expected 810.0, got {summary['total_group_bill']}"
    assert summary['total_food_cost'] == 760.0, f"Expected 760.0, got {summary['total_food_cost']}" # 120+220+120+300
    assert summary['total_drinks_cost'] == 50.0, f"Expected 50.0, got {summary['total_drinks_cost']}" # 20+30

    payable_map = {m['name']: m['total_payable'] for m in summary['member_summaries']}
    print("  -> Computed Individual Payable Breakdown:")
    for name, amt in payable_map.items():
        print(f"     * {name:<10}: Rs. {amt:.2f}")

    # Person A: 120 (Veg Meals) + 10 (Water) + 200 (Pizza) = 330.0
    assert payable_map['Person A'] == 330.0, f"Person A expected 330.0, got {payable_map['Person A']}"
    # Person B: 220 (Biryani) + 10 (Water) + 100 (Pizza) = 330.0
    assert payable_map['Person B'] == 330.0, f"Person B expected 330.0, got {payable_map['Person B']}"
    # Person C: 20 (Water) + 10 (Shared water) = 30.0
    assert payable_map['Person C'] == 30.0, f"Person C expected 30.0, got {payable_map['Person C']}"
    # Person D: 120 (Veg Meals) + 0 (No shared items) = 120.0
    assert payable_map['Person D'] == 120.0, f"Person D expected 120.0, got {payable_map['Person D']}"
    # Person E: 0 (Consumed nothing) = 0.0
    assert payable_map['Person E'] == 0.0, f"Person E expected 0.0, got {payable_map['Person E']}"

    # Sum of all individual payables must EXACTLY match the final restaurant bill
    sum_payables = sum(payable_map.values())
    assert sum_payables == 810.0, f"Sum ({sum_payables}) != Group Bill (810.0)"
    print(f"  -> Sum of individual amounts: Rs. {sum_payables:.2f} matches total bill Rs. {summary['total_group_bill']:.2f} (Zero discrepancy verified!)")

    # 8. Testing Edit and Delete APIs
    print("\n[8/10] Testing Edit and Delete APIs...")
    items = database.get_items_with_allocations(group_id)
    pizza_item = [it for it in items if 'Pizza' in it['name']][0]

    # Test GET single item
    r_item = client.get(f'/api/items/{pizza_item["id"]}')
    assert r_item.status_code == 200
    assert r_item.get_json()['item']['name'] == pizza_item['name']

    # Delete the pizza item (reduces total bill by 300 to 510)
    r_del = client.delete(f'/api/items/{pizza_item["id"]}')
    assert r_del.status_code == 200
    summary_after_del = database.calculate_group_summary(group_id)
    assert summary_after_del['total_group_bill'] == 510.0
    print("  -> Deleted item and verified bill recalculated to Rs. 510.00.")

    # Remove Person E (who had 0 items)
    r_del_m = client.delete(f'/api/members/{m_map["Person E"]}')
    assert r_del_m.status_code == 200
    assert len(database.get_members(group_id)) == 4
    print("  -> Removed Person E from group.")

    # 9. Test CSV and PDF/Print Export
    print("\n[9/10] Testing CSV and PDF/Print Export Endpoints...")
    r_csv = client.get(f'/group/{group_id}/export/csv')
    assert r_csv.status_code == 200
    assert 'text/csv' in r_csv.content_type
    assert b'510.00' in r_csv.data
    assert b'Person A' in r_csv.data
    print("  -> CSV export generated with status 200 and proper invoice headers.")

    r_print = client.get(f'/group/{group_id}/print')
    assert r_print.status_code == 200
    assert b'window.print()' in r_print.data
    print("  -> PDF/Print view generated with status 200 and print trigger.")

    # 10. Clean up test group
    print("\n[10/10] Testing Group Cleanup and Deletion...")
    client.post(f'/api/groups/{group_id}/clear')
    summary_cleared = database.calculate_group_summary(group_id)
    assert summary_cleared['total_group_bill'] == 0.0
    print("  -> Clear group expenses verified (bill reset to 0, members preserved).")

    client.delete(f'/api/groups/{group_id}')
    assert database.get_group(group_id) is None
    print("  -> Group deleted successfully from SQLite.")

    print("\n" + "=" * 60)
    print("ALL 10 TEST SUITES PASSED FLAWLESSLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
