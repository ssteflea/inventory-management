"""
Tests for restocking API endpoints.
"""
import pytest


class TestRestockingEndpoints:
    """Test suite for restocking recommendation and order-submission endpoints."""

    def test_get_recommendations_zero_budget(self, client):
        """Test that zero budget returns empty recommendations without error."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["recommendations"] == []
        assert data["total_cost"] == 0
        assert data["remaining_budget"] == 0

    def test_get_recommendations_response_structure(self, client):
        """Test that recommendations response has all required fields."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        assert response.status_code == 200

        data = response.json()

        # Verify top-level fields
        for field in ["budget", "total_cost", "remaining_budget", "forecasts_total",
                      "forecasts_considered", "recommendations"]:
            assert field in data

        assert isinstance(data["recommendations"], list)
        assert isinstance(data["budget"], (int, float))
        assert isinstance(data["total_cost"], (int, float))
        assert isinstance(data["remaining_budget"], (int, float))
        assert isinstance(data["forecasts_total"], int)
        assert isinstance(data["forecasts_considered"], int)

    def test_get_recommendations_item_structure(self, client):
        """Test that each recommendation has all required fields."""
        response = client.get("/api/restocking/recommendations?budget=10000")
        data = response.json()

        if data["recommendations"]:  # Only check if there are recommendations
            for rec in data["recommendations"]:
                # Verify all fields present
                for field in ["sku", "name", "category", "warehouse", "quantity_on_hand",
                             "reorder_point", "unit_cost", "trend", "urgency_score",
                             "recommended_quantity", "line_cost"]:
                    assert field in rec

                # Verify types
                assert isinstance(rec["sku"], str)
                assert isinstance(rec["name"], str)
                assert isinstance(rec["category"], str)
                assert isinstance(rec["warehouse"], str)
                assert isinstance(rec["quantity_on_hand"], int)
                assert isinstance(rec["reorder_point"], int)
                assert isinstance(rec["unit_cost"], (int, float))
                assert isinstance(rec["trend"], str)
                assert isinstance(rec["urgency_score"], (int, float))
                assert isinstance(rec["recommended_quantity"], int)
                assert isinstance(rec["line_cost"], (int, float))

    def test_get_recommendations_respects_budget(self, client):
        """Test that total cost never exceeds the requested budget."""
        response = client.get("/api/restocking/recommendations?budget=500")
        assert response.status_code == 200

        data = response.json()

        # Total cost must never exceed budget
        assert data["total_cost"] <= 500

        # Remaining budget must be non-negative
        assert data["remaining_budget"] >= 0

        # Remaining budget must equal budget - total_cost
        expected_remaining = round(500 - data["total_cost"], 2)
        assert abs(data["remaining_budget"] - expected_remaining) < 0.01

    def test_get_recommendations_sorted_by_urgency(self, client):
        """Test that recommendations are sorted by urgency score descending."""
        response = client.get("/api/restocking/recommendations?budget=100000")
        assert response.status_code == 200

        data = response.json()
        recs = data["recommendations"]

        if len(recs) > 1:
            scores = [r["urgency_score"] for r in recs]
            # Should be in descending order
            assert scores == sorted(scores, reverse=True)

    def test_get_recommendations_valid_trends(self, client):
        """Test that all recommendations have valid trend values."""
        response = client.get("/api/restocking/recommendations?budget=10000")
        data = response.json()

        valid_trends = ["increasing", "stable", "decreasing"]

        for rec in data["recommendations"]:
            assert rec["trend"] in valid_trends

    def test_get_recommendations_negative_budget_rejected(self, client):
        """Test that negative budget returns 400 error."""
        response = client.get("/api/restocking/recommendations?budget=-100")
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "non-negative" in data["detail"].lower() or "budget" in data["detail"].lower()

    def test_submit_restock_order_creates_submitted_status(self, client):
        """Test that submitting an order creates an order with Submitted status."""
        payload = {
            "items": [
                {
                    "sku": "PSU-501",
                    "name": "5V 10A Switching Power Supply",
                    "quantity": 10,
                    "unit_price": 18.99
                }
            ]
        }

        response = client.post("/api/restocking/order", json=payload)
        assert response.status_code == 201

        order = response.json()

        # Verify order was created with correct status
        assert order["status"] == "Submitted"
        assert "id" in order
        assert "order_number" in order
        assert order["order_number"].startswith("RSK-")

    def test_submit_restock_order_structure(self, client):
        """Test that submitted order has all required fields."""
        payload = {
            "items": [
                {"sku": "PSU-501", "name": "5V 10A Switching Power Supply", "quantity": 5, "unit_price": 18.99}
            ]
        }

        response = client.post("/api/restocking/order", json=payload)
        assert response.status_code == 201

        order = response.json()

        # Verify all Order model fields
        for field in ["id", "order_number", "customer", "items", "status", "order_date",
                     "expected_delivery", "total_value", "actual_delivery", "lead_time_days"]:
            assert field in order

    def test_submit_restock_order_has_lead_time(self, client):
        """Test that submitted orders have lead_time_days set."""
        payload = {
            "items": [
                {"sku": "PSU-501", "name": "5V 10A Switching Power Supply", "quantity": 10, "unit_price": 18.99}
            ]
        }

        response = client.post("/api/restocking/order", json=payload)
        order = response.json()

        assert order["lead_time_days"] is not None
        assert isinstance(order["lead_time_days"], int)
        assert order["lead_time_days"] > 0

    def test_submit_restock_order_has_expected_delivery(self, client):
        """Test that submitted orders have expected_delivery date."""
        payload = {
            "items": [
                {"sku": "PSU-501", "name": "5V 10A Switching Power Supply", "quantity": 10, "unit_price": 18.99}
            ]
        }

        response = client.post("/api/restocking/order", json=payload)
        order = response.json()

        assert "expected_delivery" in order
        assert order["expected_delivery"] is not None
        # Should be ISO format datetime
        assert "T" in order["expected_delivery"]

    def test_submit_restock_order_items_preserved(self, client):
        """Test that submitted order preserves the items submitted."""
        payload = {
            "items": [
                {"sku": "PSU-501", "name": "5V 10A Switching Power Supply", "quantity": 10, "unit_price": 18.99},
                {"sku": "FLT-405", "name": "Oil Filter Cartridge", "quantity": 25, "unit_price": 8.25}
            ]
        }

        response = client.post("/api/restocking/order", json=payload)
        order = response.json()

        assert len(order["items"]) == 2
        assert order["items"][0]["sku"] == "PSU-501"
        assert order["items"][0]["quantity"] == 10
        assert order["items"][1]["sku"] == "FLT-405"
        assert order["items"][1]["quantity"] == 25

    def test_submit_restock_order_total_value_calculation(self, client):
        """Test that order total_value is calculated correctly."""
        payload = {
            "items": [
                {"sku": "PSU-501", "name": "5V 10A Switching Power Supply", "quantity": 10, "unit_price": 18.99}
            ]
        }

        response = client.post("/api/restocking/order", json=payload)
        order = response.json()

        # total_value = 10 * 18.99 = 189.90
        expected_total = 10 * 18.99
        assert abs(order["total_value"] - expected_total) < 0.01

    def test_submit_restock_order_appears_in_orders_list(self, client):
        """Test that newly submitted order appears in GET /api/orders."""
        # Submit order
        payload = {
            "items": [
                {"sku": "PSU-501", "name": "5V 10A Switching Power Supply", "quantity": 5, "unit_price": 18.99}
            ]
        }

        submit_response = client.post("/api/restocking/order", json=payload)
        assert submit_response.status_code == 201
        new_order = submit_response.json()
        new_order_id = new_order["id"]

        # Fetch orders with Submitted status filter
        orders_response = client.get("/api/orders?status=Submitted")
        assert orders_response.status_code == 200

        orders = orders_response.json()
        order_ids = [o["id"] for o in orders]

        # New order should be in the list
        assert new_order_id in order_ids

    def test_submit_restock_order_empty_items_rejected(self, client):
        """Test that submitting order with no items returns 400 error."""
        payload = {"items": []}

        response = client.post("/api/restocking/order", json=payload)
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "at least one item" in data["detail"].lower() or "item" in data["detail"].lower()

    def test_lead_time_matches_category_lookup_consumables(self, client):
        """Test that Consumables category gets the correct lead time."""
        payload = {
            "items": [
                {"sku": "FLT-405", "name": "Oil Filter Cartridge", "quantity": 50, "unit_price": 8.25}
            ]
        }

        response = client.post("/api/restocking/order", json=payload)
        order = response.json()

        # FLT-405 is in Consumables category, which should have lead_time_days = 5
        assert order["lead_time_days"] == 5

    def test_lead_time_matches_category_lookup_sensors(self, client):
        """Test that Sensors category gets the correct lead time."""
        payload = {
            "items": [
                {"sku": "SNR-420", "name": "Temperature Sensor Module", "quantity": 20, "unit_price": 95.00}
            ]
        }

        response = client.post("/api/restocking/order", json=payload)
        order = response.json()

        # SNR-420 is in Sensors category, which should have lead_time_days = 7
        assert order["lead_time_days"] == 7

    def test_recommendations_considers_stock_levels(self, client):
        """Test that items below reorder point get higher urgency."""
        response = client.get("/api/restocking/recommendations?budget=100000")
        assert response.status_code == 200

        data = response.json()

        # Items with low stock relative to reorder point should have higher urgency
        if len(data["recommendations"]) > 0:
            for rec in data["recommendations"]:
                # Items below reorder point have urgency_score > 0
                # Items above reorder point have urgency_score < 0
                stock_ratio = (rec["reorder_point"] - rec["quantity_on_hand"]) / rec["reorder_point"]
                # Urgency should correlate with stock_ratio
                if stock_ratio > 0:
                    # Below reorder point should have some positive urgency
                    assert rec["urgency_score"] >= 0

    def test_order_default_customer_name(self, client):
        """Test that orders get default customer name if not provided."""
        payload = {
            "items": [
                {"sku": "PSU-501", "name": "5V 10A Switching Power Supply", "quantity": 10, "unit_price": 18.99}
            ]
        }

        response = client.post("/api/restocking/order", json=payload)
        order = response.json()

        # Should have default customer name
        assert order["customer"] == "Internal Restocking"

    def test_order_custom_customer_name(self, client):
        """Test that custom customer name is preserved."""
        payload = {
            "items": [
                {"sku": "PSU-501", "name": "5V 10A Switching Power Supply", "quantity": 10, "unit_price": 18.99}
            ],
            "customer": "Custom Supplier"
        }

        response = client.post("/api/restocking/order", json=payload)
        order = response.json()

        assert order["customer"] == "Custom Supplier"
