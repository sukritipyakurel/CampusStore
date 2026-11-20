# The cart is stored in the user's session (see cart/cart.py), so it needs no
# database tables. This keeps guest checkout simple and avoids stale carts in
# the database. Once an order is placed, its contents are saved permanently as
# orders.models.OrderItem rows.
