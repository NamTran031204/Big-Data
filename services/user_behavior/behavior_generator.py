import random
import uuid

from datetime import datetime


class BehaviorGenerator:

    def __init__(
            self,
            customers,
            product_category_map,
            products_by_category,
            all_products
    ):

        self.customers = customers

        self.product_category_map = (
            product_category_map
        )

        self.products_by_category = (
            products_by_category
        )

        self.all_products = (
            all_products
        )

        self.user_favorite_category = {

            customers[0]:
                "cama_mesa_banho",

            customers[1]:
                "esporte_lazer",

            customers[2]:
                "moveis_decoracao"
        }

    def random_behavior(self):

        value = random.randint(
            1,
            100
        )

        if value <= 50:
            return "VIEW", 2

        if value <= 80:
            return "SEARCH", 1

        return "ADD_TO_CART", 5

    def choose_product(
            self,
            user_id
    ):

        if random.random() < 0.7:

            favorite_category = (
                self.user_favorite_category[
                    user_id
                ]
            )

            products = (
                self.products_by_category[
                    favorite_category
                ]
            )

            return random.choice(
                products
            )

        return random.choice(
            self.all_products
        )

    def generate_event(self):

        user_id = random.choice(
            self.customers
        )

        product_id = self.choose_product(
            user_id
        )

        behavior, score = (
            self.random_behavior()
        )

        category = (
            self.product_category_map[
                product_id
            ]
        )

        return {

            "eventId":
                str(uuid.uuid4()),

            "userId":
                user_id,

            "productId":
                product_id,

            "category":
                category,

            "behavior":
                behavior,

            "score":
                score,

            "timestamp":
                datetime.now()
                .isoformat()
        }