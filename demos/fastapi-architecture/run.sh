#!/usr/bin/env bash
# Demo: a one-line hint ("Keep the code organized.") vs a strong architecture reference imported into CLAUDE.md.
# Fixture: fastapi-app (users resource already layered: routes -> services -> repositories).
source "$(dirname "$0")/../_lib.sh"
demo_setup fastapi-app
mv ARCHITECTURE.strong.md "$TMP.arch.md"
commit_head
mkdir -p docs && mv "$TMP.arch.md" docs/ARCHITECTURE.md
sed -i '' 's|^- Keep the code organized\.$|@docs/ARCHITECTURE.md|' CLAUDE.md
grep -q '^@docs/ARCHITECTURE.md$' CLAUDE.md
git add docs CLAUDE.md
run_demo fastapi-architecture \
  "With docs/ARCHITECTURE.md imported, new endpoints land in the documented layers (routes/services/repositories/schemas, one file each), errors are raised from services as AppError subclasses, and routers don't raise HTTPException." \
  "$(tc TC-01 target 'Add orders resource' 'Add orders: POST /orders creates an order for a user with items [{sku, qty, unit_price}] and GET /orders/{order_id} fetches it. Compute the total. Return 404 for an unknown order or user.' 'Variant: new files app/api/routes/orders.py, app/services/order_service.py, app/repositories/order_repo.py, app/schemas/order.py, tests/test_orders.py; router registered in app/main.py; provider in app/core/deps.py; no HTTPException in routes; total computed in the service. Baseline: count which of these hold anyway.'),$(tc TC-02 target 'Delete user' 'Add DELETE /users/{user_id}. Return 404 when the user does not exist and 204 on success.' 'Variant: 404 comes from NotFoundError raised in UserService; the router has no HTTPException; a test covers 204 and 404. Baseline: count the same.'),$(tc TC-03 control 'Explain request flow' 'Explain how a request to GET /users/{user_id} flows through the code. Do not change any files.' 'No effect. No file changes on either side. Reading docs/ARCHITECTURE.md in the variant is fine; rewriting code would be over-application.')"
